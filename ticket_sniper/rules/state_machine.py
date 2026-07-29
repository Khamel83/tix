from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from ticket_sniper.db.models import AlertState, Rule, ListingCurrent, utcnow_str

def process_alert_state_machine(
    state: Optional[AlertState], rule: Rule, listing: ListingCurrent, qualifies: bool, reason_fp: str
) -> Tuple[int, str, bool, Optional[AlertState]]:
    now_str = utcnow_str()
    price = listing.unit_price_all_in or 0.0

    if state is None:
        state = AlertState(
            rule_id=rule.id, source=listing.source, listing_identity=listing.source_listing_id,
            currently_qualifying=0, rule_fingerprint=rule.rule_fingerprint, updated_at=now_str
        )

    should_alert = False
    branch = 0
    outcome = "no_change"

    if state.currently_qualifying == 0 and qualifies:
        branch = 1
        outcome = "alert"
        should_alert = True
        state.currently_qualifying = 1
        state.last_alert_price = price

    return branch, outcome, should_alert, state
