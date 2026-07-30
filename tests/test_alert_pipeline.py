import pytest
from datetime import datetime, timedelta, timezone

from ticket_sniper.alerts.pipeline import evaluate_event_alerts
from ticket_sniper.db.models import AlertDecision, AlertOutbox, AlertState, ListingCurrent
from ticket_sniper.db.session import SessionLocal
from ticket_sniper.listings.collector import collect_event_listings


@pytest.mark.asyncio
async def test_first_time_qualifying_listing_creates_decision_state_and_outbox(seed_event_and_rule):
    seed_event_and_rule()
    await collect_event_listings("seatgeek", "demo-dodgers-001", tier=2)

    summary = await evaluate_event_alerts("seatgeek", "demo-dodgers-001")

    session = SessionLocal()
    try:
        assert summary["alerts_queued"] == 1
        assert session.query(AlertDecision).count() == 3
        assert session.query(AlertState).filter_by(currently_qualifying=1).count() == 1
        assert session.query(AlertOutbox).count() == 1
    finally:
        session.close()


@pytest.mark.asyncio
async def test_duplicate_qualifying_listing_does_not_enqueue_again(seed_event_and_rule):
    seed_event_and_rule()
    await collect_event_listings("seatgeek", "demo-dodgers-001", tier=2)
    await evaluate_event_alerts("seatgeek", "demo-dodgers-001")
    summary = await evaluate_event_alerts("seatgeek", "demo-dodgers-001")

    session = SessionLocal()
    try:
        assert summary["duplicates_suppressed"] >= 1
        assert session.query(AlertOutbox).count() == 1
    finally:
        session.close()


@pytest.mark.asyncio
async def test_qualifying_to_nonqualifying_updates_state_without_alert(seed_event_and_rule):
    _, _, rule = seed_event_and_rule()
    await collect_event_listings("seatgeek", "demo-dodgers-001", tier=2)
    await evaluate_event_alerts("seatgeek", "demo-dodgers-001")

    session = SessionLocal()
    try:
        listing = session.get(ListingCurrent, ("seatgeek", "demo-dodgers-good"))
        listing.unit_price_all_in = 999
        listing.payload_hash = "price-up"
        session.commit()
    finally:
        session.close()


@pytest.mark.asyncio
async def test_material_price_drop_enqueues_realert_after_cooldown(seed_event_and_rule):
    _, _, rule = seed_event_and_rule()
    rule_id = rule.id
    await collect_event_listings("seatgeek", "demo-dodgers-001", tier=2)
    await evaluate_event_alerts("seatgeek", "demo-dodgers-001")

    old_time = (datetime.now(timezone.utc) - timedelta(minutes=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    session = SessionLocal()
    try:
        listing = session.get(ListingCurrent, ("seatgeek", "demo-dodgers-good"))
        listing.unit_price_all_in = 80
        listing.payload_hash = "price-drop"
        state = session.get(AlertState, (rule_id, "seatgeek", "demo-dodgers-good"))
        state.last_alert_at = old_time
        session.commit()
    finally:
        session.close()

    summary = await evaluate_event_alerts("seatgeek", "demo-dodgers-001")

    session = SessionLocal()
    try:
        assert summary["alerts_queued"] == 1
        assert session.query(AlertOutbox).count() == 2
    finally:
        session.close()


@pytest.mark.asyncio
async def test_cooldown_suppresses_material_realert(seed_event_and_rule):
    seed_event_and_rule()
    await collect_event_listings("seatgeek", "demo-dodgers-001", tier=2)
    await evaluate_event_alerts("seatgeek", "demo-dodgers-001")

    session = SessionLocal()
    try:
        listing = session.get(ListingCurrent, ("seatgeek", "demo-dodgers-good"))
        listing.unit_price_all_in = 80
        listing.payload_hash = "price-drop"
        session.commit()
    finally:
        session.close()

    summary = await evaluate_event_alerts("seatgeek", "demo-dodgers-001")

    session = SessionLocal()
    try:
        assert summary["alerts_queued"] == 0
        assert session.query(AlertOutbox).count() == 1
    finally:
        session.close()
