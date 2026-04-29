# Revision Retest Run Log UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface PR18 revision retest task run logs in the dashboard and operator console next to the existing retest task plan.

**Architecture:** Reuse existing `AutomationRun` artifacts. The UX will select the latest research `AutomationRun` created by `record-revision-retest-task-run` and render it as read-only audit context beside the current retest task plan. It will not execute retest commands or mutate strategy artifacts.

**Tech Stack:** Python dataclasses, current JSONL repository, static dashboard HTML, operator-console HTML, pytest.

---

## Scope

This PR only shows run-log evidence for the current revision retest task plan.

It does not:
- execute `backtest`, `walk-forward`, or trial recording commands;
- mark retest tasks complete;
- evaluate leaderboard gates;
- write new artifacts from dashboard/operator-console rendering.

## File Structure

- Modify `src/forecast_loop/dashboard.py`
  - Load `automation_runs.jsonl`.
  - Add `latest_strategy_revision_retest_task_run` to `DashboardSnapshot`.
  - Render a compact `最新 retest task run log` block under the existing retest task plan.
- Modify `src/forecast_loop/operator_console.py`
  - Add `latest_strategy_revision_retest_task_run` to `OperatorConsoleSnapshot`.
  - Render the same retest-specific audit block inside research pages/previews.
- Modify `tests/test_dashboard.py`
  - Add a failing test that seeds a revision retest scaffold and matching `AutomationRun`, then expects the dashboard to show retest run status, run id, and command.
- Modify `tests/test_operator_console.py`
  - Add a failing test for the operator console research page and overview preview.
- Add `docs/architecture/PR19-revision-retest-run-log-ux.md`
  - Document read-only UX behavior and non-execution boundary.
- Add `docs/reviews/2026-04-29-pr19-revision-retest-run-log-ux-review.md`
  - Archive final subagent review result after implementation.

## Tasks

### Task 1: Dashboard Red Test

- [ ] Add `test_dashboard_shows_revision_retest_task_run_log`.
- [ ] Seed a revision retest scaffold with `_seed_dashboard_revision_retest_scaffold`.
- [ ] Save an `AutomationRun` with:
  - `automation_run_id="automation-run:dashboard-retest-task"`
  - `status="RETEST_TASK_BLOCKED"`
  - `symbol="BTC-USD"`
  - `provider="research"`
  - `command="revision-retest-plan"`
  - `decision_basis="revision_retest_task_plan_run_log"`
  - a step named `lock_evaluation_protocol`.
- [ ] Assert rendered HTML contains:
  - `最新 retest task run log`
  - `automation-run:dashboard-retest-task`
  - `RETEST_TASK_BLOCKED`
  - `revision-retest-plan`
  - `lock_evaluation_protocol`
- [ ] Run:

```powershell
python -m pytest .\tests\test_dashboard.py::test_dashboard_shows_revision_retest_task_run_log -q
```

Expected: FAIL because the dashboard does not render retest task run logs yet.

### Task 2: Dashboard Green

- [ ] Import `AutomationRun` in `src/forecast_loop/dashboard.py`.
- [ ] Add `latest_strategy_revision_retest_task_run: AutomationRun | None` to `DashboardSnapshot`.
- [ ] Load automation runs and filter with:

```python
run.symbol == dashboard_symbol
and run.provider == "research"
and run.command == "revision-retest-plan"
and run.decision_basis == "revision_retest_task_plan_run_log"
```

- [ ] Pick the latest by `completed_at`.
- [ ] Render a read-only block under `_render_revision_retest_task_plan` output.
- [ ] Run the dashboard test again.

Expected: PASS.

### Task 3: Operator Console Red Test

- [ ] Add `test_operator_console_shows_revision_retest_task_run_log`.
- [ ] Seed a visible revision retest scaffold and matching `AutomationRun`.
- [ ] Render both `research` and `overview`.
- [ ] Assert both pages contain:
  - `最新 retest task run log`
  - `automation-run:visible-retest-task`
  - `RETEST_TASK_READY`
  - `revision-retest-plan`
- [ ] Run:

```powershell
python -m pytest .\tests\test_operator_console.py::test_operator_console_shows_revision_retest_task_run_log -q
```

Expected: FAIL because operator console does not render retest-specific run logs in research surfaces yet.

### Task 4: Operator Console Green

- [ ] Add `latest_strategy_revision_retest_task_run: AutomationRun | None` to `OperatorConsoleSnapshot`.
- [ ] Reuse the same retest run filtering rule.
- [ ] Render the retest run log in `_strategy_revision_panel` and `_strategy_research_preview`.
- [ ] Run the operator console test again.

Expected: PASS.

### Task 5: Docs, Review, Gates

- [ ] Add PR19 architecture doc.
- [ ] Run focused tests:

```powershell
python -m pytest .\tests\test_dashboard.py::test_dashboard_shows_revision_retest_task_run_log .\tests\test_operator_console.py::test_operator_console_shows_revision_retest_task_run_log -q
```

- [ ] Run full gates:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

- [ ] Use reviewer subagent only for review.
- [ ] Archive review under `docs/reviews/2026-04-29-pr19-revision-retest-run-log-ux-review.md`.

## Acceptance Criteria

- Dashboard shows the latest PR18 retest task run log next to the retest task plan.
- Operator console research surfaces show the latest PR18 retest task run log.
- The UX explicitly remains read-only and does not execute command args.
- Focused tests and full gates pass.
- Final reviewer subagent has no blocking findings.
