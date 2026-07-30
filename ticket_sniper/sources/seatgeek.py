import json
import hashlib
from typing import List, Dict, Any, Tuple
from ticket_sniper.sources.base import BaseSourceAdapter

ADAPTER_VERSION = "seatgeek-listings-v1"
PARSER_VERSION = "seatgeek-fixture-v1"


def _amount(value: Dict[str, Any] | None) -> float | None:
    if not value:
        return None
    amount = value.get("amount")
    return float(amount) if amount is not None else None


class SeatGeekAdapter(BaseSourceAdapter):
    @property
    def source_name(self) -> str: return "seatgeek"

    def parse_inventory(self, raw_body: str, source_event_id: str) -> Tuple[List[Dict[str, Any]], int, bool]:
        data = json.loads(raw_body)
        listings = data.get("listings", [])
        parsed = []
        for item in listings:
            all_in = _amount(item.get("price_with_fees"))
            listed = _amount(item.get("price"))
            payload = json.dumps(item, sort_keys=True, separators=(",", ":"))
            parsed.append({
                "source_listing_id": str(item["id"]),
                "source_event_id": source_event_id,
                "raw_section": item.get("section"),
                "normalized_section": item.get("section"),
                "raw_row": item.get("row"),
                "quantity_available": int(item.get("quantity") or 1),
                "available_quantities_json": json.dumps(item.get("splits", []), sort_keys=True),
                "unit_price_listed": listed,
                "unit_fee_amount": (all_in - listed) if all_in is not None and listed is not None else None,
                "unit_price_all_in": all_in,
                "price_basis": "all_in" if all_in is not None else "listed",
                "fee_confidence": "high" if all_in is not None else "low",
                "currency": "USD",
                "listing_url": item.get("url") or "",
                "payload_hash": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                "adapter_version": ADAPTER_VERSION,
                "parser_version": PARSER_VERSION,
            })
        return parsed, len(parsed), True
