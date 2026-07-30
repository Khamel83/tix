# Tix Audit - 2026-07-29

## Current Shape

Tix is a self-hosted personal ticket-deal monitor. The intended loop is:

1. Seed profile sports and venue preferences.
2. Seed venues.
3. Discover upcoming source events.
4. Poll event market data.
5. Use a gate to decide when deeper listing collection is worth it.
6. Parse and persist listings.
7. Evaluate listings against user rules.
8. Queue durable alerts.
9. Deliver alerts through Telegram.
10. Track polling health with a deadman check.

The repository is a local prototype. The core loop works against deterministic demo data, while live-source hardening and richer operator controls remain future work.

## Built In This Product Loop

- FastAPI app with `/health` and an operator dashboard.
- SQLite schema and SQLAlchemy models for profiles, profile sports, profile venues, venues, source events, rules, listings, snapshots, fee observations, alert decisions, outbox, poll runs, and transport health.
- Default profile seeding for Los Angeles sports and venues, with alternate profile tests.
- SeatGeek venue resolution and scheduled event discovery for configured sports venues.
- SeatGeek discovery reads enabled profile venues before falling back to legacy `TARGET_SPORTS_VENUES`.
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
- Operator dashboard with profile preferences, events, listings, poll runs, gate snapshots, alert decisions, outbox counts, and manual event polling.
- Tests for SeatGeek discovery.
- Docker Compose service and Alembic startup migration.
- GitHub Actions pytest workflow.

## Partial Or Missing

- Live listing collection URL details remain behind the Argus adapter and intentionally fail closed when no fixture fallback applies.
- Fee estimation remains a skeleton and is not yet used to infer all-in prices for sources that only provide listed prices.
- The prototype profile is visible in the dashboard but not editable there yet.
- The prototype rules are seeded locally; there is not yet a dashboard editor for rules or section aliases.
- Telegram delivery requires real credentials; prototype mode can queue and inspect outbox rows without sending.

## GitHub State

- Issues #1, #2, #3, and #8-#12 are closed by merged work.
- Issue #4 is the configurable user profile and preference slice.

## Prototype Verification

The local prototype can seed profile preferences, Dodgers and Hollywood Bowl events, poll fixture event stats, pass the gate, persist listings, evaluate rules, write alert decisions, enqueue outbox messages, and show the result in the dashboard without live Argus, live SeatGeek event fetches for demo IDs, live Telegram credentials, or any purchase flow.
