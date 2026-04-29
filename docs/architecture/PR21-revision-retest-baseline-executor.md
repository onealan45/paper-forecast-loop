# PR21 Revision Retest Baseline Executor

PR21 extends the revision retest next-task executor to support the second
whitelisted evidence step: `generate_baseline_evaluation`.

## Supported Tasks After PR21

- `lock_evaluation_protocol`
- `generate_baseline_evaluation`

The executor still refuses all other ready tasks with
`unsupported_revision_retest_task_execution:<task_id>`.

## Baseline Execution

When the current PR16 task plan reports `generate_baseline_evaluation` as the
next ready task, the executor:

- loads forecasts and scores for the plan symbol;
- builds a `BaselineEvaluation` through the existing baseline builder;
- saves the baseline through the repository;
- records one execution `AutomationRun`;
- returns before/after task plans and created artifact ids.

This remains direct domain-code execution. The executor does not run shell
commands, subprocesses, or rendered command args.

## Deferred Tasks

The next unsupported task is normally `run_backtest`. Backtest and walk-forward
execution remain deferred until they can be added with task-specific artifact
alignment tests.
