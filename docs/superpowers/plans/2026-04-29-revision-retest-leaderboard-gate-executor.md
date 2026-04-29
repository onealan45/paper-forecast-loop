# PR25: Revision Retest Leaderboard Gate Executor

## Scope

Add narrow executor support for the ready `evaluate_leaderboard_gate` revision-retest task.

## Boundaries

- Do not execute arbitrary task command arrays.
- Do not shell out from the executor.
- Do not implement `record_paper_shadow_outcome`.
- Do not add live trading, broker execution, or real capital paths.
- Keep execution limited to existing repository/domain functions and artifact writes.

## Implementation Steps

1. Add failing tests proving the executor should run `evaluate_leaderboard_gate` after a PASSED retest trial.
2. Add a CLI smoke-style test for `execute-revision-retest-next-task` when the next task is `evaluate_leaderboard_gate`.
3. Update the existing unsupported-task test so the next unsupported task becomes `record_paper_shadow_outcome`.
4. Implement a whitelist branch that calls `locked_evaluation.evaluate_leaderboard_gate` with plan-linked artifact IDs.
5. Return both created artifact IDs: locked evaluation result and leaderboard entry.
6. Update README, PRD, and architecture notes to reflect PR25.
7. Run focused tests, full tests, compileall, help, and diff-check.
8. Use reviewer subagent for final review and archive findings under `docs/reviews/`.

## Acceptance Criteria

- `execute-revision-retest-next-task` can advance from `evaluate_leaderboard_gate` to `record_paper_shadow_outcome`.
- The created locked evaluation links the revision card, PASSED trial, split, cost model, baseline, backtest, and walk-forward IDs from the before-plan.
- The created leaderboard entry links the same revision card, PASSED trial, and locked evaluation.
- `record_paper_shadow_outcome` remains unimplemented in this executor and is rejected rather than silently performed.
- Full verification passes before merge.
