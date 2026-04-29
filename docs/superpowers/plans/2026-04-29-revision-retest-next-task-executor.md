# Revision Retest Next Task Executor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the first whitelisted revision retest next task so the research loop can move from inspection to one concrete artifact-producing retest step.

**Architecture:** Reuse the PR16 task planner as the source of truth. A new executor builds the current task plan, requires the next task to be `ready`, supports only `lock_evaluation_protocol` in this PR, calls the existing `lock_evaluation_protocol` domain helper directly, records an `AutomationRun` execution audit, then rebuilds the plan after execution.

**Tech Stack:** Python dataclasses, current `lock_evaluation_protocol` helper, current JSONL repository, existing `AutomationRun`, pytest.

---

## Scope

PR20 executes exactly one whitelisted task:

- `lock_evaluation_protocol`

PR20 does not execute:

- `decide`
- `backtest`
- `walk-forward`
- `record-experiment-trial`
- `evaluate-leaderboard-gate`
- `record-paper-shadow-outcome`
- arbitrary command args
- shell commands or subprocesses

Unsupported ready tasks return a clear error so future PRs can add them one at a
time with tests.

## File Structure

- Create `src/forecast_loop/revision_retest_executor.py`
  - Owns `RevisionRetestTaskExecutionResult`.
  - Owns `execute_revision_retest_next_task`.
  - Calls `build_revision_retest_task_plan`.
  - Dispatches only `lock_evaluation_protocol`.
  - Records an `AutomationRun` with status `RETEST_TASK_EXECUTED`.
- Modify `src/forecast_loop/cli.py`
  - Add `execute-revision-retest-next-task`.
  - Print JSON with `automation_run`, `before_plan`, `after_plan`, and created artifact ids.
- Modify `tests/test_research_autopilot.py`
  - Add function-level executor tests.
  - Add CLI test.
- Add `docs/architecture/PR20-revision-retest-next-task-executor.md`.
- Add `docs/reviews/2026-04-29-pr20-revision-retest-next-task-executor-review.md`.

## Tasks

### Task 1: Executor Red Tests

- [ ] Add a test that creates a DRAFT revision, a pending retest trial, and a locked split manifest without a cost model.
- [ ] Call `execute_revision_retest_next_task`.
- [ ] Assert it creates a cost model, records one automation run, and advances the next task away from `lock_evaluation_protocol`.
- [ ] Add a test that creates a plan whose next ready task is not `lock_evaluation_protocol`.
- [ ] Assert it raises `unsupported_revision_retest_task_execution`.
- [ ] Run:

```powershell
python -m pytest .\tests\test_research_autopilot.py -k "execute_revision_retest_next_task" -q
```

Expected: FAIL because `forecast_loop.revision_retest_executor` does not exist.

### Task 2: Executor Green

- [ ] Create `src/forecast_loop/revision_retest_executor.py`.
- [ ] Implement `execute_revision_retest_next_task`.
- [ ] Require `created_at` to be timezone-aware.
- [ ] Require `task.status == "ready"`.
- [ ] Support only `task.task_id == "lock_evaluation_protocol"`.
- [ ] Find the split manifest by `plan.split_manifest_id`.
- [ ] Call `lock_evaluation_protocol` with the split's train/validation/holdout windows and embargo.
- [ ] Save one `AutomationRun` with:
  - `provider="research"`
  - `command="execute-revision-retest-next-task"`
  - `status="RETEST_TASK_EXECUTED"`
  - `decision_basis="revision_retest_task_execution"`
- [ ] Rebuild and return the after-plan.
- [ ] Run the focused tests.

Expected: PASS.

### Task 3: CLI Red/Green

- [ ] Add CLI parser for `execute-revision-retest-next-task`.
- [ ] Options: `--storage-dir`, `--revision-card-id`, `--symbol`, `--now`.
- [ ] Add a CLI test that asserts JSON output includes:
  - `executed_task_id == "lock_evaluation_protocol"`
  - `automation_run.status == "RETEST_TASK_EXECUTED"`
  - `after_plan.next_task_id == "generate_baseline_evaluation"`
- [ ] Run the focused CLI test.

Expected: PASS after CLI wiring.

### Task 4: Docs, Review, Gates

- [ ] Add PR20 architecture doc.
- [ ] Archive final reviewer result under `docs/reviews/`.
- [ ] Run:

```powershell
python -m pytest .\tests\test_research_autopilot.py -k "execute_revision_retest_next_task" -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

## Acceptance Criteria

- A ready `lock_evaluation_protocol` retest task can be executed without shell/subprocess execution.
- Unsupported ready tasks are rejected clearly.
- Execution writes the expected cost model and one audit `AutomationRun`.
- Before/after plans make the state transition visible.
- Tests and compile gates pass.
- Reviewer subagent approves.
