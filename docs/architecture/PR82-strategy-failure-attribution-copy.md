# PR82: Strategy Failure Attribution Copy

## Context

PR81 added a shared strategy research conclusion line, but failure attribution
still appeared as raw machine codes such as `negative_excess_return`. That kept
traceability but made the top-level strategy conclusion less useful for a human
operator.

## Decision

Add shared display copy for strategy failure attributions in the strategy
research conclusion.

Examples:

- `negative_excess_return` -> `負超額報酬 (negative_excess_return)`
- `breakout_reversed` -> `突破後反轉 (breakout_reversed)`
- `drawdown_breach` -> `回撤超標 (drawdown_breach)`

Unknown attribution codes remain raw. This avoids hiding new research failure
modes before the codebase has an explicit display label for them.

## Scope

- Dashboard strategy research conclusion.
- Operator console strategy research conclusion.
- Shared helper in `strategy_research_display`.

This PR does not change stored artifact schemas or research scoring logic.

## Verification

- `python -m pytest tests/test_strategy_research_display.py tests/test_dashboard.py::test_dashboard_surfaces_strategy_research_context_before_raw_metadata tests/test_operator_console.py::test_research_page_surfaces_strategy_hypothesis_gates_shadow_and_autopilot -q`
