import os
import tempfile
from datetime import datetime, timezone, timedelta

os.environ.setdefault("SEATGEEK_CLIENT_ID", "test-client")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat")
os.environ.setdefault("ARGUS_BASE_URL", "http://argus.test")
os.environ.setdefault("DATABASE_PATH", tempfile.NamedTemporaryFile(delete=False).name)

import pytest

from ticket_sniper.scheduler import engine as scheduler_engine
from ticket_sniper.db.models import Base, EventPriceSnapshot, PollRun, SourceEvent
from ticket_sniper.db.session import SessionLocal, engine
from ticket_sniper.discovery.seatgeek import SeatGeekDiscovery
from ticket_sniper.scheduler.event_polling import (
    EVENT_POLL_JOB_PREFIX,
    event_poll_job_id,
    poll_cadence_for_event,
    poll_event_ticket_data,
    reconcile_event_poll_jobs,
)


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def utc_string(value):
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def add_event(source_event_id, starts_at_utc, status="active", source="seatgeek"):
    session = SessionLocal()
    try:
        session.add(
            SourceEvent(
                source=source,
                source_event_id=source_event_id,
                title=f"Event {source_event_id}",
                venue_name="Test Venue",
                starts_at_utc=utc_string(starts_at_utc),
                event_url=f"https://seatgeek.test/events/{source_event_id}",
                status=status,
            )
        )
        session.commit()
    finally:
        session.close()


class FakeInterval:
    def __init__(self, seconds):
        self._delta = timedelta(seconds=seconds)

    def total_seconds(self):
        return self._delta.total_seconds()


class FakeTrigger:
    def __init__(self, seconds):
        self.interval = FakeInterval(seconds)


class FakeJob:
    def __init__(self, job_id, seconds, args):
        self.id = job_id
        self.trigger = FakeTrigger(seconds)
        self.args = args


class FakeScheduler:
    def __init__(self):
        self.jobs = {}
        self.added_jobs = 0

    def get_jobs(self):
        return list(self.jobs.values())

    def get_job(self, job_id):
        return self.jobs.get(job_id)

    def add_job(self, func, trigger, seconds, id, args, **kwargs):
        self.added_jobs += 1
        self.jobs[id] = FakeJob(id, seconds, args)

    def remove_job(self, job_id):
        del self.jobs[job_id]


def test_poll_cadence_increases_as_event_approaches():
    now = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)

    standard = poll_cadence_for_event(utc_string(now + timedelta(days=14)), now)
    approaching = poll_cadence_for_event(utc_string(now + timedelta(days=6)), now)
    near_term = poll_cadence_for_event(utc_string(now + timedelta(days=2)), now)
    final_day = poll_cadence_for_event(utc_string(now + timedelta(hours=12)), now)

    assert standard.interval_seconds > approaching.interval_seconds
    assert approaching.interval_seconds > near_term.interval_seconds
    assert near_term.interval_seconds > final_day.interval_seconds
    assert near_term.tier == 2
    assert final_day.tier == 2


def test_dynamic_poll_reconciliation_runs_immediately_on_scheduler_start(monkeypatch):
    class FakeStartupScheduler:
        def __init__(self):
            self.jobs = {}
            self.started = False

        def add_job(self, func, trigger, **kwargs):
            self.jobs[kwargs["id"]] = kwargs

        def start(self):
            self.started = True

    fake_scheduler = FakeStartupScheduler()
    monkeypatch.setattr(scheduler_engine, "scheduler", fake_scheduler)
    before_start = datetime.now(timezone.utc)

    scheduler_engine.start_scheduler()

    reconcile_job = fake_scheduler.jobs["dynamic_event_poll_reconcile"]
    assert reconcile_job["next_run_time"] >= before_start
    assert fake_scheduler.started is True


@pytest.mark.asyncio
async def test_event_poll_fetches_and_persists_live_seatgeek_stats(monkeypatch):
    async def fake_fetch_event(self, source_event_id):
        assert source_event_id == "near-term"
        return {
            "stats": {
                "lowest_price": 81,
                "average_price": 127,
                "highest_price": 412,
                "listing_count": 93,
                "visible_listing_count": 88,
            }
        }

    monkeypatch.setattr(
        SeatGeekDiscovery,
        "fetch_event",
        fake_fetch_event,
        raising=False,
    )

    await poll_event_ticket_data("seatgeek", "near-term", tier=2)

    session = SessionLocal()
    try:
        snapshot = session.query(EventPriceSnapshot).one()
        poll_run = session.query(PollRun).one()
        assert snapshot.source_event_id == "near-term"
        assert snapshot.lowest_price == 81
        assert snapshot.listing_count == 93
        assert snapshot.visible_listing_count == 88
        assert poll_run.status == "success"
        assert poll_run.tier == 2
        assert poll_run.inventory_count == 93
        assert poll_run.pagination_complete == 1
    finally:
        session.close()


@pytest.mark.asyncio
async def test_reconcile_schedules_upcoming_events_with_dynamic_intervals():
    now = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
    add_event("standard", now + timedelta(days=14))
    add_event("near-term", now + timedelta(days=2))
    add_event("past", now - timedelta(hours=1))
    add_event("inactive", now + timedelta(hours=12), status="cancelled")
    add_event(
        "unsupported",
        now + timedelta(hours=12),
        source="stubhub",
    )

    scheduler = FakeScheduler()
    result = await reconcile_event_poll_jobs(scheduler, now)

    standard_job = scheduler.get_job(event_poll_job_id("seatgeek", "standard"))
    near_term_job = scheduler.get_job(event_poll_job_id("seatgeek", "near-term"))

    assert result == {"candidates": 2, "scheduled": 2, "unchanged": 0, "removed": 0}
    assert standard_job.trigger.interval.total_seconds() == 21600
    assert near_term_job.trigger.interval.total_seconds() == 900
    assert near_term_job.args == ["seatgeek", "near-term", 2]
    assert scheduler.get_job(event_poll_job_id("seatgeek", "past")) is None
    assert scheduler.get_job(event_poll_job_id("seatgeek", "inactive")) is None
    assert scheduler.get_job(event_poll_job_id("stubhub", "unsupported")) is None


@pytest.mark.asyncio
async def test_reconcile_removes_stale_event_poll_jobs():
    now = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
    scheduler = FakeScheduler()
    scheduler.jobs[f"{EVENT_POLL_JOB_PREFIX}seatgeek:stale"] = FakeJob(
        f"{EVENT_POLL_JOB_PREFIX}seatgeek:stale",
        900,
        ["seatgeek", "stale", 2],
    )

    result = await reconcile_event_poll_jobs(scheduler, now)

    assert result == {"candidates": 0, "scheduled": 0, "unchanged": 0, "removed": 1}
    assert scheduler.get_jobs() == []


@pytest.mark.asyncio
async def test_reconcile_leaves_unchanged_jobs_alone():
    now = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
    add_event("near-term", now + timedelta(days=2))
    scheduler = FakeScheduler()
    job_id = event_poll_job_id("seatgeek", "near-term")
    scheduler.jobs[job_id] = FakeJob(job_id, 900, ["seatgeek", "near-term", 2])

    result = await reconcile_event_poll_jobs(scheduler, now)

    assert result == {"candidates": 1, "scheduled": 0, "unchanged": 1, "removed": 0}
    assert scheduler.added_jobs == 0
