# Issue #25: Preserve Listing Change Counts

## Scope

Fix one polling-path defect: after a gated listing collection, `PollRun.changed_listing_count` must retain the count returned by listing persistence. Alert queue counts are a separate outcome and must not overwrite listing-change metrics.

## Non-goals

- No changes to gate decisions, listing persistence, alert evaluation, or notification delivery.
- No new database columns, migrations, dependencies, or scheduler behavior.
- No broad cleanup of adjacent polling metrics.

## Plan-scoped progress

- [x] Select bounded defect: polling summary overwrites listing changes with queued alerts.
- [x] Specify scope and non-goals.
- [x] Add behavioral regression reproduction and capture its pre-fix failure.
- [x] Apply the smallest production fix.
- [x] Run focused and repository-wide verification.
- [x] Review changed boundaries and record evidence.

## Verification evidence

- Pre-fix reproduction: `test_event_poll_preserves_listing_change_count_when_alerts_queue` failed with `1 == 3`; the alert count overwrote the listing change count.
- Focused regression: `PYTHONPATH=. uv run --extra dev pytest tests/test_event_polling.py::test_event_poll_preserves_listing_change_count_when_alerts_queue -q` passed.
- Focused polling suite: `PYTHONPATH=. uv run --extra dev pytest tests/test_event_polling.py -q` passed, 10 tests.
- Repository suite: `PYTHONPATH=. uv run --extra dev pytest -q` passed, 43 tests.
- Changed boundaries reviewed: `poll_event_ticket_data` now records only listing persistence metrics in `PollRun`; gate, collection, alert, and notification behavior remain unchanged.
