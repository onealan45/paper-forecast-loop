# PR86: Lineage Attribution Copy

## Context

Failure attribution copy was readable in the headline strategy conclusion and
detailed paper-shadow panels, but lineage surfaces still rendered raw-only
codes such as `drawdown_breach` and `weak_baseline_edge`. Those lineage panels
are where the user inspects how a strategy evolves, so raw-only attribution made
the research path harder to understand.

## Decision

Reuse the shared failure attribution display helper in lineage surfaces.

Covered surfaces:

- revision tree `Fixes`;
- replacement contribution `Failures`;
- replacement hypothesis panel `Failure attribution`;
- performance verdict `主要失敗`;
- performance trajectory `Failures`.

Examples:

- `drawdown_breach` -> `回撤超標 (drawdown_breach)`
- `weak_baseline_edge` -> `基準優勢不足 (weak_baseline_edge)`

Raw codes remain visible for traceability.

## Scope

- Dashboard strategy lineage display.
- Operator console strategy lineage display.

This PR does not change lineage artifact generation, scoring, or strategy
revision behavior.

## Verification

- `python -m pytest tests/test_dashboard.py::test_dashboard_strategy_lineage_includes_multi_generation_revisions tests/test_operator_console.py::test_operator_console_strategy_lineage_includes_multi_generation_revisions -q`
