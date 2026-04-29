# Revision Retest Walk-Forward Executor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the revision retest executor to run walk-forward validation
after protocol, baseline, and holdout backtest evidence exist.

**Architecture:** Continue the whitelist executor model.
`execute_revision_retest_next_task` will support `run_walk_forward` by calling
the existing `run_walk_forward_validation` domain function with the locked split
full window. It will record one execution `AutomationRun` and return
before/after plans.

**Tech Stack:** Python dataclasses, existing walk-forward engine, JSONL
repository, existing `AutomationRun`, pytest.

---

## Scope

PR23 adds support for:

- `run_walk_forward`

PR23 still does not execute:

- `record_passed_retest_trial`
- `evaluate-leaderboard-gate`
- `record-paper-shadow-outcome`
- arbitrary command args
- shell/subprocesses

## Tasks

### Task 1: Red Test

- [ ] Add fixture candles covering the retest full split window.
- [ ] Create a DRAFT revision with locked split/cost, baseline evidence, and
      holdout backtest evidence.
- [ ] Call `execute_revision_retest_next_task`.
- [ ] Assert:
  - `executed_task_id == "run_walk_forward"`;
  - one walk-forward validation is saved;
  - walk-forward backtest result ids include the previously created holdout
    backtest result id;
  - one execution automation run is saved for the walk-forward step;
  - `after_plan.next_task_id == "record_passed_retest_trial"`;
  - created artifact ids include the saved walk-forward validation id.
- [ ] Add CLI coverage for the same scenario.
- [ ] Run:

```powershell
python -m pytest .\tests\test_research_autopilot.py -k "walk_forward_next_task" -q
```

Expected: FAIL because executor rejects `run_walk_forward`.

### Task 2: Green

- [ ] Import `run_walk_forward_validation`.
- [ ] Dispatch `run_walk_forward`.
- [ ] Require `plan.split_manifest_id`.
- [ ] Load the split manifest and use `split.train_start` to
      `split.holdout_end`.
- [ ] Call
      `run_walk_forward_validation(storage_dir=..., symbol=..., start=split.train_start, end=split.holdout_end, created_at=...)`.
- [ ] Return `[result.validation.validation_id]`.
- [ ] Run focused tests.

Expected: PASS.

### Task 3: Docs, Review, Gates

- [ ] Add `docs/architecture/PR23-revision-retest-walk-forward-executor.md`.
- [ ] Add review archive under `docs/reviews/`.
- [ ] Update README, PRD, and alpha factory background.
- [ ] Run:

```powershell
python -m pytest .\tests\test_research_autopilot.py -k "walk_forward_next_task or backtest_next_task or baseline_next_task or execute_revision_retest_next_task" -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

## Acceptance Criteria

- Executor supports walk-forward validation without shell/subprocess execution.
- Before/after plans show transition from `run_walk_forward` to
  `record_passed_retest_trial`.
- Unsupported later tasks remain blocked.
- Tests and reviewer approval pass.
