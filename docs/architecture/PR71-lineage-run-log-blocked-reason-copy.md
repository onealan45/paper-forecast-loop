# PR71: Lineage Run Log Blocked Reason Copy

## Context

PR70 translated lineage blocked-context step labels in the dashboard and
operator console. The blocked reason value itself still appeared as the raw
machine code `cross_sample_autopilot_run_missing`, which is useful for
traceability but not ideal as the only human-facing explanation.

## Decision

When rendering automation run steps for dashboard or operator console, the
`next_task_blocked_reason` artifact value
`cross_sample_autopilot_run_missing` is displayed as:

`缺少 cross-sample autopilot run (cross_sample_autopilot_run_missing)`

This preserves the raw reason code while adding a short readable reason for the
operator. The underlying `AutomationRun.steps` artifact remains unchanged.

## Verification

- `python -m pytest .\tests\test_dashboard.py::test_dashboard_run_steps_translate_lineage_blocked_context -q`
- `python -m pytest .\tests\test_operator_console.py::test_operator_console_run_steps_translate_lineage_blocked_context -q`

