# PR20 Revision Retest Next Task Executor

PR20 adds the first artifact-producing executor for the revision retest chain.

## Supported Task

This PR supports exactly one next task:

- `lock_evaluation_protocol`

The executor builds the PR16 task plan, requires the next task to be `ready`,
and then calls the existing `lock_evaluation_protocol` domain helper directly.
It does not use shell execution or subprocess dispatch.

## Output Artifacts

When `lock_evaluation_protocol` is ready, execution writes:

- the idempotent split manifest row if it is not already present;
- a locked cost model snapshot;
- one `AutomationRun` with:
  - `provider = "research"`;
  - `command = "execute-revision-retest-next-task"`;
  - `status = "RETEST_TASK_EXECUTED"`;
  - `decision_basis = "revision_retest_task_execution"`.

The returned JSON includes the before-plan, after-plan, automation run, and
created artifact ids.

## Explicitly Unsupported In PR20

The executor refuses all other ready tasks with
`unsupported_revision_retest_task_execution:<task_id>`.

Deferred tasks include:

- `generate_baseline_evaluation`;
- `run_backtest`;
- `run_walk_forward`;
- `record_passed_retest_trial`;
- `evaluate_leaderboard_gate`;
- `record_paper_shadow_outcome`.

These should be added one at a time with task-specific tests.

## Research Direction

PR20 is the first step from retest inspection toward a self-evolving research
loop. It remains intentionally narrow: one validated retest step, one audit log,
and visible before/after plans.
