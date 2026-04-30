# PR85: Paper-shadow Attribution Detail Copy

## Context

The strategy research conclusion rendered failure attributions as readable
Traditional Chinese plus raw codes, but the detailed `Paper-shadow 歸因` panels
in dashboard and operator console still rendered raw-only attribution lists.
That made the detailed section harder to scan than the headline conclusion.

## Decision

Reuse the shared strategy failure attribution display helper in the detailed
paper-shadow attribution panels.

Examples:

- `negative_excess_return` -> `負超額報酬 (negative_excess_return)`
- `breakout_reversed` -> `突破後反轉 (breakout_reversed)`

Raw codes remain visible for traceability.

## Scope

- Dashboard detailed `Paper-shadow 歸因` panel.
- Operator console detailed `Paper-shadow 歸因` panel.

This PR does not change stored artifacts, paper-shadow scoring, or the headline
strategy conclusion.

## Verification

- `python -m pytest tests/test_dashboard.py::test_dashboard_surfaces_strategy_research_context_before_raw_metadata tests/test_operator_console.py::test_research_page_surfaces_strategy_hypothesis_gates_shadow_and_autopilot -q`
