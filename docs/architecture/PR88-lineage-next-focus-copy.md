# PR88: Lineage Next Research Focus Copy

## Context

Lineage verdicts and actions were readable, but the `下一步研究焦點` sentence
still embedded raw failure attribution tokens such as `drawdown_breach`.
That sentence is an operator-facing research instruction, so it should read as
human language first.

## Decision

Display lineage `next_research_focus` with readable failure attribution copy in
dashboard and operator console.

Example:

- `停止加碼此 lineage，優先研究 drawdown_breach 的修正或新策略。`
- becomes `停止加碼此 lineage，優先研究 回撤超標 (drawdown_breach) 的修正或新策略。`

The underlying `StrategyLineageSummary.next_research_focus` value remains
unchanged so CLI and automation consumers keep the raw machine token.

## Scope

- Dashboard strategy lineage display.
- Operator console strategy lineage display and overview preview.

This PR does not change lineage summary generation, CLI JSON payloads, or
research-agenda generation.

## Verification

- `python -m pytest tests/test_dashboard.py::test_dashboard_strategy_lineage_includes_multi_generation_revisions tests/test_operator_console.py::test_operator_console_strategy_lineage_includes_multi_generation_revisions -q`
