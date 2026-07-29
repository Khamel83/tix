from dataclasses import dataclass

from sqlalchemy import or_

from ticket_sniper.config import settings
from ticket_sniper.db.models import EventPriceSnapshot, Rule, SourceEvent
from ticket_sniper.db.session import run_db_transaction


@dataclass(frozen=True)
class GateResult:
    should_collect_listings: bool
    decision: str
    reason: str


async def evaluate_event_gate(source: str, source_event_id: str, snapshot: EventPriceSnapshot) -> GateResult:
    if snapshot.lowest_price is None:
        return GateResult(False, "insufficient_data", "missing lowest_price")

    def _load_rules(session):
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

    rules = await run_db_transaction(_load_rules)
    if not rules:
        return GateResult(False, "no_rules", "no enabled rules for event")

    threshold = min(rule.max_unit_price_all_in * (1 + settings.GATE_MARGIN) for rule in rules)
    if snapshot.lowest_price <= threshold:
        return GateResult(True, "pass", f"lowest_price {snapshot.lowest_price} <= gate threshold {threshold:.2f}")
    return GateResult(False, "price_above_threshold", f"lowest_price {snapshot.lowest_price} > gate threshold {threshold:.2f}")
