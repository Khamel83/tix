import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any, Dict, List, Tuple, cast

from ticket_sniper.sources.base import BaseSourceAdapter

ADAPTER_VERSION = "seatgeek-listings-v1"
PARSER_VERSION = "seatgeek-fixture-v1"
_SCRIPT_RE = re.compile(r"<script\b[^>]*>(.*?)</script\s*>", re.IGNORECASE | re.DOTALL)
_MISSING = object()


def _json_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("SeatGeek response JSON is not serializable") from exc


def normalize_scrapling_response(response: Any) -> str:
    """Convert Scrapling JSON or rendered responses to adapter input text."""
    if response is None:
        raise ValueError("SeatGeek response is empty")
    if isinstance(response, (str, bytes)):
        body = _json_text(response)
        if not body.strip():
            raise ValueError("SeatGeek response is empty")
        return body
    if isinstance(response, Mapping):
        if "listings" in response:
            return _json_text(response)
        for key in ("body", "text", "content", "page_source"):
            if key in response:
                return normalize_scrapling_response(response[key])
        return _json_text(response)

    json_value = getattr(response, "json", _MISSING)
    if json_value is not _MISSING:
        try:
            payload = json_value() if callable(json_value) else json_value
        except (TypeError, ValueError):
            payload = _MISSING
        if payload is not _MISSING and payload is not None:
            return normalize_scrapling_response(payload)

    for key in ("text", "body", "content", "page_source"):
        value = getattr(response, key, _MISSING)
        if value is not _MISSING and value is not None:
            return normalize_scrapling_response(value)
    raise ValueError("Unsupported SeatGeek response type")


def _amount(value: Dict[str, Any] | None) -> float | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("SeatGeek response contains malformed price data")
    amount = value.get("amount")
    return float(amount) if amount is not None else None


def _listing_data_from_scripts(raw_body: str) -> Dict[str, Any]:
    decoder = json.JSONDecoder()
    for match in _SCRIPT_RE.finditer(raw_body):
        script = match.group(1).strip()
        for index, char in enumerate(script):
            if char not in "[{":
                continue
            try:
                payload, _ = decoder.raw_decode(script[index:])
            except json.JSONDecodeError:
                continue
            listing_data = _find_listing_data(payload)
            if listing_data is not None:
                return listing_data
    raise ValueError("No listing JSON found in rendered SeatGeek HTML")


def _find_listing_data(payload: Any) -> Dict[str, Any] | None:
    if isinstance(payload, dict):
        if isinstance(payload.get("listings"), list):
            return payload
        for value in payload.values():
            listing_data = _find_listing_data(value)
            if listing_data is not None:
                return listing_data
    elif isinstance(payload, list):
        for value in payload:
            listing_data = _find_listing_data(value)
            if listing_data is not None:
                return listing_data
    return None


def _pagination_complete(data: Dict[str, Any]) -> bool:
    if "pagination_complete" in data:
        return bool(data["pagination_complete"])
    pagination = data.get("pagination")
    if isinstance(pagination, Mapping):
        if "complete" in pagination:
            return bool(pagination["complete"])
        if "has_next" in pagination:
            return not bool(pagination["has_next"])
        if "next" in pagination:
            return not bool(pagination["next"])
    return True


def _inventory_data(raw_body: Any) -> Dict[str, Any]:
    body = normalize_scrapling_response(raw_body)
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        data = _listing_data_from_scripts(body)
    if not isinstance(data, dict):
        raise ValueError("SeatGeek response is not an inventory object")
    if "listings" not in data:
        nested = _find_listing_data(data)
        if nested is not None:
            if "pagination_complete" in data and "pagination_complete" not in nested:
                nested = {**nested, "pagination_complete": data["pagination_complete"]}
            elif "pagination" in data and "pagination" not in nested:
                nested = {**nested, "pagination": data["pagination"]}
            data = nested
        else:
            raise ValueError("SeatGeek response contains no inventory listings")
    listings = data["listings"]
    if not isinstance(listings, list) or not listings:
        raise ValueError("SeatGeek response contains no inventory listings")
    if any(not isinstance(item, dict) for item in listings):
        raise ValueError("SeatGeek response contains malformed inventory listings")
    if any(not item.get("id") for item in listings):
        raise ValueError("SeatGeek response contains listings without an id")
    return data


class SeatGeekAdapter(BaseSourceAdapter):
    @property
    def source_name(self) -> str:
        return "seatgeek"

    def parse_inventory(self, raw_body: Any, source_event_id: str) -> Tuple[List[Dict[str, Any]], int, bool]:
        data = _inventory_data(raw_body)
        listings = cast(List[Dict[str, Any]], data["listings"])
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
        return parsed, len(parsed), _pagination_complete(data)
