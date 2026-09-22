# Agent workflow

This repository uses a short specification-and-plan step before feature and bug-fix work. The purpose is to make the requested behavior, production boundaries, and verification path explicit before code changes begin.

## When the full workflow is required

Use the full workflow for any change that adds or fixes observable behavior, including changes to:

- production Python code, HTTP endpoints, dashboard behavior, scheduler jobs, or source adapters;
- polling cadence, event collection, gates, rules, alert decisions, or notification delivery;
- database models, migrations, persistence, retries, idempotency, or state transitions; or
- a defect whose fix could change an existing test or user-visible contract.

A small maintenance change may use the reduced form only when it cannot change runtime behavior or the test contract. Examples include a documentation correction, comment or spelling fix, formatting-only change, or a mechanical rename with no behavior change. The reduced form still records the files, intent, verification command, and non-goals in the issue, pull request, or working note.

## Required specification and plan

Before editing for full-workflow changes, write a plan in the issue, pull request, or a working note. Keep it concrete and brief, but include every item below:

1. **Requested behavior:** clarify the trigger and inputs, observable outputs, errors or failure behavior, and any relevant state transition. State assumptions where the request is silent.
2. **Affected boundaries and files:** name the production modules, persistence tables/models or migrations, scheduled jobs, external adapters, endpoints/templates, and configuration boundaries that may be involved. Trace the path far enough to identify callers and consumers, not only the first file that needs editing.
3. **Existing tests:** name the relevant tests under `tests/` and explain what each proves. Include the targeted command and the repository-wide command used for final verification.
4. **Acceptance criteria:** turn the request into observable checks a reviewer can perform.
5. **Non-goals:** state adjacent behavior, integrations, refactors, dependencies, and UI or schema work that are intentionally out of scope.

Do not start implementation until the specification and all five plan sections are written. Keep the plan aligned with `CONTEXT.md` terminology and the existing module layout. If the change crosses a persistence boundary, state whether an Alembic migration is required; do not silently alter the schema.

## Stateful monitoring checklist

For a change on the monitoring path, the plan must explicitly account for each applicable step below. A step may be marked “not affected” with a reason, but it must not be omitted:

- **Polling:** trigger, cadence/tier selection, source fetch, timeout or source failure, and `PollRun` status/counts.
- **Gate and rule evaluation:** missing or stale aggregate data, gate decisions, relevant enabled rules, listing qualification, and evaluation failures.
- **Persistence:** transaction boundaries, current-versus-history writes, idempotency, partial failure behavior, and any migration.
- **Duplicate suppression:** `AlertState` transitions, reason fingerprints, cooldown/re-alert behavior, and the invariant that repeated input does not create an unintended duplicate.
- **Outbox delivery:** durable enqueueing, dedupe keys, pending/sent/failed/skipped states, retry timing, payload preservation, and worker scheduling.
- **Notifications:** transport success and failure, placeholder/missing credentials, and whether the user-visible result is a queued alert or a delivered alert.
- **Deadman checks:** what successful high-tier polling is required, stale-data detection, deduped warning behavior, and routing through the durable outbox.

When one step changes, inspect its neighboring steps and their existing tests. Preserve fail-closed behavior for unavailable external services unless the specification explicitly changes it.

## Tests and dependencies

Use the repository's existing test layout and tooling:

- Put tests in `tests/`, using the shared fixtures and database reset behavior in `tests/conftest.py`.
- Run the relevant test files with `python -m pytest tests/<file>.py` (or the equivalent project virtual-environment Python, such as `.venv/bin/python -m pytest tests/<file>.py`).
- Run the complete suite with `python -m pytest`; the CI workflow uses the same command after installing the existing `.[dev]` extra.
- Use `pytest.mark.asyncio` and `async def` for asynchronous tests, matching the current `pytest-asyncio` convention. Do not introduce another test runner, async framework, or parallel test layout.
- Do not add a production/runtime dependency for a feature or its tests. `pytest` and `pytest-asyncio` are already the repository's development-test dependencies; reuse them and existing fixtures before adding anything.

A new or changed test must defend an observable behavior, boundary, invariant, transition, or real error. Prefer a focused regression test for a bug; do not add tests that only assert implementation details. For a behavior change, update the existing test that owns that boundary rather than creating a duplicate suite.

## Implementation and review checklist

1. Read `CONTEXT.md`, `TODO.md`, the affected production modules, and the existing boundary tests.
2. For a full-workflow change, write and review the specification and plan above before editing; for a reduced-form change, write and review the reduced record (files, intent, verification command, and non-goals) before editing.
3. Implement the smallest complete change, migrating all affected callers and removing obsolete paths rather than leaving aliases or dead code.
4. Run focused pytest tests while iterating, then run `python -m pytest` before handoff.
5. In the final note, report the changed files, observable behavior, tests and commands run, acceptance-criteria coverage, and the stated non-goals. A reviewer should be able to verify the work from that note without installing a new runtime dependency.
