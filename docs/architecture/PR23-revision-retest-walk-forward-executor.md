# PR23 Revision Retest Walk-Forward Executor

## Purpose

PR23 extends `execute-revision-retest-next-task` so the revision retest chain can
advance from holdout backtest evidence to walk-forward validation evidence.

The new supported task is:

- `run_walk_forward`

The executor remains a narrow domain-code whitelist. It does not dispatch shell
commands, does not run arbitrary command arguments from the plan, and does not
execute later retest tasks.

## Execution Flow

When the current revision retest plan reports `next_task_id == "run_walk_forward"`:

1. The executor requires `split_manifest_id`.
2. It loads that split manifest from repository artifacts.
3. It calls the existing `run_walk_forward_validation` domain function.
4. The walk-forward run uses `split.train_start` through `split.holdout_end`.
5. The walk-forward engine reads stored candles from the same storage directory.
6. It writes `walk_forward_validations.jsonl` and any required window backtest
   run/result artifacts.
7. The executor records an execution `AutomationRun`.
8. It returns before/after revision retest plans and created artifact ids.

The expected after-plan transition is:

```text
run_walk_forward -> record_passed_retest_trial
```

## Still Blocked

PR23 deliberately does not execute:

- `record_passed_retest_trial`
- `evaluate_leaderboard_gate`
- `record_paper_shadow_outcome`
- arbitrary command args
- shell or subprocess commands

Those tasks need their own narrow executors and tests before they can run from
the retest executor.

## Research Meaning

This moves the self-evolving revision loop one step closer to a complete
evaluation chain. A DRAFT revision can now produce both holdout backtest and
walk-forward validation evidence, but it still cannot become rankable or
promotion-ready without a PASSED retest trial, locked evaluation, leaderboard,
and paper-shadow evidence.

## Verification

Covered behavior:

- executor writes one walk-forward validation for `run_walk_forward`;
- executor records an execution `AutomationRun`;
- CLI returns JSON with before/after plans;
- after-plan advances to `record_passed_retest_trial`;
- later unsupported ready tasks remain blocked.

Primary focused command:

```powershell
python -m pytest .\tests\test_research_autopilot.py -k "walk_forward_next_task or backtest_next_task or baseline_next_task or execute_revision_retest_next_task" -q
```
