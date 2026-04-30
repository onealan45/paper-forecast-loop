# PR78: Revision Retest Task Plan Readable Copy

## Context

PR75 through PR77 made lineage task plans and run logs easier to read by
showing Traditional Chinese copy while preserving raw machine codes. Revision
retest task-plan panels still rendered required artifacts and missing inputs as
raw codes.

## Decision

Dashboard and operator console revision retest task-plan panels now reuse the
same `display_step_artifact` helper for:

- required artifact values such as `cost_model_snapshot` and `split_manifest`;
- missing input values such as `train_start`, `validation_end`, and
  `storage_dir`.

The raw codes remain visible in parentheses for traceability.

## Verification

- `python -m pytest .\tests\test_dashboard.py::test_dashboard_shows_revision_retest_task_plan .\tests\test_dashboard.py::test_dashboard_revision_retest_task_plan_translates_missing_inputs -q`
- `python -m pytest .\tests\test_operator_console.py::test_operator_console_shows_revision_retest_task_plan .\tests\test_operator_console.py::test_operator_console_revision_retest_task_plan_translates_missing_inputs -q`

