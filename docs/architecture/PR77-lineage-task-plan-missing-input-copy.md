# PR77: Lineage Task Plan Missing Input Copy

## Context

PR72 and PR73 made lineage run-log missing inputs readable in dashboard and
operator console. The primary lineage task-plan panels still listed
`missing_inputs` as raw codes, so a blocked next task could be harder to scan
than its audit log entry.

## Decision

Dashboard and operator console lineage task-plan panels now render missing
inputs through the shared `display_step_artifact("next_task_missing_inputs",
...)` helper.

The display keeps raw codes in parentheses while adding readable copy for known
evidence inputs such as locked evaluation, walk-forward validation, and
paper-shadow outcome.

## Verification

- `python -m pytest .\tests\test_dashboard.py::test_dashboard_lineage_task_plan_translates_missing_inputs -q`
- `python -m pytest .\tests\test_operator_console.py::test_operator_console_lineage_task_plan_translates_missing_inputs -q`

