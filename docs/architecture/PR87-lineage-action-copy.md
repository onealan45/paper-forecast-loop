# PR87: Lineage Action Copy

## Context

Lineage attribution labels were readable, but lineage actions still rendered as
raw automation codes such as `QUARANTINE_STRATEGY` and `PROMOTION_READY`.
Those codes are useful for artifact traceability, but the UX should first tell
the human what happened.

## Decision

Reuse the shared research action display helper in lineage surfaces.

Covered surfaces:

- performance verdict `最新動作`;
- performance trajectory `Action`;
- replacement contribution `Action`.

Examples:

- `QUARANTINE_STRATEGY` -> `隔離策略 (QUARANTINE_STRATEGY)`
- `PROMOTION_READY` -> `可進入下一階段 (PROMOTION_READY)`

Raw codes remain visible for traceability.

## Scope

- Dashboard strategy lineage display.
- Operator console strategy lineage display.

This PR does not change lineage artifact generation, action counts, autopilot
logic, or strategy promotion behavior.

## Verification

- `python -m pytest tests/test_dashboard.py::test_dashboard_strategy_lineage_includes_multi_generation_revisions tests/test_operator_console.py::test_operator_console_strategy_lineage_includes_multi_generation_revisions tests/test_dashboard.py::test_dashboard_shows_lineage_replacement_retest_scaffold tests/test_operator_console.py::test_operator_console_shows_lineage_replacement_retest_scaffold -q`
