# PR93: Leaderboard Promotion Copy

## Context

Paper-shadow and lineage strategy status surfaces now render readable labels
with raw codes. The Leaderboard panels still showed promotion stage as raw-only
codes such as `CANDIDATE`, even though those rows sit directly above the
strategy status and paper-shadow evidence.

## Decision

Add a shared `format_promotion_stage` display helper and use it in dashboard and
operator-console Leaderboard panels.

Examples:

- `BLOCKED` -> `已阻擋 (BLOCKED)`
- `CANDIDATE` -> `候選策略 (CANDIDATE)`
- `PAPER_SHADOW_PASSED` -> `paper-shadow 通過 (PAPER_SHADOW_PASSED)`

Unknown promotion-stage values remain unchanged so new machine codes are still
visible instead of being mislabeled.

## Scope

- Dashboard strategy research Leaderboard promotion row.
- Operator console strategy research Leaderboard promotion row.
- Shared strategy research display formatter.

This PR does not change leaderboard artifacts, promotion gates, strategy
promotion behavior, paper-shadow scoring, CLI JSON, or execution logic.

## Verification

- `python -m pytest tests/test_strategy_research_display.py::test_format_promotion_stage_keeps_raw_code_with_readable_label tests/test_dashboard.py::test_dashboard_surfaces_strategy_research_context_before_raw_metadata tests/test_operator_console.py::test_research_page_surfaces_strategy_hypothesis_gates_shadow_and_autopilot -q`
