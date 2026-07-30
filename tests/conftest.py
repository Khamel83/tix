import os
import tempfile
from datetime import datetime, timezone

# Test modules must not import ticket_sniper modules before pytest loads this
# file. If a test needs unusual import timing, repeat these setdefault calls at
# that test file's top before importing application modules.
os.environ.setdefault("SEATGEEK_CLIENT_ID", "test-client")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat")
os.environ.setdefault("ARGUS_BASE_URL", "http://argus.test")
os.environ.setdefault("DATABASE_PATH", tempfile.NamedTemporaryFile(delete=False).name)
os.environ.setdefault("TIX_PROTOTYPE_MODE", "1")

import pytest

from ticket_sniper.db.models import Base, Rule, RuleSectionMatcher, SourceEvent, Venue
from ticket_sniper.db.session import SessionLocal, engine
from ticket_sniper.rules.evaluator import compute_rule_fingerprint


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def utc_string(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seed_event_and_rule(db_session):
    def _seed(
        *,
        source_event_id="demo-dodgers-001",
        venue_name="Dodger Stadium",
        rule_name="Dodgers two under 150",
        max_unit_price=150.0,
        max_order_total=300.0,
        section="Field 1",
    ):
        venue = Venue(display_name=venue_name, source="seatgeek", source_venue_id=venue_name)
        db_session.add(venue)
        db_session.flush()
        event = SourceEvent(
            source="seatgeek",
            source_event_id=source_event_id,
            venue_id=venue.id,
            title=f"{venue_name} Demo Event",
            venue_name=venue_name,
            starts_at_utc="2026-08-15T02:10:00Z",
            event_url=f"https://example.test/events/{source_event_id}",
            status="active",
        )
        db_session.add(event)
        rule = Rule(
            name=rule_name,
            enabled=1,
            scope_type="venue",
            scope_venue_id=venue.id,
            max_unit_price_all_in=max_unit_price,
            max_order_total=max_order_total,
            quantity_mode="exact",
            quantity_value=2,
            minimum_fee_confidence="medium",
            rule_fingerprint="pending",
        )
        db_session.add(rule)
        db_session.flush()
        matcher = RuleSectionMatcher(
            rule_id=rule.id,
            action="include",
            matcher_type="exact",
            matcher_value=section,
            sort_order=0,
        )
        db_session.add(matcher)
        db_session.flush()
        rule.rule_fingerprint = compute_rule_fingerprint(rule, [matcher])
        db_session.commit()
        return venue, event, rule

    return _seed
