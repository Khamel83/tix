import json

from sqlalchemy import or_

from ticket_sniper.db.models import (
    AlertDecision,
    AlertOutbox,
    AlertState,
    ListingCurrent,
    Rule,
    RuleSectionMatcher,
    SourceEvent,
)
from ticket_sniper.db.session import run_db_transaction
from ticket_sniper.rules.evaluator import EvaluationResult, evaluate_listing
from ticket_sniper.rules.state_machine import process_alert_state_machine


def format_alert_message(rule: Rule, listing: ListingCurrent, result: EvaluationResult) -> str:
    return (
        f"Ticket alert: {rule.name}\n"
        f"{listing.normalized_section or listing.raw_section} row {listing.raw_row or '-'}\n"
        f"${listing.unit_price_all_in:.2f} all-in, qty {rule.quantity_value}\n"
        f"{listing.listing_url}"
    )


def _relevant_rules(session, source: str, source_event_id: str):
    event = session.get(SourceEvent, (source, source_event_id))
    if event is None:
        return []
    return (
        session.query(Rule)
        .filter(Rule.enabled == 1)
        .filter(
            or_(
                Rule.scope_type == "global",
                (Rule.scope_type == "venue") & (Rule.scope_venue_id == event.venue_id),
                (
                    (Rule.scope_source == source)
                    & (Rule.scope_source_event_id == source_event_id)
                ),
            )
        )
        .all()
    )


async def evaluate_event_alerts(source: str, source_event_id: str) -> dict:
    def _evaluate(session):
        listings = (
            session.query(ListingCurrent)
            .filter_by(source=source, source_event_id=source_event_id, status="active")
            .all()
        )
        rules = _relevant_rules(session, source, source_event_id)
        listings_evaluated = 0
        decisions_written = 0
        alerts_queued = 0
        duplicates_suppressed = 0
        for rule in rules:
            matchers = (
                session.query(RuleSectionMatcher)
                .filter_by(rule_id=rule.id)
                .order_by(RuleSectionMatcher.sort_order.asc())
                .all()
            )
            for listing in listings:
                listings_evaluated += 1
                result = evaluate_listing(rule, matchers, listing)
                state = session.get(AlertState, (rule.id, source, listing.source_listing_id))
                branch, outcome, should_alert, next_state = process_alert_state_machine(
                    state, rule, listing, result.qualifies, result.reason_fingerprint
                )
                session.merge(next_state)
                inputs = {
                    "qualifies": result.qualifies,
                    "reason_vector": result.reason_vector,
                    "reason_fingerprint": result.reason_fingerprint,
                    "unit_price_all_in": listing.unit_price_all_in,
                }
                session.add(
                    AlertDecision(
                        rule_id=rule.id,
                        source=source,
                        listing_identity=listing.source_listing_id,
                        branch=branch,
                        outcome=outcome,
                        inputs_json=json.dumps(inputs, sort_keys=True),
                    )
                )
                decisions_written += 1
                if outcome == "duplicate_suppressed":
                    duplicates_suppressed += 1
                if should_alert:
                    dedupe_key = f"{rule.id}:{source}:{listing.source_listing_id}:{branch}:{result.reason_fingerprint}"
                    existing = session.query(AlertOutbox).filter_by(dedupe_key=dedupe_key).one_or_none()
                    if existing is None:
                        session.add(
                            AlertOutbox(
                                payload_json=json.dumps(
                                    {
                                        "text": format_alert_message(rule, listing, result),
                                        "rule_id": rule.id,
                                        "source": source,
                                        "source_event_id": source_event_id,
                                        "source_listing_id": listing.source_listing_id,
                                    },
                                    sort_keys=True,
                                ),
                                dedupe_key=dedupe_key,
                            )
                        )
                        alerts_queued += 1
                    else:
                        duplicates_suppressed += 1
        return {
            "listings_evaluated": listings_evaluated,
            "decisions_written": decisions_written,
            "alerts_queued": alerts_queued,
            "duplicates_suppressed": duplicates_suppressed,
        }

    return await run_db_transaction(_evaluate)
