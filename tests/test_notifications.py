import json

import pytest

from ticket_sniper.db.models import AlertOutbox, utcnow_str
from ticket_sniper.db.session import SessionLocal
from ticket_sniper.notifications.worker import process_pending_outbox


def add_outbox():
    session = SessionLocal()
    try:
        row = AlertOutbox(payload_json=json.dumps({"text": "hello"}), dedupe_key="k")
        session.add(row)
        session.commit()
        return row.id
    finally:
        session.close()


@pytest.mark.asyncio
async def test_placeholder_credentials_mark_outbox_skipped():
    outbox_id = add_outbox()

    result = await process_pending_outbox()

    session = SessionLocal()
    try:
        row = session.get(AlertOutbox, outbox_id)
        assert result["skipped_no_credentials"] == 1
        assert row.status == "skipped_no_credentials"
        assert json.loads(row.payload_json)["text"] == "hello"
    finally:
        session.close()


@pytest.mark.asyncio
async def test_failed_telegram_send_records_attempt_and_error(monkeypatch):
    import ticket_sniper.notifications.telegram as telegram

    monkeypatch.setattr(telegram, "telegram_credentials_available", lambda: True)

    async def fail(payload):
        raise RuntimeError("telegram down")

    monkeypatch.setattr(telegram, "send_telegram_payload", fail)
    outbox_id = add_outbox()

    result = await process_pending_outbox()

    session = SessionLocal()
    try:
        row = session.get(AlertOutbox, outbox_id)
        assert result["failed"] == 1
        assert row.status == "pending"
        assert row.attempts == 1
        assert "telegram down" in row.last_error
        assert row.next_attempt_at > utcnow_str()
    finally:
        session.close()
