# PR18 Revision Retest Task Run Log

## Purpose

PR18 records the current revision retest task plan as an audit-visible
`AutomationRun`. PR16 can derive the next task, and PR17 can display it. PR18
adds a lightweight log showing that the system inspected the plan at a specific
time and whether the next retest task was ready, blocked, or complete.

## Behavior

New CLI:

```powershell
python run_forecast_loop.py record-revision-retest-task-run --storage-dir .\paper_storage\manual-research --revision-card-id strategy-card:example-revision --symbol BTC-USD
```

The command:

- builds the read-only `revision-retest-plan`;
- writes one `automation_runs.jsonl` row with provider `research`;
- records each retest task as a step;
- returns both `automation_run` and `revision_retest_task_plan` in JSON.

## Status Mapping

- `RETEST_TASK_READY`: the next task has enough prerequisites to show concrete
  command args.
- `RETEST_TASK_BLOCKED`: the next task is blocked by missing inputs or missing
  evidence.
- `RETEST_TASK_COMPLETE`: no remaining retest task exists.
- `RETEST_TASK_IN_PROGRESS`: reserved for future task states.

## Boundary

This command is a run log only. It does not execute command args, run backtests,
run walk-forward validation, record PASSED trials, evaluate leaderboard gates,
or record paper-shadow outcomes.

The command intentionally writes only `automation_runs.jsonl`. All strategy,
trial, split, baseline, backtest, walk-forward, locked-evaluation,
leaderboard, and paper-shadow artifacts remain unchanged.
