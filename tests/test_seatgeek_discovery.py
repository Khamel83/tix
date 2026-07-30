import os
import tempfile

os.environ.setdefault("SEATGEEK_CLIENT_ID", "test-client")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat")
os.environ.setdefault("ARGUS_BASE_URL", "http://argus.test")
os.environ.setdefault("DATABASE_PATH", tempfile.NamedTemporaryFile(delete=False).name)

import pytest

from ticket_sniper.db.models import Base, SourceEvent, Venue
from ticket_sniper.db.session import SessionLocal, engine
from ticket_sniper.discovery.seatgeek import SeatGeekDiscovery
from ticket_sniper.profiles.preferences import ProfileSpec, VenuePreference, seed_profile


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.mark.asyncio
async def test_upserts_target_venues_and_events():
    discovery = SeatGeekDiscovery()
    venues = await discovery._upsert_target_venues(
        [
            {
                "display_name": "Dodger Stadium",
                "source_venue_id": "8",
                "city": "Los Angeles",
                "timezone": "America/Los_Angeles",
            }
        ]
    )

    count = await discovery._upsert_source_events(
        {
            venues[0]["id"]: [
                {
                    "id": 123,
                    "title": "Los Angeles Dodgers vs. San Francisco Giants",
                    "datetime_utc": "2026-08-01T02:10:00",
                    "url": "https://seatgeek.test/event/123",
                    "venue": {"name": "Dodger Stadium"},
                    "performers": [{"name": "Los Angeles Dodgers"}],
                }
            ]
        }
    )

    session = SessionLocal()
    try:
        venue = session.query(Venue).one()
        event = session.query(SourceEvent).one()
        assert count == 1
        assert venue.display_name == "Dodger Stadium"
        assert venue.source_venue_id == "8"
        assert event.venue_id == venue.id
        assert event.venue_name == "Dodger Stadium"
        assert event.starts_at_utc == "2026-08-01T02:10:00Z"
    finally:
        session.close()


@pytest.mark.asyncio
async def test_collects_default_target_sports_venues_and_associated_events():
    class FakeDiscovery(SeatGeekDiscovery):
        requested_max_pages = []

        async def resolve_venue(self, display_name):
            return {
                "display_name": display_name,
                "source_venue_id": {
                    "Dodger Stadium": "8",
                    "Crypto.com Arena": "9",
                    "Intuit Dome": "500",
                }[display_name],
                "city": "Los Angeles",
                "timezone": "America/Los_Angeles",
            }

        async def fetch_events_for_venue(self, source_venue_id, **kwargs):
            self.requested_max_pages.append(kwargs.get("max_pages"))
            return [
                {
                    "id": int(source_venue_id) * 100,
                    "title": f"Event at venue {source_venue_id}",
                    "datetime_utc": "2026-09-01T03:00:00Z",
                    "url": f"https://seatgeek.test/event/{source_venue_id}",
                    "venue": {"name": f"Venue {source_venue_id}"},
                    "performers": [],
                }
            ]

    result = await FakeDiscovery().collect_target_sports_venues_and_events(
        ["Dodger Stadium", "Crypto.com Arena", "Intuit Dome"]
    )

    session = SessionLocal()
    try:
        assert result == {"venues_seeded": 3, "venues_resolved": 3, "events_upserted": 3}
        assert session.query(Venue).count() == 3
        assert session.query(SourceEvent).count() == 3
        assert {
            event.venue_id for event in session.query(SourceEvent).all()
        } == {venue.id for venue in session.query(Venue).all()}
        assert FakeDiscovery.requested_max_pages == [10, 10, 10]
    finally:
        session.close()


@pytest.mark.asyncio
async def test_collects_profile_venues_when_no_explicit_targets_are_passed():
    await seed_profile(
        ProfileSpec(
            slug="default",
            display_name="Default Tix Profile",
            home_city="Seattle",
            sports=["Mariners"],
            venues=[
                VenuePreference(display_name="T-Mobile Park", city="Seattle", source_venue_id="100"),
                VenuePreference(display_name="Climate Pledge Arena", city="Seattle", source_venue_id="200"),
            ],
        )
    )

    class FakeDiscovery(SeatGeekDiscovery):
        requested_venues = []

        async def resolve_venue(self, display_name):
            self.requested_venues.append(display_name)
            return {
                "display_name": display_name,
                "source_venue_id": {"T-Mobile Park": "100", "Climate Pledge Arena": "200"}[display_name],
                "city": "Seattle",
                "timezone": "America/Los_Angeles",
            }

        async def fetch_events_for_venue(self, source_venue_id, **kwargs):
            return [
                {
                    "id": int(source_venue_id),
                    "title": f"Event {source_venue_id}",
                    "datetime_utc": "2026-09-01T03:00:00Z",
                    "url": f"https://seatgeek.test/event/{source_venue_id}",
                    "venue": {"name": f"Venue {source_venue_id}"},
                    "performers": [],
                }
            ]

    result = await FakeDiscovery().collect_target_sports_venues_and_events()

    assert FakeDiscovery.requested_venues == ["T-Mobile Park", "Climate Pledge Arena"]
    assert result["venues_seeded"] == 2
    assert result["events_upserted"] == 2
