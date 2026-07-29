import json
import hashlib
from typing import List, Dict, Any, Tuple
from ticket_sniper.sources.base import BaseSourceAdapter

class SeatGeekAdapter(BaseSourceAdapter):
    @property
    def source_name(self) -> str: return "seatgeek"

    def parse_inventory(self, raw_body: str, source_event_id: str) -> Tuple[List[Dict[str, Any]], int, bool]:
        data = json.loads(raw_body)
        listings = data.get("listings", [])
        parsed = []
        for item in listings:
            parsed.append({
                "source_listing_id": str(item["id"]),
                "quantity_available": item.get("quantity", 1),
                "unit_price_all_in": item.get("price_with_fees", {}).get("amount"),
                "price_basis": "all_in"
            })
        return parsed, len(parsed), True
