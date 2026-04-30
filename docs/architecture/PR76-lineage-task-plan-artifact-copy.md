# PR76: Lineage Task Plan Artifact Copy

## Context

PR75 added readable display copy for `next_task_required_artifact` run-log
steps. The lineage task-plan panels still rendered the same required artifact
field directly from `next_task.required_artifact`, so the primary next-task view
could lag behind the audit run-log view.

## Decision

Dashboard and operator console lineage task-plan panels now render required
artifacts through the shared `display_step_artifact("next_task_required_artifact",
...)` helper.

This keeps the raw artifact code visible in parentheses while showing readable
Traditional Chinese copy for known lineage task artifacts such as
`strategy_card`.

## Verification

- `python -m pytest .\tests\test_dashboard.py::test_dashboard_lineage_research_agenda_visibility -q`
- `python -m pytest .\tests\test_operator_console.py::test_operator_console_lineage_research_agenda_visibility -q`

