# PR79: Revision Next Required Readable Copy

## Context

PR78 made revision retest task-plan panels readable, but the surrounding
Revision Retest Scaffold summary still rendered `Next Required` values as raw
artifact codes. That left two adjacent views describing the same research work
with different copy.

## Decision

Dashboard and operator console scaffold `Next Required` lists now use
`display_required_artifacts()`, a shared helper that applies the same required
artifact copy used by task-plan panels.

The displayed values keep raw machine codes in parentheses.

## Verification

- `python -m pytest .\tests\test_automation_step_display.py .\tests\test_dashboard.py::test_dashboard_shows_strategy_revision_retest_scaffold -q`
- `python -m pytest .\tests\test_operator_console.py::test_operator_console_shows_strategy_revision_retest_scaffold -q`

