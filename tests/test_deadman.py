import json

import pytest

from ticket_sniper.db.models import AlertOutbox
from ticket_sniper.db.session import SessionLocal
from ticket_sniper.health.deadman import run_deadman_switch_check


@pytest.mark.asyncio
async def test_deadman_enqueues_outbox_row_instead_of_direct_send():
    await run_deadman_switch_check()

    session = SessionLocal()
    try:
        row = session.query(AlertOutbox).one()
        assert row.dedupe_key.startswith("deadman:tier2")
        assert "Ticket-Sniper Operator Alert" in json.loads(row.payload_json)["text"]
    finally:
        session.close()
