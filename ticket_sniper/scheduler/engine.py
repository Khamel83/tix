import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from ticket_sniper.db.session import engine
from ticket_sniper.discovery.seatgeek import SeatGeekDiscovery
from ticket_sniper.notifications.worker import process_pending_outbox
from ticket_sniper.health.deadman import run_deadman_switch_check
from ticket_sniper.config import settings
from ticket_sniper.scheduler.event_polling import reconcile_event_poll_jobs

logger = logging.getLogger(__name__)

jobstores = {'default': SQLAlchemyJobStore(engine=engine)}
scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="UTC")

async def discover_target_sports_events():
    result = await SeatGeekDiscovery().collect_target_sports_venues_and_events()
    logger.info("Target sports discovery completed: %s", result)

async def reconcile_dynamic_event_polling():
    await reconcile_event_poll_jobs(scheduler)

def start_scheduler():
    scheduler.add_job(process_pending_outbox, 'interval', seconds=10, id='outbox_drain', replace_existing=True)
    scheduler.add_job(run_deadman_switch_check, 'interval', hours=1, id='deadman_check', replace_existing=True)
    scheduler.add_job(discover_target_sports_events, 'interval', hours=6, id='target_sports_discovery', replace_existing=True)
    scheduler.add_job(
        reconcile_dynamic_event_polling,
        'interval',
        seconds=settings.EVENT_POLL_RECONCILE_SECONDS,
        id='dynamic_event_poll_reconcile',
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.start()
