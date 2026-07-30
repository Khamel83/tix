from pathlib import Path
from typing import Any, Dict, List

from ticket_sniper.argus.client import ArgusClient
from ticket_sniper.argus.models import FetchRawRequest
from ticket_sniper.config import settings
from ticket_sniper.db.models import ListingCurrent, ListingPriceHistory, PollRun, SourceEvent, utcnow_str
from ticket_sniper.db.session import run_db_transaction
from ticket_sniper.sources.seatgeek import SeatGeekAdapter

FIXTURE_BY_EVENT_ID = {
    "demo-dodgers-001": "seatgeek_listings_dodgers.json",
    "demo-hollywoodbowl-001": "seatgeek_listings_hollywood_bowl.json",
}


def _fixture_path(source_event_id: str) -> Path | None:
    name = FIXTURE_BY_EVENT_ID.get(source_event_id)
    if not name:
        return None
    return Path(__file__).resolve().parents[2] / "tests" / "fixtures" / name


async def _fetch_live_argus_payload(source_event_id: str) -> str:
    def _event_url(session):
        event = session.get(SourceEvent, ("seatgeek", source_event_id))
        if event is None or not event.event_url:
            raise RuntimeError(f"No stored event URL for SeatGeek event {source_event_id}")
        return event.event_url

    event_url = await run_db_transaction(_event_url)
    response = await ArgusClient().fetch_raw(
        FetchRawRequest(
            url=event_url,
            render="browser",
            cache=False,
            extractors=["raw_html"],
            impersonate="chrome",
            egress="residential",
            timeout_seconds=20,
        )
    )
    if response.status != "ok":
        message = "Argus listing collection failed"
        if response.http_status is not None:
            message += f" (http_status={response.http_status})"
        if response.error:
            message += f": {response.error}"
        raise RuntimeError(message)
    if not response.body:
        raise RuntimeError("Argus listing collection failed: empty response body")
    return response.body


async def collect_event_listings(
    source: str,
    source_event_id: str,
    tier: int,
    raw_body: str | None = None,
    run_id: int | None = None,
) -> Dict[str, Any]:
    if source != "seatgeek":
        raise ValueError(f"Unsupported listing source: {source}")
    try:
        body = raw_body
        fixture = _fixture_path(source_event_id)
        if body is None and (settings.TIX_PROTOTYPE_MODE or fixture):
            if fixture and fixture.exists():
                body = fixture.read_text()
        if body is None:
            body = await _fetch_live_argus_payload(source_event_id)

        listings, inventory_count, pagination_complete = SeatGeekAdapter().parse_inventory(body, source_event_id)
        summary = await upsert_listings(source, source_event_id, listings, run_id or 0)
        summary.update(
            {
                "inventory_count": inventory_count,
                "pagination_complete": pagination_complete,
                "status": "success",
            }
        )
        return summary
    except Exception as exc:
        if run_id is not None:
            def _fail(session):
                run = session.get(PollRun, run_id)
                if run:
                    run.status = "failed"
                    run.completed_at = utcnow_str()
                    run.error_code = exc.__class__.__name__
                    run.error_summary = "Listing collection failed"

            await run_db_transaction(_fail)
        raise


async def upsert_listings(
    source: str,
    source_event_id: str,
    listings: List[Dict[str, Any]],
    run_id: int,
) -> Dict[str, int]:
    def _write(session):
        new_count = 0
        changed_count = 0
        now = utcnow_str()
        seen = set()
        for data in listings:
            source_listing_id = data["source_listing_id"]
            seen.add(source_listing_id)
            current = session.get(ListingCurrent, (source, source_listing_id))
            changed = False
            if current is None:
                current = ListingCurrent(source=source, source_listing_id=source_listing_id, first_seen_at=now)
                session.add(current)
                new_count += 1
                changed = True
            else:
                changed = (
                    current.payload_hash != data["payload_hash"]
                    or current.quantity_available != data["quantity_available"]
                    or current.unit_price_all_in != data.get("unit_price_all_in")
                )
                if changed:
                    changed_count += 1

            for key, value in data.items():
                setattr(current, key, value)
            current.source = source
            current.source_event_id = source_event_id
            current.identity_type = "source_id"
            current.identity_confidence = "high"
            current.status = "active"
            current.inactive_at = None
            current.consecutive_missing_count = 0
            current.last_seen_at = now

            if changed:
                session.add(
                    ListingPriceHistory(
                        source=source,
                        source_listing_id=source_listing_id,
                        observed_at=now,
                        unit_price_listed=current.unit_price_listed,
                        unit_price_all_in=current.unit_price_all_in,
                        price_basis=current.price_basis,
                        quantity_available=current.quantity_available,
                    )
                )

        if run_id:
            run = session.get(PollRun, run_id)
            if run:
                run.inventory_count = len(listings)
                run.new_listing_count = new_count
                run.changed_listing_count = changed_count
                run.parser_version = "seatgeek-fixture-v1"

        return {
            "listings_seen": len(seen),
            "new_listing_count": new_count,
            "changed_listing_count": changed_count,
        }

    return await run_db_transaction(_write)
