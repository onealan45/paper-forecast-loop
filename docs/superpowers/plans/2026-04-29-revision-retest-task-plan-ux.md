# PR17 Revision Retest Task Plan UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface the PR16 read-only revision retest task plan in the static dashboard and local operator console.

**Architecture:** Reuse `build_revision_retest_task_plan` during snapshot construction and store the resulting `RevisionRetestTaskPlan | None` on read-only UX snapshots. Rendering remains defensive: if no valid DRAFT revision exists or the planner cannot resolve required source artifacts, the existing revision candidate UI still renders without task-plan details.

**Tech Stack:** Python dataclasses, existing dashboard/operator console HTML renderers, pytest.

---

## Scope

PR17 only displays the read-only retest task plan. It does not execute task
commands, write new artifacts, run backtests, or add browser automation.

## File Structure

- Modify `src/forecast_loop/dashboard.py`
  - Add `latest_strategy_revision_retest_task_plan` to `DashboardSnapshot`.
  - Build it with a safe helper around `build_revision_retest_task_plan`.
  - Render next task, task status, blocked reason, missing inputs, and command
    args in the existing strategy revision block.
- Modify `src/forecast_loop/operator_console.py`
  - Add the same snapshot field.
  - Render the task plan in the revision candidate panel and strategy preview.
- Modify tests:
  - `tests/test_dashboard.py`
  - `tests/test_operator_console.py`
- Modify docs after green tests:
  - `README.md`
  - `docs/PRD.md`
  - `docs/architecture/alpha-factory-research-background.md`
  - Add `docs/architecture/PR17-revision-retest-task-plan-ux.md`
  - Add final review archive under `docs/reviews/`

## Task 1: Failing UX Tests

- [ ] Add dashboard regression asserting the HTML contains:
  - `下一個 retest 研究任務`
  - `lock_evaluation_protocol`
  - `split_window_inputs_required`
  - `train_start`

- [ ] Add operator console regression asserting the research page contains the
  same task-plan details.

- [ ] Run:

```powershell
python -m pytest .\tests\test_dashboard.py::test_dashboard_shows_revision_retest_task_plan .\tests\test_operator_console.py::test_operator_console_shows_revision_retest_task_plan -q
```

Expected: FAIL because snapshots and renderers do not yet include the task plan.

## Task 2: Snapshot Integration

- [ ] Import:

```python
from forecast_loop.revision_retest_plan import RevisionRetestTaskPlan, build_revision_retest_task_plan
```

- [ ] Add snapshot field:

```python
latest_strategy_revision_retest_task_plan: RevisionRetestTaskPlan | None
```

- [ ] Add safe helper:

```python
def _safe_revision_retest_task_plan(repository, storage_dir, symbol, revision_card):
    if revision_card is None:
        return None
    try:
        return build_revision_retest_task_plan(
            repository=repository,
            storage_dir=storage_dir,
            symbol=symbol,
            revision_card_id=revision_card.card_id,
        )
    except ValueError:
        return None
```

## Task 3: Rendering

- [ ] Dashboard renderer shows a compact task-plan block under `Revision Retest
Scaffold`:
  - `下一個 retest 研究任務`
  - task id/status
  - required artifact
  - missing inputs
  - blocked reason
  - command args when present

- [ ] Operator console renderer shows the same information in both research page
and overview preview.

## Task 4: Verification And Review

- [ ] Run targeted tests.
- [ ] Run full gates:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

- [ ] Request one final reviewer subagent.
- [ ] Archive review under `docs/reviews/2026-04-29-pr17-revision-retest-task-plan-ux-review.md`.

## Acceptance Criteria

- Dashboard shows the next retest research task and why it is blocked or ready.
- Operator console shows the same task-plan details.
- UX remains read-only.
- No task execution is added.
- Tests and reviewer approval pass.
