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

## Built On `main`

- FastAPI app with `/health` and a minimal dashboard.
- SQLite schema and SQLAlchemy models for venues, source events, rules, listings, snapshots, fee observations, alert decisions, outbox, poll runs, and transport health.
- SeatGeek venue resolution and scheduled event discovery for configured sports venues.
- Bounded SeatGeek event pagination for scheduled discovery.
- Scheduler jobs for Telegram outbox draining, deadman checks, and SeatGeek target sports discovery.
- Argus client wrapper for `/api/fetch-raw`.
- SeatGeek listing parser skeleton.
- Fee estimator skeleton.
- Rule fingerprint helper.
- One-branch alert state transition skeleton.
- Telegram outbox drain skeleton.
- Tests for SeatGeek discovery.
- Docker Compose service and Alembic startup migration.

## Built In Open PR

PR #6 adds dynamic event polling:

- Event poll cadence tiers based on event start time.
- Scheduler reconciliation for upcoming SeatGeek source events.
- SeatGeek event stats polling into `event_price_snapshots`.
- Poll run success/failure recording.
- Tests for cadence, reconciliation, malformed timestamps, startup reconciliation, and stats persistence.

PR #6 is mergeable in GitHub, but it was built against the old nested repository layout. Rebase or recreate it after the repository root cleanup lands.

## Partial Or Missing

- Listing-level collection is not wired. The Argus client and SeatGeek parser exist, but no runtime path fetches raw listing pages, parses listings, upserts `listings_current`, or writes `listing_price_history`.
- Gate evaluation is represented in the schema, but there is no gate implementation that compares aggregate event stats against rules and triggers deeper polling.
- Rule evaluation is incomplete. There is no implemented matcher evaluation over sections, quantity modes, fee confidence, or max order total.
- Alert state machine is incomplete. The README claims a 9-branch anti-flap state machine, but `main` only handles first-time qualification.
- Alert decisions are not written by a runtime evaluation flow.
- Alert outbox messages are not produced by rule evaluation.
- Telegram delivery does not yet mark failed attempts with backoff or record durable failure state.
- Deadman check sends Telegram directly instead of using the alert outbox.
- Dashboard is only a static online page.
- Configuration and docs do not yet distinguish required credentials, optional integrations, or local development defaults.
- There is no CI workflow.

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

## Next Build Slice

The next practical slice should be the end-to-end listing evaluation path:

1. Poll one SeatGeek source event through Argus or official API data.
2. Parse listings into `listings_current` and `listing_price_history`.
3. Evaluate one real rule against those listings.
4. Create alert decisions and enqueue alert outbox rows.
5. Let the existing Telegram drain deliver those queued alerts.

That slice would turn Tix from a schema plus discovery service into a working ticket-deal monitor.
