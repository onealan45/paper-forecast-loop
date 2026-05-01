# PR91: Lineage Attribution Count Copy

## Context

PR86 made individual lineage failure-attribution references readable in revision
trees, replacement contributions, verdicts, and trajectories. PR90 then made
lineage action-count aggregates readable. The remaining aggregate gap was
`failure_attribution_counts`, which still rendered raw-only keys such as
`drawdown_breach` and `weak_baseline_edge`.

## Decision

Render lineage failure-attribution aggregate keys through the shared
failure-attribution formatter in dashboard and operator-console views.

Examples:

- `drawdown_breach` -> `回撤超標 (drawdown_breach)`
- `weak_baseline_edge` -> `基準優勢不足 (weak_baseline_edge)`

The count values remain unchanged.

## Scope

- Dashboard strategy lineage failure-attribution count display.
- Operator console strategy lineage failure-attribution count display.
- Operator overview strategy lineage preview failure-attribution list.

This PR does not change stored lineage artifacts, lineage summary generation,
CLI JSON output, failure routing, or research execution logic.

## Verification

- `python -m pytest tests/test_dashboard.py::test_dashboard_strategy_lineage_includes_multi_generation_revisions tests/test_operator_console.py::test_operator_console_strategy_lineage_includes_multi_generation_revisions -q`
