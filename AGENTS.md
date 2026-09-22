# Repository instructions

## Durable progress state for multi-step work

Use a repository-local ledger when work has multiple dependent steps. This state is planning evidence only; it is not application data.

### Location and identity

- Assign every plan one immutable, unique `plan_id` in the form `plan-YYYYMMDDTHHMMSSZ-<slug>-<8-hex-random>`. Do not reuse an identifier, even after cleanup.
- Store only that plan's state under `.agent-progress/<plan_id>/ledger.yaml`. The directory name and the ledger's `plan_id` must match exactly. Do not scan, combine, or copy records from another plan directory.
- The plan scope is immutable and must name the goal, acceptance criteria, allowed files or directories, affected subsystems, and ordered steps. Record it as `scope` and compute a `scope_digest` from its canonical serialization when the plan starts.
- Keep generated state out of source packages and production configuration. `.agent-progress/` is ignored by Git and is never read by the application or CI.

### Required progress record

`ledger.yaml` is a YAML list of records. Append one record for each step transition; do not rewrite earlier records. Every record must include all of these fields:

```yaml
- plan_id: plan-20260917T120000Z-alert-docs-a1b2c3d4
  scope_digest: sha256:<digest of canonical scope JSON>
  scope:
    goal: "..."
    acceptance_criteria: ["..."]
    allowed_paths: ["AGENTS.md", ".gitignore"]
    affected_subsystems: ["repository instructions"]
    ordered_steps: ["...", "..."]
  current_step: 2
  status: completed # completed, in_progress, or abandoned
  affected_files_or_subsystem: ["AGENTS.md", ".gitignore"]
  verification:
    command: "python -m pytest"
    result: "PASS (exit 0)"
  repository_state_after:
    head: "<git rev-parse HEAD>"
    status: "<git status --short --untracked-files=all>"
    diff_sha256: "<sha256 of the tracked diff excluding .agent-progress>"
  recorded_at: "2026-09-17T12:34:56Z"
```

The canonical scope serialization is UTF-8 JSON with sorted keys and no insignificant whitespace. Hash that exact byte sequence with SHA-256. `current_step`, `affected_files_or_subsystem`, `verification.command`, and `verification.result` are mandatory even for an abandoned step. A result is valid only when the recorded command was actually run and includes its exit status; never infer success from intent or from an earlier run. Record the repository state after verification so a later resume can prove which worktree was verified.

### Resume and stale-ledger rejection

Before continuing a plan, verify all of the following:

1. Open only `.agent-progress/<current-plan-id>/ledger.yaml`; reject a missing ledger, a plan-id mismatch, or any record whose scope or `scope_digest` differs from the current plan.
2. Recompute the canonical scope digest and compare it with every record. A changed goal, acceptance criterion, allowed path, subsystem, or ordered step is a new plan and requires a new `plan_id`; never merge the old ledger.
3. Reproduce the latest record's repository-state evidence using `git rev-parse HEAD`, `git status --short --untracked-files=all`, and `git diff --binary HEAD -- . ':(exclude).agent-progress' | sha256sum`. Resume only when the values match `repository_state_after` (or the recorded initial state for a plan with no completed step).
4. Confirm every prior record has a real verification command, an explicit result, and a reproducible exit status. If evidence is missing, contradictory, or cannot be reproduced, reject the prior run and restart with a new plan; do not mark it completed and do not merge its progress.
5. Check that no other plan's records are being used. A ledger from another plan, a changed plan, or an unverifiable prior run is stale and must be rejected rather than merged into current progress.

### Completion, abandonment, and cleanup

Keep each plan isolated in its own directory while work is active. Mark the final record `status: completed` only after all acceptance criteria and verification commands pass. If work stops without completion, append an `abandoned` record with the reason and the last verification result; do not resume it under a different scope. After review, remove only that plan's `.agent-progress/<plan_id>/` directory, or retain it as ignored local history. Never move terminal records into another plan's ledger, and never let cleanup alter source files, dependencies, runtime behavior, or CI test execution.
