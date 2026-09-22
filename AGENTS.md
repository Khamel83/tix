# Agent Instructions

## Systematic debugging for ticket-monitoring failures

When a failure is reported in the ticket-monitoring pipeline, use this bounded workflow. Work only on the reported failure and the causal path needed to explain it.

1. **Build and preserve a deterministic reproduction.** Start from a failing regression test, an existing failing test, or a captured failing test/trace with pinned inputs and external responses. Preserve the original failure artifact and record the exact observed symptom. Do not proceed from an unverified hunch.
2. **State ranked hypotheses before changing production code.** Each hypothesis must make a falsifiable prediction. Gather evidence for the first incorrect state, not merely the final bad output. At every relevant boundary, compare expected and actual data and state:
   - polling: source response, normalization, poll-run status, and tier;
   - decision: gate/rule result, Alert Decision branch, reason fingerprint, and Alert State;
   - persistence: transaction boundaries, committed rows, reads, dedupe keys, and durable outbox state;
   - scheduling: cadence, reconciliation, job execution, and whether a poll was actually scheduled;
   - notification: outbox selection, delivery result, status, attempts, and next retry time.
   Include evidence from external-service boundaries and persistence boundaries whenever either can cause the failure.
3. **Test the root cause at the narrowest correct seam.** Use targeted probes or a debugger that distinguish the hypotheses, changing one variable at a time. Do not add broad logging or infer causality from correlation. If duplicate suppression is involved, inspect Alert State, reason fingerprints, and outbox dedupe keys. If outbox delivery is involved, inspect claiming/selection, delivery status, errors, attempts, and retry timing. If alert decisions are involved, inspect the evaluated listing/rule inputs and recorded branch. If deadman behavior is involved, inspect successful high-tier Poll Runs, the threshold, deduplication, and routing through Alert Outbox.
4. **Lock the diagnosed cause with a regression test before the fix.** The test must reproduce the real failure at the narrowest seam that includes its causal path, fail for the diagnosed cause before the production change, and pass after the change. Keep assertions on observable behavior and relevant state transitions; do not replace the failing scenario with a shallow mock.
5. **Only then change production code.** Keep the fix minimal and local to the demonstrated cause. Do not suppress the symptom, swallow or weaken an error, add a special case for the fixture, or perform broad unrelated refactors. Do not change retry or timeout behavior unless evidence shows that retry or timeout behavior is causal.
6. **Re-run the original reproduction and regression test.** Remove temporary instrumentation and throwaway artifacts. Confirm that duplicate suppression, outbox delivery, alert decisions, or deadman behavior still satisfy their existing contracts when those paths were involved.
