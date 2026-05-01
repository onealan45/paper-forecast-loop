# PR89: Autopilot Next Action Copy

## Context

Strategy conclusions and lineage displays already rendered research actions as
readable text plus raw action code. Several autopilot panels still rendered
`next_research_action` as raw-only codes such as `REPAIR_EVIDENCE_CHAIN` and
`UPDATE_LINEAGE_VERDICT`.

## Decision

Route dashboard and operator-console autopilot next-action displays through the
shared research action formatter.

Covered surfaces include:

- strategy research header and next-action card;
- fresh-sample / replacement validation action rows;
- revision retest autopilot run panel;
- lineage replacement retest autopilot run panel;
- operator overview lineage autopilot next step.

Examples:

- `REPAIR_EVIDENCE_CHAIN` -> `修復證據鏈 (REPAIR_EVIDENCE_CHAIN)`
- `UPDATE_LINEAGE_VERDICT` -> `更新 lineage 判定 (UPDATE_LINEAGE_VERDICT)`

Unknown free-form fallback text remains unchanged.

## Scope

- Dashboard autopilot next-action display.
- Operator console autopilot next-action display.

This PR does not change stored autopilot artifacts, task routing, or execution
logic.

## Verification

- `python -m pytest tests/test_dashboard.py::test_dashboard_shows_revision_retest_autopilot_run tests/test_operator_console.py::test_operator_console_shows_revision_retest_autopilot_run tests/test_dashboard.py::test_dashboard_shows_lineage_replacement_retest_scaffold tests/test_operator_console.py::test_operator_console_shows_lineage_replacement_retest_scaffold -q`
