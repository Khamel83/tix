import json
import logging
import httpx
from ticket_sniper.config import settings
from ticket_sniper.notifications.worker import process_pending_outbox

logger = logging.getLogger(__name__)


def telegram_credentials_available() -> bool:
    token = settings.TELEGRAM_BOT_TOKEN or ""
    chat_id = settings.TELEGRAM_CHAT_ID or ""
    placeholders = {"test-token", "replace-me", "changeme", "dummy", "placeholder"}
    return bool(token and chat_id and token not in placeholders and chat_id not in {"test-chat", "replace-me", "changeme"})


async def send_telegram_payload(payload: dict) -> None:
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    body = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": payload.get("text", "Ticket Alert!"),
        "parse_mode": payload.get("parse_mode", "HTML"),
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=body)
        resp.raise_for_status()


async def drain_alert_outbox():
    return await process_pending_outbox()
