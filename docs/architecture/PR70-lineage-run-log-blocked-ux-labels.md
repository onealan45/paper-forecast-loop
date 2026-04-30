# PR70: Lineage Run Log Blocked UX Labels

## Context

PR69 added `next_task_blocked_reason` and `next_task_missing_inputs` steps to
lineage research task run logs. The dashboard and local operator console already
render automation run steps, but they displayed raw step names. That made the
new blocked context technically visible but weaker for a human operator trying
to understand why the research loop is blocked.

## Decision

Dashboard and operator console run-step renderers now translate the new lineage
blocked context step names into Traditional Chinese labels:

- `next_task_blocked_reason` -> `下一個任務阻擋原因`
- `next_task_missing_inputs` -> `缺少證據輸入`

The underlying automation run artifact is unchanged. Only read-only rendering is
affected.

## Verification

- `python -m pytest .\tests\test_dashboard.py::test_dashboard_run_steps_translate_lineage_blocked_context -q`
- `python -m pytest .\tests\test_operator_console.py::test_operator_console_run_steps_translate_lineage_blocked_context -q`

