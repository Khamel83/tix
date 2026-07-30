from ticket_sniper.db.models import ListingCurrent, Rule, RuleSectionMatcher
from ticket_sniper.rules.evaluator import evaluate_listing


def rule(**kwargs):
    values = dict(
        id=1,
        name="rule",
        max_unit_price_all_in=150,
        max_order_total=300,
        quantity_mode="exact",
        quantity_value=2,
        minimum_fee_confidence="medium",
        rule_fingerprint="fp",
    )
    values.update(kwargs)
    return Rule(**values)


def listing(**kwargs):
    values = dict(
        source="seatgeek",
        source_listing_id="l1",
        source_event_id="e1",
        raw_section="Field 1",
        normalized_section="Field 1",
        raw_row="A",
        quantity_available=4,
        available_quantities_json="[1, 2, 4]",
        unit_price_all_in=125,
        fee_confidence="high",
        listing_url="https://example.test",
        payload_hash="hash",
        adapter_version="v",
        parser_version="v",
    )
    values.update(kwargs)
    return ListingCurrent(**values)


def matcher(action="include", value="Field 1"):
    return RuleSectionMatcher(action=action, matcher_type="exact", matcher_value=value, sort_order=0)


def test_include_exact_section_match_qualifies():
    result = evaluate_listing(rule(), [matcher()], listing())
    assert result.qualifies is True
    assert "section:included" in result.reason_vector


def test_exclude_matcher_overrides_include():
    result = evaluate_listing(rule(), [matcher(), matcher("exclude", "Field 1")], listing())
    assert result.qualifies is False
    assert "section:excluded" in result.reason_vector


def test_exact_quantity_requires_split_when_splits_present():
    result = evaluate_listing(rule(quantity_value=3), [matcher()], listing())
    assert result.qualifies is False
    assert "quantity:exact:fail" in result.reason_vector


def test_price_total_and_fee_confidence_failures_are_reported():
    result = evaluate_listing(
        rule(max_unit_price_all_in=100, max_order_total=200, minimum_fee_confidence="high"),
        [matcher()],
        listing(unit_price_all_in=125, fee_confidence="medium"),
    )
    assert result.qualifies is False
    assert "price:unit:fail" in result.reason_vector
    assert "price:total:fail" in result.reason_vector
    assert "fee_confidence:fail" in result.reason_vector
    assert len(result.reason_fingerprint) == 64
