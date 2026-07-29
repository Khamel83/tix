import json
import hashlib
from dataclasses import dataclass
from typing import List
from ticket_sniper.db.models import Rule, RuleSectionMatcher, ListingCurrent


@dataclass(frozen=True)
class EvaluationResult:
    qualifies: bool
    reason_vector: list[str]
    reason_fingerprint: str


def compute_rule_fingerprint(rule: Rule, matchers: List[RuleSectionMatcher]) -> str:
    sorted_matchers = sorted(matchers, key=lambda x: x.sort_order)
    payload = {
        "max_unit_price_all_in": rule.max_unit_price_all_in,
        "quantity_mode": rule.quantity_mode,
        "quantity_value": rule.quantity_value,
        "matchers": [{"action": m.action, "type": m.matcher_type, "value": m.matcher_value} for m in sorted_matchers]
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _fingerprint(reasons: list[str]) -> str:
    return hashlib.sha256(json.dumps(sorted(reasons), sort_keys=True).encode("utf-8")).hexdigest()


def _section_matches(matcher: RuleSectionMatcher, section: str | None) -> bool:
    if section is None:
        return False
    if matcher.matcher_type == "exact":
        return section.casefold() == matcher.matcher_value.casefold()
    if matcher.matcher_type == "contains":
        return matcher.matcher_value.casefold() in section.casefold()
    return False


def evaluate_listing(rule: Rule, matchers: list[RuleSectionMatcher], listing: ListingCurrent) -> EvaluationResult:
    reasons: list[str] = []
    qualifies = True

    include_matchers = [m for m in matchers if m.action == "include"]
    exclude_matchers = [m for m in matchers if m.action == "exclude"]
    section = listing.normalized_section or listing.raw_section
    if include_matchers:
        included = any(_section_matches(m, section) for m in include_matchers)
        reasons.append("section:included" if included else "section:not_included")
        qualifies = qualifies and included
    else:
        reasons.append("section:any")
    if any(_section_matches(m, section) for m in exclude_matchers):
        reasons.append("section:excluded")
        qualifies = False

    requested_qty = int(rule.quantity_value or 1)
    if rule.quantity_mode == "exact":
        splits = None
        if listing.available_quantities_json:
            try:
                splits = json.loads(listing.available_quantities_json)
            except json.JSONDecodeError:
                splits = None
        quantity_ok = requested_qty in splits if splits else listing.quantity_available >= requested_qty
        reasons.append("quantity:exact:pass" if quantity_ok else "quantity:exact:fail")
        qualifies = qualifies and quantity_ok
    else:
        quantity_ok = listing.quantity_available >= requested_qty
        reasons.append("quantity:min:pass" if quantity_ok else "quantity:min:fail")
        qualifies = qualifies and quantity_ok

    unit_price = listing.unit_price_all_in
    unit_ok = unit_price is not None and unit_price <= rule.max_unit_price_all_in
    reasons.append("price:unit:pass" if unit_ok else "price:unit:fail")
    qualifies = qualifies and unit_ok

    if rule.max_order_total is not None:
        total = (unit_price or 0) * requested_qty
        total_ok = total <= rule.max_order_total
        reasons.append("price:total:pass" if total_ok else "price:total:fail")
        qualifies = qualifies and total_ok

    rank = {"low": 0, "medium": 1, "high": 2}
    fee_ok = rank.get(listing.fee_confidence or "low", 0) >= rank.get(rule.minimum_fee_confidence or "medium", 1)
    reasons.append("fee_confidence:pass" if fee_ok else "fee_confidence:fail")
    qualifies = qualifies and fee_ok

    sorted_reasons = sorted(reasons)
    return EvaluationResult(qualifies=qualifies, reason_vector=sorted_reasons, reason_fingerprint=_fingerprint(sorted_reasons))
