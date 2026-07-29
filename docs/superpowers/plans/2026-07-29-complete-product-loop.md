# Complete Product Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Tix into a working local prototype that can discover events for configured venues such as Dodger Stadium and Hollywood Bowl, collect ticket listings for a selected event, evaluate deal rules, write alert decisions, queue alert messages, and expose the result in the local dashboard.

**Architecture:** Keep Tix local-first and source-specific for the prototype. Use SeatGeek event discovery as the event catalog, use a deterministic listing collection interface that can run against fixture data and later Argus/live data, then connect listing persistence, rule evaluation, alert state, durable outbox, and dashboard status into one observable loop.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, SQLite, Alembic, APScheduler, Jinja2, pytest, pytest-asyncio, httpx.

## Global Constraints

- Work from `/Volumes/2TB_SSD/GitHub/tix`.
- Start from `origin/main`; create a branch named `codex/tix-complete-product-loop`.
- Do not reintroduce nested `GitHub/tix/` paths.
- Do not print secrets or real environment values.
- Preserve domain language from `CONTEXT.md`: Tix and Ticket Sniper are one system.
- Use `.venv/bin/python -m pytest` for local validation.
- Close GitHub issues through PR body keywords, not manual premature closure: `Closes #8`, `Closes #9`, `Closes #10`, `Closes #11`, `Closes #12`.
- GitHub closes those issues when the PR is merged, not merely when the branch is pushed.
- Do not close #2 or #4 unless the private Maya Work Items are reviewed and explicitly satisfied.
- Prototype success means the user can run the app locally, discover or seed events, open the dashboard, inspect available events/listings/alerts, manually poll a Dodgers/Hollywood Bowl style event, and see a rule-generated alert queued without live Argus credentials and without making any purchase.
- Demo Source Event IDs are fixed: `demo-dodgers-001` maps to `tests/fixtures/seatgeek_listings_dodgers.json`; `demo-hollywoodbowl-001` maps to `tests/fixtures/seatgeek_listings_hollywood_bowl.json`.
- In prototype mode, manual polling must not require live SeatGeek, live Argus, or live Telegram credentials.

---

## Copyable Worker Prompt

Use this prompt for a fresh implementation worker:

```text
You are working in /Volumes/2TB_SSD/GitHub/tix on repo Khamel83/tix.

Current repo state:
- main is clean and already contains PR #7 repo-root cleanup and PR #6 dynamic SeatGeek event polling.
- The accidental /Volumes/2TB_SSD root Git checkout has been moved aside.
- Use /Volumes/2TB_SSD/GitHub/tix as the only working repo.
- Existing tests pass in .venv: .venv/bin/python -m pytest -> 11 passed.

Goal:
Complete the Tix product loop into a working local prototype:
1. Discover or seed events for venues like Dodger Stadium and Hollywood Bowl.
2. Choose an event in the dashboard.
3. Collect listing-level data for that Source Event using a deterministic fixture-backed path when live Argus is unavailable or `TIX_PROTOTYPE_MODE=1`, with an Argus/live interface kept behind an adapter.
4. Persist current listings and price history.
5. Evaluate Rules over section, quantity, fee confidence, all-in unit price, and max order total.
6. Run Gate evaluation from aggregate event stats to listing polling.
7. Write AlertDecision rows, update AlertState, enqueue AlertOutbox messages, and run an Outbox dispatcher that can process queued notifications.
8. Show operational state in the dashboard and add CI.

Open issues to resolve through the final PR:
- Closes #8 Complete rule evaluation for sections, quantity, fees, and totals.
- Closes #9 Implement gate evaluation from event stats to listing polling.
- Closes #10 Complete alert state machine and durable outbox production.
- Closes #11 Implement listing collection and persistence path.
- Closes #12 Add CI and operational status surface.

Do not close #2 or #4 unless you first review the private Maya Work Item source material and confirm those source-review issues are actually satisfied.

Use the plan in docs/superpowers/plans/2026-07-29-complete-product-loop.md.
Follow TDD. Make small commits. Use explicit path staging, never git add -A.
Before claiming done, run:
- .venv/bin/python -m pytest
- .venv/bin/python -m compileall ticket_sniper
- docker compose config

Key loop integration requirements:
- `ticket_sniper/scheduler/event_polling.py` must run Gate evaluation after event stats polling.
- When the Gate passes, polling must collect listings, persist listings, call `evaluate_event_alerts(source, source_event_id)`, and record summary counts on the relevant `PollRun`.
- `ticket_sniper/listings/collector.py` must fall back to local fixture files when live Argus is unavailable or `TIX_PROTOTYPE_MODE=1`.
- `poll_event_ticket_data` must use fixture event stats for `demo-dodgers-001` and `demo-hollywoodbowl-001` when `TIX_PROTOTYPE_MODE=1`, instead of calling live SeatGeek.
- `ticket_sniper/notifications/worker.py` must process pending `AlertOutbox` rows and be wired into the scheduler.
- Schema/model changes must include Alembic migrations, or the PR must explicitly justify why no migration is needed.

Open a PR against main with a body containing:
Closes #8
Closes #9
Closes #10
Closes #11
Closes #12
```

## File Structure

- Modify `ticket_sniper/sources/base.py`: define a source adapter interface for listing collection/parsing.
- Modify `ticket_sniper/sources/seatgeek.py`: parse realistic listing payloads into normalized listing records.
- Modify `.env.example`: add `TIX_PROTOTYPE_MODE=0`.
- Modify `ticket_sniper/config.py`: add `TIX_PROTOTYPE_MODE: bool = Field(False, env="TIX_PROTOTYPE_MODE")`.
- Create `ticket_sniper/listings/collector.py`: collect listing data for a Source Event and persist current/history rows.
- Create `ticket_sniper/rules/evaluator.py` or replace existing contents: evaluate one Listing against one Rule and return a reason vector.
- Modify `ticket_sniper/rules/state_machine.py`: implement duplicate suppression, re-alert thresholds, cooldowns, and recovery transitions.
- Create `ticket_sniper/alerts/pipeline.py`: evaluate persisted listings against active rules, write AlertDecision rows, update AlertState, and enqueue AlertOutbox messages.
- Create `ticket_sniper/gates/evaluator.py`: decide when aggregate EventPriceSnapshot data warrants listing collection.
- Modify `ticket_sniper/scheduler/event_polling.py`: after event stats polling, run Gate evaluation and trigger listing collection when the Gate passes.
- Modify `ticket_sniper/notifications/telegram.py`: record send failures, attempts, and retry timing.
- Create `ticket_sniper/notifications/worker.py`: process pending AlertOutbox rows through Telegram delivery and update durable delivery status.
- Modify `ticket_sniper/health/deadman.py`: enqueue deadman alerts through AlertOutbox instead of direct Telegram send.
- Modify `ticket_sniper/web/app.py` and templates: expose events, listings, poll runs, outbox status, deadman status, and manual event poll.
- Create `ticket_sniper/demo/seed.py`: seed prototype venues, events, rules, and fixture listings.
- Add `.github/workflows/test.yml`: run tests on pull requests.
- Add tests under `tests/` for each task.
- Update `README.md` and `docs/AUDIT.md` after implementation.

### Task 1: Test Harness And Demo Fixtures

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/fixtures/seatgeek_listings_dodgers.json`
- Create: `tests/fixtures/seatgeek_listings_hollywood_bowl.json`
- Create: `ticket_sniper/demo/seed.py`
- Modify: `README.md`

**Interfaces:**
- Produces: reusable database reset fixture, event/rule/listing fixture helpers, deterministic demo Source Event IDs, and a demo seed command.

- [ ] Create shared pytest fixtures. At module scope in `tests/conftest.py`, before any `ticket_sniper` imports, call `os.environ.setdefault` for `SEATGEEK_CLIENT_ID`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ARGUS_BASE_URL`, `DATABASE_PATH`, and `TIX_PROTOTYPE_MODE`.
- [ ] Document in `tests/conftest.py` that new test files must not import `ticket_sniper` modules before pytest loads `conftest.py`; if a test needs unusual import timing, it must repeat the required `os.environ.setdefault` calls at file top.
- [ ] Keep existing tests passing while migrating away from per-file env setup.
- [ ] Add fixture listing payloads with at least three listings:
  - one Dodgers listing that qualifies for a two-ticket rule,
  - one listing excluded by section,
  - one listing above max all-in price.
- [ ] Add a Hollywood Bowl payload with at least one qualifying listing and one non-qualifying listing.
- [ ] Use this fixture JSON shape exactly:

```json
{
  "listings": [
    {
      "id": "demo-listing-1",
      "section": "Field 1",
      "row": "A",
      "quantity": 4,
      "splits": [1, 2, 4],
      "price_with_fees": {"amount": 125.0},
      "price": {"amount": 98.0},
      "url": "https://example.test/listing/demo-listing-1"
    }
  ]
}
```

- [ ] Add a top-level `_fixture_schema` or `_comment` field to each fixture file describing those expected fields so future maintainers do not guess.
- [ ] Add `seed_demo_data()` that creates:
  - Venue `Dodger Stadium`,
  - Venue `Hollywood Bowl`,
  - active SeatGeek Source Event `demo-dodgers-001` for Dodger Stadium,
  - active SeatGeek Source Event `demo-hollywoodbowl-001` for Hollywood Bowl,
  - one enabled Rule for Dodgers two tickets under a target all-in price,
  - one enabled Rule for Hollywood Bowl under a target all-in price.
- [ ] In Task 1 only, seed any needed demo listing rows directly with SQLAlchemy models so the seed command is useful before the listing collector exists.
- [ ] Demo listings must use `fee_confidence="high"` because fixture prices are treated as all-in prices and should pass rules with `minimum_fee_confidence="medium"`.
- [ ] Add README commands:
  - `.venv/bin/python -m pytest`
  - `.venv/bin/python -m ticket_sniper.demo.seed`
  - `.venv/bin/uvicorn ticket_sniper.web.app:app --reload`
- [ ] Run `tests/conftest.py` consumers through existing tests and commit.

### Task 2: Listing Collection And Persistence (#11)

**Files:**
- Modify: `ticket_sniper/sources/base.py`
- Modify: `ticket_sniper/sources/seatgeek.py`
- Create: `ticket_sniper/listings/__init__.py`
- Create: `ticket_sniper/listings/collector.py`
- Test: `tests/test_listing_collection.py`

**Interfaces:**
- Produces: `async def collect_event_listings(source: str, source_event_id: str, tier: int, raw_body: str | None = None) -> dict`.
- Produces: `async def upsert_listings(source: str, source_event_id: str, listings: list[dict], run_id: int) -> dict`.
- Both functions use `run_db_transaction` internally for DB work and are awaited from `poll_event_ticket_data`.

- [ ] Write tests for parsing SeatGeek fixture listings into normalized fields: source listing ID, section, row, quantity available, available quantities, all-in unit price, listed unit price when present, listing URL, payload hash, adapter version, and parser version.
- [ ] Write tests for idempotent upsert into `listings_current`.
- [ ] Write tests that changed price or quantity writes `listing_price_history`.
- [ ] Write tests that failed collection records `PollRun.status == "failed"` and keeps existing listing rows untouched.
- [ ] Implement parser normalization in `ticket_sniper/sources/seatgeek.py`.
- [ ] Implement collection/persistence in `ticket_sniper/listings/collector.py`.
- [ ] For prototype mode, allow `raw_body` injection so tests and the dashboard can run without live Argus.
- [ ] Add `TIX_PROTOTYPE_MODE` configuration. When enabled, or when live Argus is unavailable, load fixture payloads by known demo `source_event_id` so manual dashboard polls produce listings and alerts.
- [ ] Add `TIX_PROTOTYPE_MODE: bool = Field(False, env="TIX_PROTOTYPE_MODE")` to `Settings`.
- [ ] Add `TIX_PROTOTYPE_MODE=0` to `.env.example`.
- [ ] Implement fixture fallback mapping exactly:
  - `demo-dodgers-001` -> `tests/fixtures/seatgeek_listings_dodgers.json`
  - `demo-hollywoodbowl-001` -> `tests/fixtures/seatgeek_listings_hollywood_bowl.json`
- [ ] Keep live Argus fetch behind a clearly named function; if live URL details are unknown and no fixture fallback applies, return a recorded failure instead of pretending success.
- [ ] Before adding any migration, diff `ticket_sniper/db/models.py` against `alembic/versions/001_initial_schema.py`. If any persisted columns/tables/indexes change, write a hand-authored Alembic revision matching the existing migration style and test `alembic upgrade head`.
- [ ] Run `tests/test_listing_collection.py` and commit.

### Task 3: Rule Evaluation (#8)

**Files:**
- Modify: `ticket_sniper/rules/evaluator.py`
- Test: `tests/test_rule_evaluator.py`

**Interfaces:**
- Produces: `EvaluationResult(qualifies: bool, reason_vector: list[str], reason_fingerprint: str)`.
- Produces: `evaluate_listing(rule: Rule, matchers: list[RuleSectionMatcher], listing: ListingCurrent) -> EvaluationResult`.

- [ ] Write tests for include exact section match.
- [ ] Write tests for exclude matcher overriding include matcher.
- [ ] Write tests for exact quantity mode requiring `quantity_value` to be available.
- [ ] For `quantity_mode == "exact"`, require `rule.quantity_value` to appear in `json.loads(listing.available_quantities_json)` when that field is present; fall back to `listing.quantity_available >= rule.quantity_value` only when splits are absent.
- [ ] Write tests for max all-in unit price.
- [ ] Write tests for max order total.
- [ ] Write tests for minimum fee confidence ordering: `low < medium < high`.
- [ ] Implement deterministic reason vectors such as `section:included`, `section:excluded`, `quantity:exact:pass`, `price:unit:pass`, `price:total:fail`, `fee_confidence:pass`.
- [ ] Sort `reason_vector` before stable JSON serialization and SHA-256 hashing so fingerprints are deterministic.
- [ ] Run `tests/test_rule_evaluator.py` and commit.

### Task 4: Alert State Machine And Outbox (#10)

**Files:**
- Modify: `ticket_sniper/rules/state_machine.py`
- Create: `ticket_sniper/alerts/__init__.py`
- Create: `ticket_sniper/alerts/pipeline.py`
- Test: `tests/test_alert_pipeline.py`

**Interfaces:**
- Consumes: `evaluate_listing(...) -> EvaluationResult`.
- Produces: `async def evaluate_event_alerts(source: str, source_event_id: str) -> dict`.
- Produces: `format_alert_message(rule: Rule, listing: ListingCurrent, result: EvaluationResult) -> str`.
- `evaluate_event_alerts` uses `run_db_transaction` internally for DB work and is awaited from `poll_event_ticket_data`.

- [ ] Write tests that first-time qualifying listing creates `AlertDecision`, updates `AlertState`, and enqueues one `AlertOutbox` row.
- [ ] Write tests that the same qualifying listing with same reason fingerprint does not enqueue a duplicate alert.
- [ ] Write tests that a material price drop passing `realert_drop_dollars` or `realert_drop_percent` enqueues a re-alert.
- [ ] Write tests that cooldown suppresses a re-alert until `realert_cooldown_minutes` has elapsed.
- [ ] Write tests that a listing moving from qualifying to non-qualifying updates state without alerting.
- [ ] Implement state transitions with branch numbers documented in code comments and tests.
- [ ] Implement outbox dedupe keys using rule ID, source, listing identity, outcome branch, and reason fingerprint.
- [ ] Return summary counts from `evaluate_event_alerts`: listings evaluated, decisions written, alerts queued, and duplicates suppressed.
- [ ] Run `tests/test_alert_pipeline.py` and commit.

### Task 5: Gate Evaluation And Event Poll Integration (#9)

**Files:**
- Create: `ticket_sniper/gates/__init__.py`
- Create: `ticket_sniper/gates/evaluator.py`
- Modify: `ticket_sniper/scheduler/event_polling.py`
- Test: `tests/test_gate_evaluator.py`
- Test: `tests/test_event_polling.py`

**Interfaces:**
- Produces: `evaluate_event_gate(source: str, source_event_id: str, snapshot: EventPriceSnapshot) -> GateResult`.
- Produces: `GateResult(should_collect_listings: bool, decision: str, reason: str)`.

- [ ] Write tests that a low event `lowest_price` relative to active rules passes the Gate.
- [ ] Write tests that missing stats records `insufficient_data` and does not collect listings.
- [ ] Write tests that no relevant enabled rules records `no_rules`.
- [ ] Write tests that a passing Gate calls `collect_event_listings`.
- [ ] Write tests that successful listing collection calls `evaluate_event_alerts`.
- [ ] Write tests that `EventPriceSnapshot.gate_decision` and `gate_reason` are updated from the Gate.
- [ ] Define prototype Gate logic explicitly: for active relevant rules, pass if `snapshot.lowest_price <= rule.max_unit_price_all_in * (1 + settings.GATE_MARGIN)`.
- [ ] Implement venue-scoped and source-event-scoped rule lookup.
- [ ] Update `poll_event_ticket_data` to persist stats, run Gate, collect listings only when the Gate passes, then call `evaluate_event_alerts(source, source_event_id)` after listings are persisted.
- [ ] In prototype mode, add fixture event stats for:
  - `demo-dodgers-001`: enough stats for the Gate to pass at least one Dodgers rule.
  - `demo-hollywoodbowl-001`: enough stats for the Gate to pass at least one Hollywood Bowl rule.
- [ ] In prototype mode, `poll_event_ticket_data` must use those fixture stats and must not call `SeatGeekDiscovery().fetch_event`.
- [ ] Record listing and alert summary counts on `PollRun` using existing fields where possible: `inventory_count`, `new_listing_count`, `changed_listing_count`; add a migration only if new fields are necessary.
- [ ] Run gate and event polling tests and commit.

### Task 6: Telegram Outbox Worker Reliability And Deadman Routing

**Files:**
- Modify: `ticket_sniper/notifications/telegram.py`
- Create: `ticket_sniper/notifications/worker.py`
- Modify: `ticket_sniper/scheduler/engine.py`
- Modify: `ticket_sniper/health/deadman.py`
- Test: `tests/test_notifications.py`
- Test: `tests/test_deadman.py`

**Interfaces:**
- Produces: retry behavior for `AlertOutbox`.
- Produces: `process_pending_outbox(limit: int = 10) -> dict`.
- Produces: deadman alert rows in `AlertOutbox`.

- [ ] Write tests that successful Telegram send marks outbox row `sent`.
- [ ] Write tests that failed Telegram send increments `attempts`, records `last_error`, and schedules `next_attempt_at`.
- [ ] Write tests that repeated failures do not lose payload JSON.
- [ ] Write tests that deadman creates an outbox row instead of sending directly.
- [ ] Implement `process_pending_outbox(limit=10)` that loads due pending rows, sends through Telegram, marks sent rows `sent`, and records failures with attempts/backoff.
- [ ] When `TELEGRAM_BOT_TOKEN` is a placeholder such as the `.env.example` value, `process_pending_outbox` must skip HTTP delivery, mark rows `skipped_no_credentials`, preserve `payload_json`, and log a warning.
- [ ] Wire `process_pending_outbox` into APScheduler on the existing outbox interval.
- [ ] For prototype/manual workflows, allow the dashboard to show queued outbox rows even when Telegram credentials are placeholders; do not require real Telegram delivery for prototype success.
- [ ] Implement fixed backoff first; avoid introducing a queue library.
- [ ] Run notification/deadman tests and commit.

### Task 7: Dashboard Prototype And Manual Workflow (#12)

**Files:**
- Modify: `ticket_sniper/web/app.py`
- Modify: `ticket_sniper/web/templates/base.html`
- Modify: `ticket_sniper/web/templates/dashboard.html`
- Create: `tests/test_web_dashboard.py`

**Interfaces:**
- Consumes: event/listing/poll/outbox data from DB.
- Produces: dashboard routes and manual event poll route.

- [ ] Add dashboard data queries for:
  - active Source Events,
  - recent Poll Runs,
  - recent EventPriceSnapshots,
  - current listings for selected event,
  - outbox counts by status,
  - latest AlertDecisions.
- [ ] Add `POST /events/{source}/{source_event_id}/poll` to run `poll_event_ticket_data`.
- [ ] Add tests using FastAPI TestClient for dashboard load and manual poll route.
- [ ] Manual poll must work in prototype mode without live Argus by using fixture fallback, then returning visible counts for Gate decision, listings persisted, decisions written, and alerts queued.
- [ ] Keep visual design utilitarian and dense; this is an operator dashboard, not a landing page.
- [ ] Ensure the user can see Dodgers/Hollywood Bowl seeded events and whether listings/alerts exist.
- [ ] Run dashboard tests and commit.

### Task 8: CI And Documentation (#12)

**Files:**
- Create: `.github/workflows/test.yml`
- Modify: `README.md`
- Modify: `docs/AUDIT.md`

**Interfaces:**
- Produces: GitHub Actions test gate.
- Produces: accurate operator docs.

- [ ] Add a GitHub Actions workflow on pull requests and pushes to `main`.
- [ ] Use Python 3.11 or 3.12 in CI, install `.[dev]`, and run `python -m pytest`.
- [ ] Document prototype run steps:
  - create `.env` from `.env.example`,
  - create `.venv`,
  - install `.[dev]`,
  - seed demo data,
  - run dashboard,
  - trigger manual event poll.
- [ ] Update `docs/AUDIT.md` so completed items move from missing to built.
- [ ] Run `docker compose config`.
- [ ] If migrations were added, run `.venv/bin/alembic upgrade head` against a disposable local DB.
- [ ] Run full verification and commit.

### Task 9: Final PR And Issue Closure

**Files:**
- No code files unless final docs need correction.

**Interfaces:**
- Produces: one PR that closes #8-#12.

- [ ] Run full verification:
  - `.venv/bin/python -m pytest`
  - `.venv/bin/python -m compileall ticket_sniper`
  - `docker compose config`
- [ ] Confirm `git status --short` only contains intentional tracked changes.
- [ ] Push branch `codex/tix-complete-product-loop`.
- [ ] Open PR against `main` with this body:

```md
## Summary
- Completes the local Tix prototype loop from event discovery through listing collection, rule evaluation, alert decisions, durable outbox, and dashboard visibility.
- Adds fixture-backed demo data for Dodgers and Hollywood Bowl style scenarios.
- Adds CI and updates operator documentation.

## Verification
- `.venv/bin/python -m pytest`
- `.venv/bin/python -m compileall ticket_sniper`
- `docker compose config`
- `.venv/bin/alembic upgrade head` if migrations were added

Closes #8
Closes #9
Closes #10
Closes #11
Closes #12
```

- [ ] Do not close #2 or #4 from this PR unless their Maya source review is explicitly completed and documented.

## Self-Review

- Spec coverage: #8 is covered by Task 3, #9 by Task 5, #10 by Task 4 and Task 6, #11 by Task 2, and #12 by Tasks 7-8.
- Prototype coverage: Tasks 1, 2, 4, 5, 6, and 7 together allow a seeded Dodgers/Hollywood Bowl event to produce visible listings, rule decisions, queued alerts, and observable outbox state locally without live Argus credentials.
- Known source gate: #2 and #4 remain outside this plan unless their private Maya source is reviewed.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-29-complete-product-loop.md`. Two execution options:

**1. Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints.
