# PR22 Revision Retest Backtest Executor

## Purpose

PR22 extends `execute-revision-retest-next-task` so the revision retest chain can
advance one more artifact-producing step after protocol locking and baseline
generation.

The new supported task is:

- `run_backtest`

The executor remains a narrow domain-code whitelist. It does not dispatch shell
commands, does not run arbitrary command arguments from the plan, and does not
execute later retest tasks.

## Execution Flow

When the current revision retest plan reports `next_task_id == "run_backtest"`:

1. The executor requires `split_manifest_id`.
2. It loads that split manifest from repository artifacts.
3. It calls the existing `run_backtest` domain function.
4. The backtest uses `split.holdout_start` and `split.holdout_end`.
5. The backtest reads stored candles from the same storage directory.
6. It writes `backtest_runs.jsonl` and `backtest_results.jsonl`.
7. The executor records an execution `AutomationRun`.
8. It returns before/after revision retest plans and created artifact ids.

The expected after-plan transition is:

```text
run_backtest -> run_walk_forward
```

## Still Blocked

PR22 deliberately does not execute:

- `run_walk_forward`
- `record-experiment-trial`
- `evaluate-leaderboard-gate`
- `record-paper-shadow-outcome`
- arbitrary command args
- shell or subprocess commands

Those tasks need their own narrow executors and tests before they can run from
the retest executor.

## Research Meaning

This is a self-evolving strategy loop bridge, not a promotion shortcut. A DRAFT
revision can now produce holdout backtest evidence from its locked split, but it
still cannot become rankable or promotion-ready without later walk-forward,
experiment trial, locked evaluation, leaderboard, and paper-shadow evidence.

## Verification

Covered behavior:

- executor writes one backtest run and one backtest result for `run_backtest`;
- executor records an execution `AutomationRun`;
- CLI returns JSON with before/after plans;
- after-plan advances to `run_walk_forward`;
- later unsupported ready tasks remain blocked.

Primary focused command:

```powershell
python -m pytest .\tests\test_research_autopilot.py -k "backtest_next_task or baseline_next_task or execute_revision_retest_next_task" -q
```
