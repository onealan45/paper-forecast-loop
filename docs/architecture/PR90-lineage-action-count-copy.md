# PR90: Lineage Action Count Copy

## Context

PR87 made individual lineage actions readable in verdicts, trajectories, and
replacement contribution rows. The aggregate lineage `action_counts` panel still
rendered raw-only keys such as `QUARANTINE_STRATEGY` and `REVISE_STRATEGY`.
That created a small but visible readability gap in the strategy UX.

## Decision

Render lineage action-count keys through the shared research-action formatter in
dashboard and operator-console views.

Examples:

- `QUARANTINE_STRATEGY` -> `隔離策略 (QUARANTINE_STRATEGY)`
- `REVISE_STRATEGY` -> `修訂策略 (REVISE_STRATEGY)`

The count values remain unchanged.

## Scope

- Dashboard strategy lineage action-count display.
- Operator console strategy lineage action-count display.
- Operator overview strategy lineage preview action list.

This PR does not change stored lineage artifacts, lineage summary generation,
CLI JSON output, action routing, or research execution logic.

## Verification

- `python -m pytest tests/test_dashboard.py::test_dashboard_strategy_lineage_includes_multi_generation_revisions tests/test_operator_console.py::test_operator_console_strategy_lineage_includes_multi_generation_revisions -q`
