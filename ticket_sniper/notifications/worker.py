import json
import logging
from datetime import datetime, timedelta, timezone

from ticket_sniper.db.models import AlertOutbox, utcnow_str
from ticket_sniper.db.session import run_db_transaction

logger = logging.getLogger(__name__)


def _next_attempt_after(attempts: int) -> str:
    seconds = min(300, 30 * max(1, attempts))
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


async def process_pending_outbox(limit: int = 10) -> dict:
    from ticket_sniper.notifications.telegram import send_telegram_payload, telegram_credentials_available

    def _fetch_pending(session):
        return [
            row.id
            for row in session.query(AlertOutbox)
            .filter(AlertOutbox.status == "pending", AlertOutbox.next_attempt_at <= utcnow_str())
            .order_by(AlertOutbox.created_at.asc())
            .limit(limit)
            .all()
        ]

    ids = await run_db_transaction(_fetch_pending)
    sent = failed = skipped = 0
    if not ids:
        return {"processed": 0, "sent": 0, "failed": 0, "skipped_no_credentials": 0}

    if not telegram_credentials_available():
        logger.warning("Skipping Telegram delivery because credentials are placeholders or missing")

        def _skip(session):
            for outbox_id in ids:
                row = session.get(AlertOutbox, outbox_id)
                if row and row.status == "pending":
                    row.status = "skipped_no_credentials"

        await run_db_transaction(_skip)
        return {"processed": len(ids), "sent": 0, "failed": 0, "skipped_no_credentials": len(ids)}

    for outbox_id in ids:
        def _load(session):
            row = session.get(AlertOutbox, outbox_id)
            return json.loads(row.payload_json) if row else None

        payload = await run_db_transaction(_load)
        if payload is None:
            continue
        try:
            await send_telegram_payload(payload)

            def _mark_sent(session):
                row = session.get(AlertOutbox, outbox_id)
                if row:
                    row.status = "sent"
                    row.sent_at = utcnow_str()

            await run_db_transaction(_mark_sent)
            sent += 1
        except Exception as exc:
            def _mark_failed(session):
                row = session.get(AlertOutbox, outbox_id)
                if row:
                    row.attempts += 1
                    row.last_error = str(exc)
                    row.next_attempt_at = _next_attempt_after(row.attempts)

            await run_db_transaction(_mark_failed)
            failed += 1

    return {"processed": len(ids), "sent": sent, "failed": failed, "skipped_no_credentials": skipped}
