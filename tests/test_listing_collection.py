import json

import pytest

from ticket_sniper.argus.models import FetchRawResponse
from ticket_sniper.db.models import ListingCurrent, ListingPriceHistory, PollRun, SourceEvent
from ticket_sniper.db.session import SessionLocal, run_db_transaction
from ticket_sniper.config import settings
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


def test_seatgeek_parser_accepts_direct_listing_json():
    listings, count, complete = SeatGeekAdapter().parse_inventory(
        fixture_body(), "demo-dodgers-001"
    )

    assert count == 3
    assert complete is True
    assert listings[0]["source_listing_id"] == "demo-dodgers-good"


def test_seatgeek_parser_accepts_listing_json_embedded_in_html_script():
    inventory = json.loads(fixture_body())
    html = (
        "<html><head><script id=\"__NEXT_DATA__\" type=\"application/json\">"
        + json.dumps({"props": {"pageProps": {"inventory": inventory}}})
        + "</script></head><body></body></html>"
    )

    listings, count, complete = SeatGeekAdapter().parse_inventory(html, "demo-dodgers-001")

    assert count == 3
    assert complete is True
    assert listings[0]["source_listing_id"] == "demo-dodgers-good"


@pytest.mark.asyncio
async def test_live_collection_uses_stored_source_event_url(seed_event_and_rule, monkeypatch):
    event_url = "https://seatgeek.com/los-angeles-dodgers-tickets/example-real-event"
    seed_event_and_rule(source_event_id="real-event", venue_name="Real Venue")

    def update_event_url(session):
        event = session.get(SourceEvent, ("seatgeek", "real-event"))
        event.event_url = event_url

    await run_db_transaction(update_event_url)
    captured = {}

    class FakeArgusClient:
        async def fetch_raw(self, request):
            captured["request"] = request
            return FetchRawResponse(status="ok", body=fixture_body())

    monkeypatch.setattr(settings, "LISTING_COLLECTION_SOURCE", "argus")

    summary = await collect_event_listings(
        "seatgeek", "real-event", tier=2, argus_client=FakeArgusClient()
    )

    assert summary["status"] == "success"
    assert captured["request"].url == event_url
    assert captured["request"].render == "browser"
    assert captured["request"].extractors == ["raw_html"]


@pytest.mark.asyncio
async def test_live_collection_preserves_argus_error_and_http_status(
    seed_event_and_rule, monkeypatch
):
    seed_event_and_rule(source_event_id="real-error", venue_name="Error Venue")

    class FakeArgusClient:
        async def fetch_raw(self, request):
            return FetchRawResponse(
                status="error",
                http_status=503,
                error="managed browser unavailable",
            )

    monkeypatch.setattr(settings, "LISTING_COLLECTION_SOURCE", "argus")

    with pytest.raises(RuntimeError) as failure:
        await collect_event_listings(
            "seatgeek",
            "real-error",
            tier=2,
            argus_client=FakeArgusClient(),
        )

    assert str(failure.value) == (
        "Argus listing collection failed (http_status=503): managed browser unavailable"
    )


@pytest.mark.asyncio
async def test_scrapling_collection_hands_raw_payload_to_adapter_and_upserts(
    seed_event_and_rule, monkeypatch
):
    event_url = "https://seatgeek.com/example/scrapling-event"
    seed_event_and_rule(source_event_id="scrapling-event")

    def update_event_url(session):
        session.get(SourceEvent, ("seatgeek", "scrapling-event")).event_url = event_url

    await run_db_transaction(update_event_url)
    monkeypatch.setattr(settings, "LISTING_COLLECTION_SOURCE", "scrapling")
    captured = {}

    class FakeScraplingResponse:
        body = fixture_body().encode("utf-8")
        text = "not the raw SeatGeek payload"

    class FakeScraplingClient:
        async def fetch_raw(self, url):
            captured["url"] = url
            return FakeScraplingResponse()

    summary = await collect_event_listings(
        "seatgeek",
        "scrapling-event",
        tier=2,
        scrapling_client=FakeScraplingClient(),
    )

    session = SessionLocal()
    try:
        assert captured["url"] == event_url
        assert summary["status"] == "success"
        assert summary["listings_seen"] == 3
        assert session.query(ListingCurrent).count() == 3
        assert session.get(ListingCurrent, ("seatgeek", "demo-dodgers-good")) is not None
    finally:
        session.close()


@pytest.mark.asyncio
async def test_scrapling_failure_uses_configured_argus_fallback(
    seed_event_and_rule, monkeypatch
):
    seed_event_and_rule(source_event_id="scrapling-fallback")
    monkeypatch.setattr(settings, "LISTING_COLLECTION_SOURCE", "scrapling")
    monkeypatch.setattr(settings, "SCRAPLING_FALLBACK_SOURCE", "argus")
    captured = {}

    class FailingScraplingClient:
        async def fetch_raw(self, url):
            raise RuntimeError("scrapling unavailable")

    class FakeArgusClient:
        async def fetch_raw(self, request):
            captured["argus_url"] = request.url
            return FetchRawResponse(status="ok", body=fixture_body())

    summary = await collect_event_listings(
        "seatgeek",
        "scrapling-fallback",
        tier=2,
        scrapling_client=FailingScraplingClient(),
        argus_client=FakeArgusClient(),
    )

    session = SessionLocal()
    try:
        assert captured["argus_url"] == "https://example.test/events/scrapling-fallback"
        assert summary["status"] == "success"
        assert session.query(ListingCurrent).count() == 3
    finally:
        session.close()


@pytest.mark.asyncio
async def test_scrapling_failure_does_not_load_fixture_when_fallback_is_error(
    seed_event_and_rule, monkeypatch
):
    seed_event_and_rule(source_event_id="demo-dodgers-001")
    monkeypatch.setattr(settings, "LISTING_COLLECTION_SOURCE", "scrapling")
    monkeypatch.setattr(settings, "SCRAPLING_FALLBACK_SOURCE", "error")

    class FailingScraplingClient:
        async def fetch_raw(self, url):
            raise RuntimeError("scrapling unavailable")
    def fail_fixture(source_event_id):
        raise AssertionError("live Scrapling collection loaded a fixture")

    monkeypatch.setattr(
        "ticket_sniper.listings.collector._fixture_path",
        fail_fixture,
    )

    with pytest.raises(RuntimeError, match="scrapling unavailable"):
        await collect_event_listings(
            "seatgeek",
            "demo-dodgers-001",
            tier=2,
            scrapling_client=FailingScraplingClient(),
        )

    session = SessionLocal()
    try:
        assert session.query(ListingCurrent).count() == 0
    finally:
        session.close()


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
