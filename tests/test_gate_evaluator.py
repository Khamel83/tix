import pytest

from ticket_sniper.db.models import EventPriceSnapshot
from ticket_sniper.gates.evaluator import evaluate_event_gate


@pytest.mark.asyncio
async def test_low_event_price_passes_gate(seed_event_and_rule):
    seed_event_and_rule()
    snapshot = EventPriceSnapshot(source="seatgeek", source_event_id="demo-dodgers-001", lowest_price=100, gate_decision="x")

    result = await evaluate_event_gate("seatgeek", "demo-dodgers-001", snapshot)

    assert result.should_collect_listings is True
    assert result.decision == "pass"


@pytest.mark.asyncio
async def test_missing_stats_records_insufficient_data(seed_event_and_rule):
    seed_event_and_rule()
    snapshot = EventPriceSnapshot(source="seatgeek", source_event_id="demo-dodgers-001", lowest_price=None, gate_decision="x")

    result = await evaluate_event_gate("seatgeek", "demo-dodgers-001", snapshot)

    assert result.should_collect_listings is False
    assert result.decision == "insufficient_data"


@pytest.mark.asyncio
async def test_no_relevant_rules_records_no_rules():
    snapshot = EventPriceSnapshot(source="seatgeek", source_event_id="missing", lowest_price=10, gate_decision="x")

    result = await evaluate_event_gate("seatgeek", "missing", snapshot)

    assert result.should_collect_listings is False
    assert result.decision == "no_rules"
