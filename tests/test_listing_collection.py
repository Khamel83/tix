import json

import pytest

from ticket_sniper.db.models import ListingCurrent, ListingPriceHistory, PollRun
from ticket_sniper.db.session import SessionLocal, run_db_transaction
from ticket_sniper.listings.collector import collect_event_listings, upsert_listings
from ticket_sniper.sources.seatgeek import SeatGeekAdapter


def fixture_body(name="seatgeek_listings_dodgers.json"):
    return (Path(__file__).parent / "fixtures" / name).read_text()


from pathlib import Path


def test_seatgeek_fixture_listing_parser_normalizes_fields():
    listings, count, complete = SeatGeekAdapter().parse_inventory(fixture_body(), "demo-dodgers-001")

    good = listings[0]
    assert count == 3
    assert complete is True
    assert good["source_listing_id"] == "demo-dodgers-good"
    assert good["raw_section"] == "Field 1"
    assert good["raw_row"] == "A"
    assert good["quantity_available"] == 4
    assert json.loads(good["available_quantities_json"]) == [1, 2, 4]
    assert good["unit_price_all_in"] == 125.0
    assert good["unit_price_listed"] == 98.0
    assert good["fee_confidence"] == "high"
    assert len(good["payload_hash"]) == 64


@pytest.mark.asyncio
async def test_upsert_listings_is_idempotent_and_records_history_on_change():
    listings, _, _ = SeatGeekAdapter().parse_inventory(fixture_body(), "demo-dodgers-001")

    first = await upsert_listings("seatgeek", "demo-dodgers-001", listings, run_id=0)
    second = await upsert_listings("seatgeek", "demo-dodgers-001", listings, run_id=0)
    changed = dict(listings[0])
    changed["unit_price_all_in"] = 99.0
    changed["payload_hash"] = "changed"
    third = await upsert_listings("seatgeek", "demo-dodgers-001", [changed], run_id=0)

    session = SessionLocal()
    try:
        assert first["new_listing_count"] == 3
        assert second["new_listing_count"] == 0
        assert second["changed_listing_count"] == 0
        assert third["changed_listing_count"] == 1
        assert session.query(ListingCurrent).count() == 3
        assert session.query(ListingPriceHistory).count() == 4
    finally:
        session.close()


@pytest.mark.asyncio
async def test_failed_collection_marks_poll_run_failed_and_keeps_existing_rows(monkeypatch):
    listings, _, _ = SeatGeekAdapter().parse_inventory(fixture_body(), "demo-dodgers-001")
    await upsert_listings("seatgeek", "demo-dodgers-001", listings, run_id=0)

    def _run(session):
        run = PollRun(tier=2, source="seatgeek", source_event_id="missing", status="running")
        session.add(run)
        session.flush()
        return run.id

    run_id = await run_db_transaction(_run)
    monkeypatch.setattr("ticket_sniper.listings.collector._fetch_live_argus_payload", _raise_runtime)

    with pytest.raises(RuntimeError):
        await collect_event_listings("seatgeek", "missing", tier=2, run_id=run_id)

    session = SessionLocal()
    try:
        assert session.get(PollRun, run_id).status == "failed"
        assert session.query(ListingCurrent).count() == 3
    finally:
        session.close()


async def _raise_runtime(source_event_id):
    raise RuntimeError("no fixture")
