# PR73: Shared Automation Step Display Copy

## Context

PR70 through PR72 improved lineage blocker readability in both the static
dashboard and the local operator console. The display logic was intentionally
small, but it existed in two places. That created a drift risk: future blocker
labels or artifact copy could be added to one UX surface and missed in the
other.

## Decision

Automation step display copy now lives in
`forecast_loop.automation_step_display`:

- `display_step_name(name)` translates known step names;
- `display_step_artifact(name, artifact_id)` adds readable copy for known
  blocked reasons and missing input lists while preserving raw machine codes.

Dashboard and operator console both call this shared helper. The underlying
`AutomationRun.steps` artifacts remain unchanged.

## Verification

- `python -m pytest .\tests\test_automation_step_display.py -q`
- `python -m pytest .\tests\test_dashboard.py::test_dashboard_run_steps_translate_lineage_blocked_context .\tests\test_operator_console.py::test_operator_console_run_steps_translate_lineage_blocked_context -q`

