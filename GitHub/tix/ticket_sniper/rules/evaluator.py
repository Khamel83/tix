import json
import hashlib
from typing import Dict, List, Tuple, Optional
from ticket_sniper.db.models import Rule, RuleSectionMatcher, ListingCurrent

def compute_rule_fingerprint(rule: Rule, matchers: List[RuleSectionMatcher]) -> str:
    sorted_matchers = sorted(matchers, key=lambda x: x.sort_order)
    payload = {
        "max_unit_price_all_in": rule.max_unit_price_all_in,
        "quantity_mode": rule.quantity_mode,
        "quantity_value": rule.quantity_value,
        "matchers": [{"action": m.action, "type": m.matcher_type, "value": m.matcher_value} for m in sorted_matchers]
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
