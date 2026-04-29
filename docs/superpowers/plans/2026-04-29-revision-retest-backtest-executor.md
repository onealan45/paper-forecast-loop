# Revision Retest Backtest Executor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the revision retest executor to run the holdout backtest task after protocol and baseline evidence exist.

**Architecture:** Continue the whitelist executor model. `execute_revision_retest_next_task` will support `run_backtest` by calling the existing `run_backtest` domain function with the locked split holdout window. It will record one execution `AutomationRun` and return before/after plans.

**Tech Stack:** Python dataclasses, existing backtest engine, JSONL repository, existing `AutomationRun`, pytest.

---

## Scope

PR22 adds support for:

- `run_backtest`

PR22 still does not execute:

- `run_walk_forward`
- `record-experiment-trial`
- `evaluate-leaderboard-gate`
- `record-paper-shadow-outcome`
- arbitrary command args
- shell/subprocesses

## Tasks

### Task 1: Red Test

- [ ] Add fixture candles covering the retest holdout window.
- [ ] Create a DRAFT revision with locked split/cost and baseline evidence.
- [ ] Call `execute_revision_retest_next_task`.
- [ ] Assert:
  - `executed_task_id == "run_backtest"`;
  - one backtest run and one backtest result are saved;
  - one execution automation run is saved;
  - `after_plan.next_task_id == "run_walk_forward"`;
  - created artifact ids include the saved backtest result id.
- [ ] Add CLI coverage for the same scenario.
- [ ] Run:

```powershell
python -m pytest .\tests\test_research_autopilot.py -k "backtest_next_task" -q
```

Expected: FAIL because executor rejects `run_backtest`.

### Task 2: Green

- [ ] Import `run_backtest`.
- [ ] Dispatch `run_backtest`.
- [ ] Require `plan.split_manifest_id`.
- [ ] Load the split manifest and use its holdout window.
- [ ] Call `run_backtest(storage_dir=..., symbol=..., start=split.holdout_start, end=split.holdout_end, created_at=...)`.
- [ ] Return `[result.result_id]`.
- [ ] Run focused tests.

Expected: PASS.

### Task 3: Docs, Review, Gates

- [ ] Add `docs/architecture/PR22-revision-retest-backtest-executor.md`.
- [ ] Add review archive under `docs/reviews/`.
- [ ] Update README, PRD, and alpha factory background.
- [ ] Run:

```powershell
python -m pytest .\tests\test_research_autopilot.py -k "backtest_next_task or baseline_next_task or execute_revision_retest_next_task" -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

## Acceptance Criteria

- Executor supports holdout backtest task without shell/subprocess execution.
- Before/after plans show transition from `run_backtest` to `run_walk_forward`.
- Unsupported later tasks remain blocked.
- Tests and reviewer approval pass.
