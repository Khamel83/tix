import asyncio
import json

from ticket_sniper.db.models import Base, Rule, RuleSectionMatcher, SourceEvent, Venue, utcnow_str
from ticket_sniper.db.session import engine, run_db_transaction
from ticket_sniper.listings.collector import collect_event_listings
from ticket_sniper.profiles.preferences import load_active_profile, seed_profile
from ticket_sniper.rules.evaluator import compute_rule_fingerprint

DEMO_EVENT_BY_VENUE = {
    "Dodger Stadium": ("demo-dodgers-001", "Dodgers Demo", "Field 1", 150.0, 300.0),
    "Hollywood Bowl": ("demo-hollywoodbowl-001", "Hollywood Bowl Demo", "Terrace 3", 160.0, 320.0),
}


async def seed_demo_data() -> dict:
    Base.metadata.create_all(bind=engine)
    profile_summary = await seed_profile()
    profile = await load_active_profile()
    profile_venues = [venue["display_name"] for venue in (profile or {}).get("venues", [])]

    def _seed_core(session):
        created = {"venues": 0, "events": 0, "rules": 0}
        specs = [
            (venue_name, *DEMO_EVENT_BY_VENUE[venue_name])
            for venue_name in profile_venues
            if venue_name in DEMO_EVENT_BY_VENUE
        ]
        for venue_name, event_id, title, section, max_unit, max_total in specs:
            venue = session.query(Venue).filter_by(display_name=venue_name).one_or_none()
            if venue is None:
                venue = Venue(display_name=venue_name, source="seatgeek", source_venue_id=venue_name)
                session.add(venue)
                session.flush()
                created["venues"] += 1

            event = session.get(SourceEvent, ("seatgeek", event_id))
            if event is None:
                event = SourceEvent(
                    source="seatgeek",
                    source_event_id=event_id,
                    first_seen_at=utcnow_str(),
                    last_seen_at=utcnow_str(),
                )
                session.add(event)
                created["events"] += 1
            event.venue_id = venue.id
            event.title = title
            event.venue_name = venue_name
            event.performers_json = json.dumps([], sort_keys=True)
            event.starts_at_utc = "2026-08-15T02:10:00Z"
            event.event_url = f"https://example.test/events/{event_id}"
            event.status = "active"

            rule = session.query(Rule).filter_by(name=f"{venue_name} demo rule").one_or_none()
            if rule is None:
                rule = Rule(
                    name=f"{venue_name} demo rule",
                    enabled=1,
                    scope_type="venue",
                    scope_venue_id=venue.id,
                    max_unit_price_all_in=max_unit,
                    max_order_total=max_total,
                    quantity_mode="exact",
                    quantity_value=2,
                    minimum_fee_confidence="medium",
                    rule_fingerprint="pending",
                )
                session.add(rule)
                session.flush()
                matcher = RuleSectionMatcher(
                    rule_id=rule.id,
                    action="include",
                    matcher_type="exact",
                    matcher_value=section,
                )
                session.add(matcher)
                session.flush()
                rule.rule_fingerprint = compute_rule_fingerprint(rule, [matcher])
                created["rules"] += 1
        return created

    summary = await run_db_transaction(_seed_core)
    summary["profiles"] = profile_summary["profiles"]
    summary["profile_sports"] = profile_summary["sports"]
    summary["profile_venues"] = profile_summary["venues"]
    dodgers = await collect_event_listings("seatgeek", "demo-dodgers-001", tier=0)
    bowl = await collect_event_listings("seatgeek", "demo-hollywoodbowl-001", tier=0)
    summary["listings"] = dodgers["listings_seen"] + bowl["listings_seen"]
    return summary


def main() -> None:
    print(asyncio.run(seed_demo_data()))


if __name__ == "__main__":
    main()
