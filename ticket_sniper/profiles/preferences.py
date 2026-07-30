from dataclasses import dataclass, field
from typing import Any

from ticket_sniper.config import settings
from ticket_sniper.db.models import ProfileSport, ProfileVenue, UserProfile, utcnow_str
from ticket_sniper.db.session import run_db_transaction

DEFAULT_PROFILE_SLUG = "default"


@dataclass(frozen=True)
class VenuePreference:
    display_name: str
    city: str | None = "Los Angeles"
    source: str = "seatgeek"
    source_venue_id: str | None = None
    timezone: str = "America/Los_Angeles"


@dataclass(frozen=True)
class ProfileSpec:
    slug: str = DEFAULT_PROFILE_SLUG
    display_name: str = "Default Tix Profile"
    home_city: str = "Los Angeles"
    timezone: str = "America/Los_Angeles"
    default_source: str = "seatgeek"
    preferred_quantity: int = 2
    max_unit_price_all_in: float | None = 150.0
    max_order_total: float | None = 300.0
    sports: list[str] = field(default_factory=lambda: ["Dodgers", "Lakers", "Clippers", "Kings"])
    venues: list[VenuePreference] = field(
        default_factory=lambda: [
            VenuePreference("Dodger Stadium", source_venue_id="demo-dodger-stadium"),
            VenuePreference("Crypto.com Arena", source_venue_id="demo-crypto-arena"),
            VenuePreference("Intuit Dome", source_venue_id="demo-intuit-dome"),
            VenuePreference("BMO Stadium", source_venue_id="demo-bmo-stadium"),
            VenuePreference("Hollywood Bowl", source_venue_id="demo-hollywood-bowl"),
        ]
    )


def default_profile_spec() -> ProfileSpec:
    return ProfileSpec()


async def seed_profile(spec: ProfileSpec | None = None) -> dict[str, int]:
    profile_spec = spec or default_profile_spec()

    def _seed(session):
        created = {"profiles": 0, "sports": 0, "venues": 0}
        now = utcnow_str()
        profile = session.query(UserProfile).filter_by(slug=profile_spec.slug).one_or_none()
        if profile is None:
            profile = UserProfile(slug=profile_spec.slug, created_at=now)
            session.add(profile)
            created["profiles"] += 1

        profile.display_name = profile_spec.display_name
        profile.home_city = profile_spec.home_city
        profile.timezone = profile_spec.timezone
        profile.default_source = profile_spec.default_source
        profile.preferred_quantity = profile_spec.preferred_quantity
        profile.max_unit_price_all_in = profile_spec.max_unit_price_all_in
        profile.max_order_total = profile_spec.max_order_total
        profile.enabled = 1
        profile.updated_at = now
        session.flush()

        for index, sport_name in enumerate(profile_spec.sports):
            sport = (
                session.query(ProfileSport)
                .filter_by(profile_id=profile.id, sport_name=sport_name)
                .one_or_none()
            )
            if sport is None:
                sport = ProfileSport(profile_id=profile.id, sport_name=sport_name, created_at=now)
                session.add(sport)
                created["sports"] += 1
            sport.enabled = 1
            sport.sort_order = index
            sport.updated_at = now

        for index, venue_spec in enumerate(profile_spec.venues):
            venue = (
                session.query(ProfileVenue)
                .filter_by(
                    profile_id=profile.id,
                    source=venue_spec.source,
                    display_name=venue_spec.display_name,
                )
                .one_or_none()
            )
            if venue is None:
                venue = ProfileVenue(
                    profile_id=profile.id,
                    source=venue_spec.source,
                    display_name=venue_spec.display_name,
                    created_at=now,
                )
                session.add(venue)
                created["venues"] += 1
            venue.source_venue_id = venue_spec.source_venue_id
            venue.city = venue_spec.city
            venue.timezone = venue_spec.timezone
            venue.enabled = 1
            venue.sort_order = index
            venue.updated_at = now

        return created

    return await run_db_transaction(_seed)


async def load_active_profile(slug: str = DEFAULT_PROFILE_SLUG) -> dict[str, Any] | None:
    def _load(session):
        profile = session.query(UserProfile).filter_by(slug=slug, enabled=1).one_or_none()
        if profile is None:
            return None
        sports = (
            session.query(ProfileSport)
            .filter_by(profile_id=profile.id, enabled=1)
            .order_by(ProfileSport.sort_order.asc(), ProfileSport.sport_name.asc())
            .all()
        )
        venues = (
            session.query(ProfileVenue)
            .filter_by(profile_id=profile.id, enabled=1)
            .order_by(ProfileVenue.sort_order.asc(), ProfileVenue.display_name.asc())
            .all()
        )
        return {
            "id": profile.id,
            "slug": profile.slug,
            "display_name": profile.display_name,
            "home_city": profile.home_city,
            "timezone": profile.timezone,
            "default_source": profile.default_source,
            "preferred_quantity": profile.preferred_quantity,
            "max_unit_price_all_in": profile.max_unit_price_all_in,
            "max_order_total": profile.max_order_total,
            "sports": [sport.sport_name for sport in sports],
            "venues": [
                {
                    "display_name": venue.display_name,
                    "source": venue.source,
                    "source_venue_id": venue.source_venue_id,
                    "city": venue.city,
                    "timezone": venue.timezone,
                }
                for venue in venues
            ],
        }

    return await run_db_transaction(_load)


async def get_target_venue_names(slug: str = DEFAULT_PROFILE_SLUG) -> list[str]:
    profile = await load_active_profile(slug)
    if profile and profile["venues"]:
        return [venue["display_name"] for venue in profile["venues"]]
    return list(settings.TARGET_SPORTS_VENUES)
