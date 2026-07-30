import pytest

from ticket_sniper.db.models import ProfileSport, ProfileVenue, UserProfile
from ticket_sniper.db.session import SessionLocal
from ticket_sniper.profiles.preferences import (
    ProfileSpec,
    VenuePreference,
    get_target_venue_names,
    load_active_profile,
    seed_profile,
)


@pytest.mark.asyncio
async def test_seed_default_profile_stores_sports_and_venues():
    summary = await seed_profile()

    session = SessionLocal()
    try:
        profile = session.query(UserProfile).filter_by(slug="default").one()
        sports = [row.sport_name for row in session.query(ProfileSport).order_by(ProfileSport.sort_order).all()]
        venues = [row.display_name for row in session.query(ProfileVenue).order_by(ProfileVenue.sort_order).all()]
        assert summary == {"profiles": 1, "sports": 4, "venues": 5}
        assert profile.display_name == "Default Tix Profile"
        assert sports == ["Dodgers", "Lakers", "Clippers", "Kings"]
        assert venues[:2] == ["Dodger Stadium", "Crypto.com Arena"]
        assert "Hollywood Bowl" in venues
    finally:
        session.close()


@pytest.mark.asyncio
async def test_alternate_profile_drives_target_venue_names():
    await seed_profile(
        ProfileSpec(
            slug="seattle",
            display_name="Seattle Profile",
            home_city="Seattle",
            sports=["Mariners"],
            venues=[
                VenuePreference(display_name="T-Mobile Park", city="Seattle", source_venue_id="seattle-1"),
                VenuePreference(display_name="Climate Pledge Arena", city="Seattle"),
            ],
        )
    )

    venues = await get_target_venue_names("seattle")
    profile = await load_active_profile("seattle")

    assert venues == ["T-Mobile Park", "Climate Pledge Arena"]
    assert profile["home_city"] == "Seattle"
    assert profile["sports"] == ["Mariners"]


@pytest.mark.asyncio
async def test_seed_profile_is_idempotent_and_updates_existing_preferences():
    await seed_profile(
        ProfileSpec(
            slug="default",
            display_name="Default Tix Profile",
            home_city="Los Angeles",
            sports=["Dodgers"],
            venues=[VenuePreference(display_name="Dodger Stadium", city="Los Angeles")],
        )
    )
    summary = await seed_profile(
        ProfileSpec(
            slug="default",
            display_name="Updated Profile",
            home_city="Pasadena",
            sports=["Dodgers", "Galaxy"],
            venues=[
                VenuePreference(display_name="Dodger Stadium", city="Los Angeles"),
                VenuePreference(display_name="Rose Bowl", city="Pasadena"),
            ],
        )
    )

    session = SessionLocal()
    try:
        assert summary == {"profiles": 0, "sports": 1, "venues": 1}
        assert session.query(UserProfile).count() == 1
        assert session.query(ProfileSport).count() == 2
        assert session.query(ProfileVenue).count() == 2
        assert session.query(UserProfile).one().home_city == "Pasadena"
    finally:
        session.close()
