import json
import logging
import httpx
from datetime import datetime
from zoneinfo import ZoneInfo
from ticket_sniper.config import settings
from ticket_sniper.db.models import AlertOutbox, AlertState, utcnow_str
from ticket_sniper.db.session import run_db_transaction

logger = logging.getLogger(__name__)

async def drain_alert_outbox():
    def _fetch_pending(session):
        return session.query(AlertOutbox).filter(AlertOutbox.status == "pending", AlertOutbox.next_attempt_at <= utcnow_str()).limit(10).all()

    pending = await run_db_transaction(_fetch_pending)
    if not pending: return

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=10.0) as client:
        for item in pending:
            payload = json.loads(item.payload_json)
            body = {"chat_id": settings.TELEGRAM_CHAT_ID, "text": payload.get("text", "Ticket Alert!"), "parse_mode": "HTML"}
            try:
                resp = await client.post(url, json=body)
                if resp.status_code == 200:
                    def _confirm(session):
                        row = session.query(AlertOutbox).get(item.id)
                        row.status = "sent"
                        row.sent_at = utcnow_str()
                    await run_db_transaction(_confirm)
            except Exception as e:
                logger.error(f"Telegram error: {e}")
