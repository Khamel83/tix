import logging
import httpx
from datetime import datetime, timezone, timedelta
from ticket_sniper.config import settings
from ticket_sniper.db.models import PollRun, AlertOutbox
from ticket_sniper.db.session import run_db_transaction

logger = logging.getLogger(__name__)

async def run_deadman_switch_check():
    def _inspect_health(session):
        now = datetime.now(timezone.utc)
        threshold = (now - timedelta(hours=settings.DEADMAN_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")
        last_tier2 = session.query(PollRun).filter(PollRun.tier == 2, PollRun.status == "success").order_by(PollRun.started_at.desc()).first()
        if not last_tier2 or last_tier2.started_at < threshold:
            return True, f"No Tier 2 success in {settings.DEADMAN_HOURS}h."
        return False, ""

    triggered, reason = await run_db_transaction(_inspect_health)
    if triggered:
        msg = f"⚠️ <b>Ticket-Sniper Operator Alert</b>\n\n{reason}"
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                await client.post(url, json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"})
            except Exception as e:
                logger.error(f"Failed dispatching deadman alert: {e}")
