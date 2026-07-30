# Tix Audit - 2026-07-29

## Current Shape

Tix is a self-hosted personal ticket-deal monitor. The intended loop is:

1. Seed venues.
2. Discover upcoming source events.
3. Poll event market data.
4. Use a gate to decide when deeper listing collection is worth it.
5. Parse and persist listings.
6. Evaluate listings against user rules.
7. Queue durable alerts.
8. Deliver alerts through Telegram.
9. Track polling health with a deadman check.

The repository is early-stage. The schema anticipates the full loop, but the runtime only implements parts of it.

## Built In This Product Loop

- FastAPI app with `/health` and an operator dashboard.
- SQLite schema and SQLAlchemy models for venues, source events, rules, listings, snapshots, fee observations, alert decisions, outbox, poll runs, and transport health.
- SeatGeek venue resolution and scheduled event discovery for configured sports venues.
- Bounded SeatGeek event pagination for scheduled discovery.
- Dynamic event polling with cadence tiers.
- Scheduler jobs for outbox draining, deadman checks, SeatGeek target sports discovery, and dynamic event poll reconciliation.
- Argus client wrapper for `/api/fetch-raw`.
- SeatGeek listing parser for fixture-compatible listing payloads.
- Fixture-backed prototype listing collection for `demo-dodgers-001` and `demo-hollywoodbowl-001`.
- Current listing upsert and price history persistence.
- Gate evaluation from event price snapshots to listing collection.
- Fee estimator skeleton.
- Rule fingerprint helper and listing evaluator for sections, quantities, prices, totals, and fee confidence.
- Alert state transitions for first alerts, duplicate suppression, material re-alerts, cooldown suppression, and recovery.
- Alert decisions and durable outbox enqueueing.
- Telegram outbox worker with success, failure/backoff, and skipped-placeholder credential states.
- Deadman checks routed through the durable outbox.
- Operator dashboard with events, listings, poll runs, gate snapshots, alert decisions, outbox counts, and manual event polling.
- Tests for SeatGeek discovery.
- Docker Compose service and Alembic startup migration.
- GitHub Actions pytest workflow.

## Partial Or Missing

- Live listing collection URL details remain behind the Argus adapter and intentionally fail closed when no fixture fallback applies.
- Fee estimation remains a skeleton and is not yet used to infer all-in prices for sources that only provide listed prices.
- The prototype rules are seeded locally; there is not yet a dashboard editor for rules or section aliases.
- Telegram delivery requires real credentials; prototype mode can queue and inspect outbox rows without sending.

## GitHub State

- Issue #1 maps to merged PR #5 and can be closed as implemented.
- Issue #3 maps to open PR #6 and should remain open until dynamic event polling is rebased onto the cleaned repository root.
- Issues #2 and #4 are Maya-routed context items. Their public bodies do not include the private source material, so they should stay open but be labeled as needing source review before implementation.
- PR #5 is merged.
- PR #6 is open and mergeable, but structurally stale once this cleanup branch lands.

## Immediate Cleanup Recommendation

1. Merge the repository-root cleanup first.
2. Rebase or recreate PR #6 onto the cleaned root.
3. Close issue #1.
4. Label issues #2 and #4 as `needs-source-review`.
5. Convert this audit into concrete implementation issues for the missing runtime loop.

## Prototype Verification

The local prototype can seed Dodgers and Hollywood Bowl events, poll fixture event stats, pass the gate, persist listings, evaluate rules, write alert decisions, enqueue outbox messages, and show the result in the dashboard without live Argus, live SeatGeek event fetches for demo IDs, live Telegram credentials, or any purchase flow.
