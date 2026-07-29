from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from ticket_sniper.db.models import AlertState, Rule, ListingCurrent, utcnow_str


def _parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def _material_drop_passes(rule: Rule, previous_price: float, current_price: float) -> bool:
    drop_dollars = previous_price - current_price
    drop_percent = drop_dollars / previous_price if previous_price else 0.0
    dollar_pass = drop_dollars >= rule.realert_drop_dollars
    percent_pass = drop_percent >= rule.realert_drop_percent
    if rule.realert_mode == "both":
        return dollar_pass and percent_pass
    if rule.realert_mode == "dollars":
        return dollar_pass
    if rule.realert_mode == "percent":
        return percent_pass
    return dollar_pass or percent_pass


def process_alert_state_machine(
    state: Optional[AlertState], rule: Rule, listing: ListingCurrent, qualifies: bool, reason_fp: str
) -> Tuple[int, str, bool, Optional[AlertState]]:
    now_str = utcnow_str()
    now = datetime.now(timezone.utc)
    price = listing.unit_price_all_in or 0.0

    if state is None:
        state = AlertState(
            rule_id=rule.id, source=listing.source, listing_identity=listing.source_listing_id,
            currently_qualifying=0, rule_fingerprint=rule.rule_fingerprint, updated_at=now_str
        )
    if state.currently_qualifying is None:
        state.currently_qualifying = 0
    if state.transition_sequence is None:
        state.transition_sequence = 0

    should_alert = False
    branch = 0
    outcome = "no_change"

    # Branch 1: first observed qualification.
    if state.currently_qualifying == 0 and qualifies:
        branch = 1
        outcome = "alert"
        should_alert = True
        state.currently_qualifying = 1
        state.last_alert_price = price
        state.last_alert_at = now_str
    # Branch 2/3: still qualifying; suppress duplicates unless price drop and cooldown justify a re-alert.
    elif state.currently_qualifying == 1 and qualifies:
        last_alert_price = state.last_alert_price if state.last_alert_price is not None else price
        material_drop = _material_drop_passes(rule, last_alert_price, price)
        last_alert_at = _parse_utc(state.last_alert_at)
        cooldown_elapsed = (
            last_alert_at is None
            or now - last_alert_at >= timedelta(minutes=rule.realert_cooldown_minutes)
        )
        should_alert = material_drop and cooldown_elapsed
        if should_alert:
            branch = 3
            outcome = "realert"
        elif state.reason_fingerprint == reason_fp:
            branch = 2
            outcome = "duplicate_suppressed"
        else:
            branch = 3
            outcome = "realert_suppressed"
        if should_alert:
            state.last_alert_price = price
            state.last_alert_at = now_str
    # Branch 4: recovery from qualifying to non-qualifying.
    elif state.currently_qualifying == 1 and not qualifies:
        branch = 4
        outcome = "recovered"
        state.currently_qualifying = 0
    # Branch 5: remains non-qualifying.
    else:
        branch = 5
        outcome = "not_qualifying"

    if qualifies:
        state.last_qualifying_price = price
    state.reason_fingerprint = reason_fp
    state.rule_fingerprint = rule.rule_fingerprint
    state.transition_sequence = (state.transition_sequence or 0) + 1
    state.updated_at = now_str
    return branch, outcome, should_alert, state
