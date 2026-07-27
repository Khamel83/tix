import logging
import httpx
from typing import Optional, Dict, Any
from ticket_sniper.config import settings
from ticket_sniper.db.models import SourceEvent, utcnow_str
from ticket_sniper.db.session import run_db_transaction

logger = logging.getLogger(__name__)
SEATGEEK_API_BASE = "https://api.seatgeek.com/2"

class SeatGeekDiscovery:
    def __init__(self):
        self.client_id = settings.SEATGEEK_CLIENT_ID

    async def resolve_venue(self, display_name: str) -> Optional[Dict[str, Any]]:
        url = f"{SEATGEEK_API_BASE}/venues"
        params = {"q": display_name, "client_id": self.client_id}
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(url, params=params)
                if resp.status_code != 200: return None
                venues = resp.json().get("venues", [])
                if not venues: return None
                top = venues[0]
                return {
                    "source_venue_id": str(top["id"]),
                    "display_name": display_name,
                    "city": top.get("city"),
                    "timezone": top.get("timezone", "America/Los_Angeles")
                }
            except Exception as e:
                logger.error(f"Failed resolving venue {display_name}: {e}")
                return None
