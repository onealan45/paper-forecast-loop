# PR24 Revision Retest Passed Trial Executor

## Purpose

PR24 extends `execute-revision-retest-next-task` so the revision retest chain can
advance from completed baseline, holdout backtest, and walk-forward evidence to
a PASSED retest experiment trial.

The new supported task is:

- `record_passed_retest_trial`

The executor remains a narrow domain-code whitelist. It does not dispatch shell
commands, does not run arbitrary command arguments from the plan, and does not
execute later retest tasks.

## Execution Flow

When the current revision retest plan reports
`next_task_id == "record_passed_retest_trial"`:

1. The executor requires a pending trial id, dataset id, backtest result id, and
   walk-forward validation id.
2. It loads the pending retest trial and revision strategy card.
3. It calls the existing `record_experiment_trial` domain function.
4. The recorded trial has `status="PASSED"`.
5. The trial links the dataset, holdout backtest, walk-forward validation, and
   source paper-shadow outcome.
6. The executor records an execution `AutomationRun`.
7. It returns before/after revision retest plans and created artifact ids.

The expected after-plan transition is:

```text
record_passed_retest_trial -> evaluate_leaderboard_gate
```

## Still Blocked

PR24 deliberately does not execute:

- `evaluate_leaderboard_gate`
- `record_paper_shadow_outcome`
- arbitrary command args
- shell or subprocess commands

Those tasks need their own narrow executors and tests before they can run from
the retest executor.

## Research Meaning

This turns completed retest evidence into an auditable PASSED trial, but it
does not rank, promote, or shadow-trade the revised strategy. Leaderboard
evaluation remains a separate locked gate.

## Verification

Covered behavior:

- executor records one PASSED retest trial for `record_passed_retest_trial`;
- PASSED trial links dataset, backtest, walk-forward, source outcome, and retest
  protocol parameters;
- executor records an execution `AutomationRun`;
- CLI returns JSON with before/after plans;
- after-plan advances to `evaluate_leaderboard_gate`;
- later unsupported ready tasks remain blocked.

Primary focused command:

```powershell
python -m pytest .\tests\test_research_autopilot.py -k "passed_trial_next_task or walk_forward_next_task or backtest_next_task or baseline_next_task or execute_revision_retest_next_task" -q
```
