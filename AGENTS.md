# Agent Execution Guidance

## Default execution

The primary agent owns the plan, integration, and completion decision. Use inline execution by default. Subagent-driven execution is optional, and is appropriate only when a plan is large enough to contain multiple independently checkable slices. Do not delegate a task merely to parallelize a small edit.

## Assigning subagents

When using subagents, assign vertical slices rather than horizontal chores. Each assignment must include:

- one independently checkable behavior or workflow;
- explicit file or subsystem scope, including files the subagent must not change;
- concrete acceptance criteria and known dependencies;
- the verification command or runtime scenario expected for that slice.

Slices must have a clear owner and should not overlap in files. If overlap is unavoidable, designate one integration owner and have other agents return findings without editing the shared boundary.

## Subagent return contract

Every subagent must return all of the following, even when it makes no code change:

1. **Findings**: relevant behavior, conventions, and discovered constraints.
2. **Changes**: exact files changed and the observable behavior implemented; distinguish edits from recommendations.
3. **Unresolved risks**: edge cases, boundary assumptions, failed checks, and follow-up concerns.
4. **Verification evidence**: exact commands or runtime/CLI scenarios actually run, exit status, and material output. A plan, a test expectation, or an unexecuted command is not evidence.

The primary agent must review each return, inspect the actual diff and file scope, resolve conflicts or omissions, and only then integrate the result. Do not treat a subagent's completion message as proof of correctness.

## Re-review and completion

After implementation and verification, the primary agent must perform a scoped re-review based on the actual changed files and behavior. Trace the changed path end to end, check callers and persisted or emitted state, and compare the result with the slice acceptance criteria; do not substitute a generic checklist.

Any change that spans polling, decision, persistence, or notification boundaries requires an explicit re-review across every affected boundary, including handoff data, failure behavior, and state transitions. A focused review of only the edited function is insufficient.

Completion requires recorded evidence from the relevant focused test, the broader applicable test command, and any required runtime or CLI smoke check. Run those commands; do not claim completion from a plan, a predicted test result, or an expectation that a command would pass. If a required check cannot run, report the blocker and do not claim the work is complete.
