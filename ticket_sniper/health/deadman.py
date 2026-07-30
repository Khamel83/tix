import logging
import json
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
        msg = f"Ticket-Sniper Operator Alert\n\n{reason}"

        def _enqueue(session):
            key = f"deadman:tier2:{settings.DEADMAN_HOURS}"
            existing = session.query(AlertOutbox).filter_by(dedupe_key=key, status="pending").one_or_none()
            if existing is None:
                session.add(
                    AlertOutbox(
                        payload_json=json.dumps({"text": msg, "source": "deadman"}, sort_keys=True),
                        dedupe_key=key,
                    )
                )

        await run_db_transaction(_enqueue)
