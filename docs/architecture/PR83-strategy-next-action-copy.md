# PR83: Strategy Next Research Action Copy

## Context

The PR82 strategy research conclusion made failure attribution readable, but the
next research action still appeared as raw automation text such as
`REVISE_STRATEGY`. That kept auditability but made the conclusion feel like a
machine log instead of an operator-facing research summary.

## Decision

Add shared display copy for the strategy conclusion's next research action.

Examples:

- `REVISE_STRATEGY` -> `修訂策略 (REVISE_STRATEGY)`
- `REPAIR_EVIDENCE_CHAIN` -> `修復證據鏈 (REPAIR_EVIDENCE_CHAIN)`
- `PROMOTION_READY` -> `可進入下一階段 (PROMOTION_READY)`

Unknown action codes remain raw so new research actions are not mislabeled.

## Scope

- Shared strategy research conclusion helper.
- Dashboard strategy research conclusion.
- Operator console strategy research conclusion.
- The missing paper-shadow outcome branch, so repair-oriented conclusions do not
  fall back to raw-only action text.

This PR does not change stored artifacts, autopilot behavior, or promotion
logic.

## Verification

- `python -m pytest tests/test_strategy_research_display.py tests/test_dashboard.py::test_dashboard_surfaces_strategy_research_context_before_raw_metadata tests/test_operator_console.py::test_research_page_surfaces_strategy_hypothesis_gates_shadow_and_autopilot -q`
