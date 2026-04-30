# PR84: Strategy Outcome And Metric Copy

## Context

The top-level strategy research conclusion had readable failure attribution and
next action copy, but still rendered `paper-shadow FAIL` and
`after-cost excess`. That made the most important line partially machine-like
for the user.

## Decision

Format paper-shadow outcome grade and the after-cost excess metric in readable
Traditional Chinese while preserving the raw grade code.

Examples:

- `FAIL` -> `失敗 (FAIL)`
- `PASS` -> `通過 (PASS)`
- `BLOCKED` -> `已阻擋 (BLOCKED)`
- `after-cost excess -2.50%` -> `扣成本超額報酬 -2.50%`

Unknown grade codes remain raw.

## Scope

- Shared strategy research conclusion helper.
- Dashboard strategy research conclusion.
- Operator console strategy research conclusion.

This PR does not change stored artifacts, paper-shadow scoring, or promotion
logic.

## Verification

- `python -m pytest tests/test_strategy_research_display.py tests/test_dashboard.py::test_dashboard_surfaces_strategy_research_context_before_raw_metadata tests/test_operator_console.py::test_research_page_surfaces_strategy_hypothesis_gates_shadow_and_autopilot -q`
