# PR81: Strategy Research Conclusion Copy

## Context

The strategy research UX already exposed strategy cards, gates, leaderboard
state, paper-shadow attribution, and autopilot next actions. Operators still had
to mentally combine those fields to answer the core question: what does the
latest research say about this strategy right now?

## Decision

Add a shared `build_strategy_research_conclusion()` helper that summarizes:

- current strategy name;
- paper-shadow outcome grade;
- after-cost excess return when available;
- failure attribution when available;
- next research action from the autopilot run, falling back to the
  paper-shadow recommendation.

Dashboard and operator console both render this conclusion before detailed
artifact tables. The detailed artifacts remain visible for auditability.

## Verification

- `python -m pytest .\tests\test_strategy_research_display.py .\tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_context_before_raw_metadata .\tests\test_operator_console.py::test_research_page_surfaces_strategy_hypothesis_gates_shadow_and_autopilot -q`

