# PR77: Lineage Task Plan Missing Input Copy Review

## Reviewer

- Harvey (`019ddad3-2758-75c1-bb0d-7046ffe645cc`)

## Scope

Review PR77 changes that reuse the shared missing-input display copy in
dashboard and operator console lineage task-plan panels.

## Change Summary

- Dashboard lineage task-plan `Missing Inputs` now renders through
  `display_step_artifact("next_task_missing_inputs", ...)`.
- Operator console lineage task-plan `Missing inputs` uses the same helper.
- Empty missing-input lists render as `無`.
- Regression tests assert readable copy plus raw machine codes for blocked
  lineage next-task evidence gaps.
- README, PRD, and architecture notes document the behavior.

## Verification

- `python -m pytest .\tests\test_dashboard.py::test_dashboard_lineage_task_plan_translates_missing_inputs .\tests\test_operator_console.py::test_operator_console_lineage_task_plan_translates_missing_inputs -q`
- `python -m pytest -q`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
- `python .\run_forecast_loop.py --help`
- `git diff --check`
- `git ls-files .codex paper_storage reports output .env`

## Final Review

Harvey reviewed the diff and replied: `APPROVED`.

