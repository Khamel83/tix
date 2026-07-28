import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from ticket_sniper.db.session import engine
from ticket_sniper.discovery.seatgeek import SeatGeekDiscovery
from ticket_sniper.notifications.telegram import drain_alert_outbox
from ticket_sniper.health.deadman import run_deadman_switch_check

logger = logging.getLogger(__name__)

jobstores = {'default': SQLAlchemyJobStore(engine=engine)}
scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="UTC")

async def discover_target_sports_events():
    result = await SeatGeekDiscovery().collect_target_sports_venues_and_events()
    logger.info("Target sports discovery completed: %s", result)

def start_scheduler():
    scheduler.add_job(drain_alert_outbox, 'interval', seconds=10, id='outbox_drain', replace_existing=True)
    scheduler.add_job(run_deadman_switch_check, 'interval', hours=1, id='deadman_check', replace_existing=True)
    scheduler.add_job(discover_target_sports_events, 'interval', hours=6, id='target_sports_discovery', replace_existing=True)
    scheduler.start()
