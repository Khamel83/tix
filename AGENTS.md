# Tix contribution instructions

## Behavioral TDD workflow

Behavior changes MUST start with an observable regression test or a minimal reproduction that fails for the reported behavior. The test MUST assert consumer-visible behavior, state, output, or side effects; tests that only assert implementation details are not sufficient.

Use the smallest implementation that makes the failing behavioral test pass. Do not weaken, delete, or loosen a failing behavioral assertion merely to obtain a pass. After green, refactor without changing the observable contract.

Run the focused pytest target for the changed subsystem before running the broader repository suite. The focused suites are:

- Event polling: `python -m pytest tests/test_event_polling.py`
- Gate evaluation: `python -m pytest tests/test_gate_evaluator.py`
- Rule evaluation: `python -m pytest tests/test_rule_evaluator.py`
- Listing collection: `python -m pytest tests/test_listing_collection.py`
- Alerting: `python -m pytest tests/test_alert_pipeline.py`
- Notifications: `python -m pytest tests/test_notifications.py`
- Deadman monitoring: `python -m pytest tests/test_deadman.py`

For a change spanning multiple subsystems, run each applicable focused target. Then run the broader repository command: `python -m pytest`. Keep the existing pytest and pytest-asyncio setup; use `@pytest.mark.asyncio` for async tests as established by the repository.

## Red, green, refactor evidence

Each behavior change must leave evidence of:

1. **Red:** the new or updated behavioral test/reproduction fails before the implementation change.
2. **Green:** the focused target passes with the smallest implementation.
3. **Refactor:** cleanup preserves the same focused behavioral result, followed by the broader suite when practical.

A passing result obtained by weakening or deleting the failing behavioral assertion is not valid evidence.
