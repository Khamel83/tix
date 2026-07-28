import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ticket_sniper.config import settings
from ticket_sniper.db.models import (
    EventPriceSnapshot,
    PollRun,
    SourceEvent,
    utcnow_str,
)
from ticket_sniper.db.session import run_db_transaction
from ticket_sniper.discovery.seatgeek import SeatGeekDiscovery

logger = logging.getLogger(__name__)

EVENT_POLL_JOB_PREFIX = "event_poll:"


@dataclass(frozen=True)
class PollCadence:
    tier: int
    interval_seconds: int
    reason: str


@dataclass(frozen=True)
class PollCandidate:
    source: str
    source_event_id: str
    starts_at_utc: str
    cadence: PollCadence


def parse_utc_datetime(value: str) -> datetime:
    normalized = value
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def poll_cadence_for_event(starts_at_utc: str, now: Optional[datetime] = None) -> Optional[PollCadence]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    starts_at = parse_utc_datetime(starts_at_utc)
    seconds_until_start = (starts_at - now).total_seconds()
    if seconds_until_start <= 0:
        return None

    if seconds_until_start <= 24 * 60 * 60:
        return PollCadence(
            tier=2,
            interval_seconds=settings.EVENT_POLL_FINAL_DAY_INTERVAL_SECONDS,
            reason="within_1_day",
        )
    if seconds_until_start <= settings.EVENT_POLL_NEAR_TERM_DAYS * 24 * 60 * 60:
        return PollCadence(
            tier=2,
            interval_seconds=settings.EVENT_POLL_NEAR_TERM_INTERVAL_SECONDS,
            reason="near_term",
        )
    if seconds_until_start <= settings.EVENT_POLL_APPROACHING_DAYS * 24 * 60 * 60:
        return PollCadence(
            tier=1,
            interval_seconds=settings.EVENT_POLL_APPROACHING_INTERVAL_SECONDS,
            reason="approaching",
        )
    return PollCadence(
        tier=0,
        interval_seconds=settings.EVENT_POLL_BASE_INTERVAL_SECONDS,
        reason="standard",
    )


async def load_poll_candidates(now: Optional[datetime] = None) -> List[PollCandidate]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    def _load(session):
        events = (
            session.query(SourceEvent)
            .filter(SourceEvent.status == "active")
            .order_by(SourceEvent.starts_at_utc.asc())
            .all()
        )
        candidates = []
        for event in events:
            try:
                cadence = poll_cadence_for_event(event.starts_at_utc, now)
            except ValueError:
                logger.warning(
                    "Skipping event %s:%s with invalid starts_at_utc=%r",
                    event.source,
                    event.source_event_id,
                    event.starts_at_utc,
                )
                continue
            if cadence is None:
                continue
            candidates.append(
                PollCandidate(
                    source=event.source,
                    source_event_id=event.source_event_id,
                    starts_at_utc=event.starts_at_utc,
                    cadence=cadence,
                )
            )
        return candidates

    return await run_db_transaction(_load)


def event_poll_job_id(source: str, source_event_id: str) -> str:
    return f"{EVENT_POLL_JOB_PREFIX}{source}:{source_event_id}"


async def poll_event_ticket_data(source: str, source_event_id: str, tier: int) -> None:
    if source != "seatgeek":
        raise ValueError(f"Unsupported event poll source: {source}")

    def _start(session):
        run = PollRun(
            tier=tier,
            source=source,
            source_event_id=source_event_id,
            status="running",
        )
        session.add(run)
        session.flush()
        return run.id

    run_id = await run_db_transaction(_start)
    try:
        event = await SeatGeekDiscovery().fetch_event(source_event_id)
        stats = event.get("stats") or {}
        listing_count = int(stats.get("listing_count") or 0)

        def _complete(session):
            session.add(
                EventPriceSnapshot(
                    source=source,
                    source_event_id=source_event_id,
                    lowest_price=stats.get("lowest_price"),
                    average_price=stats.get("average_price"),
                    highest_price=stats.get("highest_price"),
                    listing_count=listing_count,
                    visible_listing_count=stats.get("visible_listing_count"),
                    gate_decision="not_evaluated",
                    gate_reason="aggregate_event_stats",
                )
            )
            run = session.get(PollRun, run_id)
            run.status = "success"
            run.completed_at = utcnow_str()
            run.pagination_complete = 1
            run.inventory_count = listing_count
            run.parser_version = "seatgeek-event-stats-v1"

        await run_db_transaction(_complete)
        logger.info(
            "Ticket data poll completed for %s:%s at tier %s with %s listings",
            source,
            source_event_id,
            tier,
            listing_count,
        )
    except Exception as exc:
        def _fail(session):
            run = session.get(PollRun, run_id)
            run.status = "failed"
            run.completed_at = utcnow_str()
            run.error_code = exc.__class__.__name__
            run.error_summary = "SeatGeek event statistics poll failed"

        await run_db_transaction(_fail)
        raise


def _job_interval_seconds(job: Any) -> Optional[int]:
    interval = getattr(getattr(job, "trigger", None), "interval", None)
    if interval is None:
        return None
    return int(interval.total_seconds())


def _job_args(job: Any) -> List[Any]:
    return list(getattr(job, "args", []) or [])


async def reconcile_event_poll_jobs(scheduler: Any, now: Optional[datetime] = None) -> Dict[str, int]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    candidates = await load_poll_candidates(now)
    desired_by_job_id = {
        event_poll_job_id(candidate.source, candidate.source_event_id): candidate
        for candidate in candidates
    }

    removed = 0
    for job in list(scheduler.get_jobs()):
        job_id = getattr(job, "id", "")
        if job_id.startswith(EVENT_POLL_JOB_PREFIX) and job_id not in desired_by_job_id:
            scheduler.remove_job(job_id)
            removed += 1

    scheduled = 0
    unchanged = 0
    for job_id, candidate in desired_by_job_id.items():
        expected_args = [candidate.source, candidate.source_event_id, candidate.cadence.tier]
        existing_job = scheduler.get_job(job_id)
        if (
            existing_job
            and _job_interval_seconds(existing_job) == candidate.cadence.interval_seconds
            and _job_args(existing_job) == expected_args
        ):
            unchanged += 1
            continue

        scheduler.add_job(
            poll_event_ticket_data,
            "interval",
            seconds=candidate.cadence.interval_seconds,
            id=job_id,
            args=expected_args,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            next_run_time=now,
        )
        scheduled += 1

    logger.info(
        "Event poll reconciliation complete: candidates=%s scheduled=%s unchanged=%s removed=%s",
        len(candidates),
        scheduled,
        unchanged,
        removed,
    )
    return {
        "candidates": len(candidates),
        "scheduled": scheduled,
        "unchanged": unchanged,
        "removed": removed,
    }
