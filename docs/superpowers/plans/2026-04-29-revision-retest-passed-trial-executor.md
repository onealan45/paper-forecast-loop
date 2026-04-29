# Revision Retest Passed Trial Executor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the revision retest executor to link completed baseline,
holdout backtest, and walk-forward evidence into a PASSED retest experiment
trial.

**Architecture:** Continue the whitelist executor model.
`execute_revision_retest_next_task` will support `record_passed_retest_trial`
by calling the existing `record_experiment_trial` domain function with the
pending retest trial metadata and current plan evidence ids. It will record one
execution `AutomationRun` and return before/after plans.

**Tech Stack:** Python dataclasses, existing experiment registry domain
function, JSONL repository, existing `AutomationRun`, pytest.

---

## Scope

PR24 adds support for:

- `record_passed_retest_trial`

PR24 still does not execute:

- `evaluate_leaderboard_gate`
- `record_paper_shadow_outcome`
- arbitrary command args
- shell/subprocesses

## Tasks

### Task 1: Red Test

- [ ] Create a DRAFT revision with locked split/cost, baseline evidence,
      holdout backtest evidence, and walk-forward evidence.
- [ ] Call `execute_revision_retest_next_task`.
- [ ] Assert:
  - `executed_task_id == "record_passed_retest_trial"`;
  - one PASSED revision retest trial is saved;
  - trial links dataset id, backtest result id, walk-forward validation id,
    source outcome id, and retest protocol parameters;
  - one execution automation run is saved for the passed-trial step;
  - `after_plan.next_task_id == "evaluate_leaderboard_gate"`;
  - created artifact ids include the saved PASSED trial id.
- [ ] Add CLI coverage for the same scenario.
- [ ] Run:

```powershell
python -m pytest .\tests\test_research_autopilot.py -k "passed_trial_next_task" -q
```

Expected: FAIL because executor rejects `record_passed_retest_trial`.

### Task 2: Green

- [ ] Import `record_experiment_trial`.
- [ ] Dispatch `record_passed_retest_trial`.
- [ ] Require pending trial id, dataset id, backtest result id, and
      walk-forward validation id.
- [ ] Load the pending trial and revision card.
- [ ] Call `record_experiment_trial` with `status="PASSED"` and retest
      protocol parameters.
- [ ] Return `[trial.trial_id]`.
- [ ] Run focused tests.

Expected: PASS.

### Task 3: Docs, Review, Gates

- [ ] Add `docs/architecture/PR24-revision-retest-passed-trial-executor.md`.
- [ ] Add review archive under `docs/reviews/`.
- [ ] Update README, PRD, and alpha factory background.
- [ ] Run:

```powershell
python -m pytest .\tests\test_research_autopilot.py -k "passed_trial_next_task or walk_forward_next_task or backtest_next_task or baseline_next_task or execute_revision_retest_next_task" -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

## Acceptance Criteria

- Executor supports passed-trial recording without shell/subprocess execution.
- Before/after plans show transition from `record_passed_retest_trial` to
  `evaluate_leaderboard_gate`.
- Unsupported later tasks remain blocked.
- Tests and reviewer approval pass.
