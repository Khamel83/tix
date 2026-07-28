import logging
import json
import httpx
from math import ceil
from typing import Optional, Dict, Any, Iterable, List
from ticket_sniper.config import settings
from ticket_sniper.db.models import SourceEvent, Venue, utcnow_str
from ticket_sniper.db.session import run_db_transaction

logger = logging.getLogger(__name__)
SEATGEEK_API_BASE = "https://api.seatgeek.com/2"
SEATGEEK_SOURCE = "seatgeek"
SCHEDULED_DISCOVERY_MAX_PAGES = 10

class SeatGeekDiscovery:
    def __init__(self):
        self.client_id = settings.SEATGEEK_CLIENT_ID

    async def resolve_venue(self, display_name: str) -> Optional[Dict[str, Any]]:
        url = f"{SEATGEEK_API_BASE}/venues"
        params = {"q": display_name, "client_id": self.client_id}
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(url, params=params)
                if resp.status_code != 200: return None
                venues = resp.json().get("venues", [])
                if not venues: return None
                top = venues[0]
                return {
                    "source_venue_id": str(top["id"]),
                    "display_name": display_name,
                    "city": top.get("city"),
                    "timezone": top.get("timezone", "America/Los_Angeles")
                }
            except Exception as e:
                logger.error(f"Failed resolving venue {display_name}: {e}")
                return None

    async def collect_target_sports_venues_and_events(
        self,
        target_venues: Optional[Iterable[str]] = None,
    ) -> Dict[str, int]:
        venue_names = list(target_venues or settings.TARGET_SPORTS_VENUES)
        if not venue_names:
            return {"venues_seeded": 0, "venues_resolved": 0, "events_upserted": 0}

        resolved_venues = []
        for venue_name in venue_names:
            resolved = await self.resolve_venue(venue_name)
            resolved_venues.append(
                resolved
                or {
                    "display_name": venue_name,
                    "source_venue_id": None,
                    "city": None,
                    "timezone": settings.TZ_DISPLAY,
                }
            )

        venues = await self._upsert_target_venues(resolved_venues)
        events_by_venue_id: Dict[int, List[Dict[str, Any]]] = {}
        for venue in venues:
            if not venue.get("source_venue_id"):
                logger.warning("Skipping event discovery for unresolved venue %s", venue["display_name"])
                continue
            events_by_venue_id[venue["id"]] = await self.fetch_events_for_venue(
                venue["source_venue_id"],
                max_pages=SCHEDULED_DISCOVERY_MAX_PAGES,
            )

        events_upserted = await self._upsert_source_events(events_by_venue_id)
        return {
            "venues_seeded": len(venues),
            "venues_resolved": sum(1 for venue in venues if venue.get("source_venue_id")),
            "events_upserted": events_upserted,
        }

    async def fetch_events_for_venue(
        self,
        source_venue_id: str,
        *,
        per_page: int = 100,
        max_pages: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        url = f"{SEATGEEK_API_BASE}/events"
        all_events: List[Dict[str, Any]] = []
        page = 1
        async with httpx.AsyncClient(timeout=10.0) as client:
            while max_pages is None or page <= max_pages:
                params = {
                    "venue.id": source_venue_id,
                    "client_id": self.client_id,
                    "per_page": per_page,
                    "page": page,
                }
                try:
                    resp = await client.get(url, params=params)
                    if resp.status_code != 200:
                        logger.warning(
                            "SeatGeek event discovery failed for venue %s with status %s",
                            source_venue_id,
                            resp.status_code,
                        )
                        break
                    payload = resp.json()
                except Exception as e:
                    logger.error(f"Failed fetching SeatGeek events for venue {source_venue_id}: {e}")
                    break

                events = payload.get("events", [])
                all_events.extend(events)
                if not events:
                    break

                meta = payload.get("meta", {})
                total = int(meta.get("total", len(all_events)) or 0)
                total_pages = max(1, ceil(total / per_page))
                if page >= total_pages:
                    break
                page += 1

        return all_events

    async def _upsert_target_venues(self, resolved_venues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def _write(session):
            stored = []
            for resolved in resolved_venues:
                display_name = resolved["display_name"]
                source_venue_id = resolved.get("source_venue_id")
                venue = session.query(Venue).filter_by(display_name=display_name).one_or_none()
                if venue is None and source_venue_id:
                    venue = (
                        session.query(Venue)
                        .filter_by(source=SEATGEEK_SOURCE, source_venue_id=str(source_venue_id))
                        .one_or_none()
                    )
                if venue is None:
                    venue = Venue(display_name=display_name, source=SEATGEEK_SOURCE)
                    session.add(venue)

                venue.display_name = display_name
                venue.source = SEATGEEK_SOURCE
                venue.source_venue_id = str(source_venue_id) if source_venue_id else None
                venue.city = resolved.get("city")
                venue.timezone = resolved.get("timezone") or settings.TZ_DISPLAY
                venue.enabled = 1
                if source_venue_id:
                    venue.resolved_at = utcnow_str()
                stored.append(venue)

            session.flush()
            return [
                {
                    "id": venue.id,
                    "display_name": venue.display_name,
                    "source_venue_id": venue.source_venue_id,
                }
                for venue in stored
            ]

        return await run_db_transaction(_write)

    async def _upsert_source_events(self, events_by_venue_id: Dict[int, List[Dict[str, Any]]]) -> int:
        def _write(session):
            upserted = 0
            for venue_id, events in events_by_venue_id.items():
                for event_payload in events:
                    source_event_id = str(event_payload["id"])
                    event = (
                        session.query(SourceEvent)
                        .filter_by(source=SEATGEEK_SOURCE, source_event_id=source_event_id)
                        .one_or_none()
                    )
                    if event is None:
                        event = SourceEvent(
                            source=SEATGEEK_SOURCE,
                            source_event_id=source_event_id,
                            first_seen_at=utcnow_str(),
                        )
                        session.add(event)

                    venue_payload = event_payload.get("venue") or {}
                    event.venue_id = venue_id
                    event.title = event_payload.get("title") or event_payload.get("short_title") or "Untitled Event"
                    event.venue_name = venue_payload.get("name") or event_payload.get("venue_name") or ""
                    event.performers_json = json.dumps(event_payload.get("performers", []), sort_keys=True)
                    event.starts_at_utc = self._normalize_utc_datetime(event_payload.get("datetime_utc"))
                    event.event_url = event_payload.get("url") or ""
                    event.status = event_payload.get("status") or "active"
                    event.last_seen_at = utcnow_str()
                    upserted += 1
            return upserted

        return await run_db_transaction(_write)

    @staticmethod
    def _normalize_utc_datetime(raw_value: Optional[str]) -> str:
        if not raw_value:
            return utcnow_str()
        if raw_value.endswith("Z"):
            return raw_value
        if raw_value.endswith("+00:00"):
            return f"{raw_value[:-6]}Z"
        return f"{raw_value}Z"
