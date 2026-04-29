# PR18 Revision Retest Task Run Log Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record the latest revision retest task plan as an audit-visible run log without executing any task commands.

**Architecture:** Reuse the existing `AutomationRun` artifact instead of adding a new table/model. A new helper builds the PR16 `RevisionRetestTaskPlan`, converts task statuses into automation-run steps, writes exactly one automation run, and returns both the run and the task plan for CLI output.

**Tech Stack:** Python dataclasses, current `AutomationRun` model/storage, existing JSONL repository, existing CLI parser, pytest.

---

## Scope

PR18 records a planning/run-log artifact only. It does not run `backtest`,
`walk-forward`, `record-experiment-trial`, `evaluate-leaderboard-gate`, or any
rendered command args.

## File Structure

- Create `src/forecast_loop/revision_retest_run_log.py`
  - Owns `RevisionRetestRunLogResult`.
  - Builds a task plan via `build_revision_retest_task_plan`.
  - Saves one `AutomationRun` with provider `research` and command
    `revision-retest-plan`.
- Modify `src/forecast_loop/cli.py`
  - Adds `record-revision-retest-task-run`.
  - Validates `storage_dir` exists before constructing `JsonFileRepository`.
- Modify `tests/test_research_autopilot.py`
  - Adds tests for blocked/ready run log status, write scope, and CLI JSON.
- Modify docs:
  - `README.md`
  - `docs/PRD.md`
  - `docs/architecture/alpha-factory-research-background.md`
  - Add `docs/architecture/PR18-revision-retest-task-run-log.md`
  - Add final review archive.

## Task 1: Failing Tests

- [ ] Add import:

```python
from forecast_loop.revision_retest_run_log import record_revision_retest_task_run
```

- [ ] Add blocked-plan test:

Create a DRAFT revision and pending scaffold without locked split. Call
`record_revision_retest_task_run`. Assert:

```python
assert result.automation_run.status == "RETEST_TASK_BLOCKED"
assert result.task_plan.next_task_id == "lock_evaluation_protocol"
assert result.automation_run.command == "revision-retest-plan"
assert result.automation_run.provider == "research"
assert any(step["name"] == "lock_evaluation_protocol" and step["status"] == "blocked" for step in result.automation_run.steps)
```

- [ ] Add ready-plan write-scope test:

Create a DRAFT revision scaffold with locked split. Snapshot JSONL files before
calling. Assert that only `automation_runs.jsonl` changes and status is
`RETEST_TASK_READY`.

- [ ] Add CLI test:

Call:

```python
main([
    "record-revision-retest-task-run",
    "--storage-dir", str(tmp_path),
    "--revision-card-id", revision.card_id,
    "--symbol", "BTC-USD",
    "--now", "2026-04-29T09:30:00+00:00",
])
```

Assert JSON contains `automation_run` and `revision_retest_task_plan`, and one
automation run is persisted.

- [ ] Verify RED:

```powershell
python -m pytest .\tests\test_research_autopilot.py -q
```

Expected: FAIL because `forecast_loop.revision_retest_run_log` does not exist.

## Task 2: Implementation

- [ ] Add `RevisionRetestRunLogResult` dataclass with `to_dict`.
- [ ] Implement `record_revision_retest_task_run`.
- [ ] Status mapping:
  - no next task: `RETEST_TASK_COMPLETE`
  - next task `ready`: `RETEST_TASK_READY`
  - next task `blocked`: `RETEST_TASK_BLOCKED`
  - otherwise: `RETEST_TASK_IN_PROGRESS`
- [ ] Steps:
  - one step for `revision_card`
  - one step for `source_outcome`
  - one step per task in `task_plan.tasks`
- [ ] Save exactly one `AutomationRun`.

## Task 3: CLI

- [ ] Add parser:

```python
record_retest_task_run_cmd = subparsers.add_parser("record-revision-retest-task-run")
record_retest_task_run_cmd.add_argument("--storage-dir", required=True)
record_retest_task_run_cmd.add_argument("--revision-card-id")
record_retest_task_run_cmd.add_argument("--symbol", default="BTC-USD")
record_retest_task_run_cmd.add_argument("--now")
```

- [ ] Add handler that validates storage path, calls the helper, and prints JSON.

## Task 4: Verification And Review

- [ ] Run targeted tests.
- [ ] Run full gates:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

- [ ] Request one reviewer subagent.
- [ ] Archive review under
`docs/reviews/2026-04-29-pr18-revision-retest-task-run-log-review.md`.

## Acceptance Criteria

- A user can record the current retest task plan as an `AutomationRun`.
- The command writes only the run log artifact.
- No rendered command args are executed.
- Tests and reviewer approval pass.
