# PR92: Paper-Shadow Status Copy

## Context

Strategy research conclusions already rendered paper-shadow outcome grades and
next actions as readable labels with raw codes. The detailed `Paper-shadow 歸因`
panels and operator overview preview still rendered raw-only values such as
`FAIL` and `REVISE_STRATEGY`.

## Decision

Reuse the shared strategy research display formatters for paper-shadow status
surfaces:

- outcome grade uses `format_outcome_grade`;
- recommended action uses `format_research_action`.

Examples:

- `FAIL` -> `失敗 (FAIL)`
- `REVISE_STRATEGY` -> `修訂策略 (REVISE_STRATEGY)`

## Scope

- Dashboard `Paper-shadow 歸因` detail panel.
- Operator console `Paper-shadow 歸因` detail panel.
- Operator overview strategy research preview `Paper-shadow` summary row.

This PR does not change stored paper-shadow artifacts, strategy decisions,
autopilot routing, lineage summaries, or execution logic.

## Verification

- `python -m pytest tests/test_dashboard.py::test_dashboard_surfaces_strategy_research_context_before_raw_metadata tests/test_operator_console.py::test_research_page_surfaces_strategy_hypothesis_gates_shadow_and_autopilot tests/test_operator_console.py::test_operator_console_strategy_lineage_includes_multi_generation_revisions -q`
