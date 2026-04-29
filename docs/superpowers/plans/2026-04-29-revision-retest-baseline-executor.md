# Revision Retest Baseline Executor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the revision retest executor from protocol locking to the next evidence-producing task: baseline evaluation.

**Architecture:** Keep PR20's whitelist model. `execute_revision_retest_next_task` will support `generate_baseline_evaluation` by calling the baseline builder directly and saving a `BaselineEvaluation`. It still refuses arbitrary command args and unsupported ready tasks.

**Tech Stack:** Python dataclasses, existing baseline builder, JSONL repository, existing `AutomationRun`, pytest.

---

## Scope

PR21 adds support for:

- `generate_baseline_evaluation`

PR21 still does not execute:

- `backtest`
- `walk-forward`
- `record-experiment-trial`
- `evaluate-leaderboard-gate`
- `record-paper-shadow-outcome`
- arbitrary command args
- shell/subprocesses

## Tasks

### Task 1: Red Test

- [ ] Add a test that creates a DRAFT revision with locked split/cost protocol but no baseline.
- [ ] Call `execute_revision_retest_next_task`.
- [ ] Assert:
  - `executed_task_id == "generate_baseline_evaluation"`;
  - one baseline is saved;
  - one execution automation run is saved;
  - `after_plan.next_task_id == "run_backtest"`;
  - created artifact ids include the saved baseline id.
- [ ] Run:

```powershell
python -m pytest .\tests\test_research_autopilot.py -k "baseline_next_task" -q
```

Expected: FAIL because executor rejects `generate_baseline_evaluation`.

### Task 2: Green

- [ ] Import `build_baseline_evaluation`.
- [ ] Dispatch `generate_baseline_evaluation`.
- [ ] Build the baseline from repository forecasts and scores for the plan symbol.
- [ ] Save the baseline via repository.
- [ ] Return `[baseline.baseline_id]`.
- [ ] Ensure automation run still records `RETEST_TASK_EXECUTED`.
- [ ] Run focused tests.

Expected: PASS.

### Task 3: CLI Coverage

- [ ] Add CLI test for the same scenario.
- [ ] Assert JSON output includes `executed_task_id`, baseline created id, before/after plan transition.
- [ ] Run focused CLI test.

Expected: PASS.

### Task 4: Docs, Review, Gates

- [ ] Add `docs/architecture/PR21-revision-retest-baseline-executor.md`.
- [ ] Add review archive under `docs/reviews/`.
- [ ] Run:

```powershell
python -m pytest .\tests\test_research_autopilot.py -k "baseline_next_task" -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

## Acceptance Criteria

- Executor supports `generate_baseline_evaluation` without shell/subprocess execution.
- Before/after plans show transition from baseline task to backtest task.
- Unsupported retest tasks remain blocked.
- Tests and reviewer approval pass.
