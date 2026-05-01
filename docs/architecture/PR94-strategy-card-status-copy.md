# PR94: Strategy Card Status Copy

## Context

Strategy research panels now render action, outcome, promotion, and failure
codes as readable labels with raw codes retained. Strategy-card lifecycle status
still appeared as raw-only values such as `ACTIVE` and `DRAFT` across current
strategy, revision, replacement, and lineage surfaces.

## Decision

Add a shared `format_strategy_card_status` display helper and use it wherever
dashboard or operator console renders strategy-card status.

Examples:

- `ACTIVE` -> `啟用 (ACTIVE)`
- `DRAFT` -> `草稿 (DRAFT)`
- `QUARANTINED` -> `隔離中 (QUARANTINED)`
- `RETIRED` -> `已淘汰 (RETIRED)`

Unknown status values remain unchanged so new machine codes stay visible rather
than being mislabeled.

## Scope

- Dashboard current strategy status, revision status, replacement status, and
  lineage node status rows.
- Operator console current strategy status, revision status, replacement status,
  and lineage node status rows.
- Shared strategy research display formatter.

This PR does not change strategy-card artifacts, strategy lifecycle state,
promotion behavior, CLI JSON, or execution logic.

## Verification

- `python -m pytest tests/test_strategy_research_display.py::test_format_strategy_card_status_keeps_raw_code_with_readable_label tests/test_dashboard.py::test_dashboard_surfaces_strategy_research_context_before_raw_metadata tests/test_dashboard.py::test_dashboard_strategy_lineage_includes_multi_generation_revisions tests/test_operator_console.py::test_research_page_surfaces_strategy_hypothesis_gates_shadow_and_autopilot tests/test_operator_console.py::test_operator_console_strategy_lineage_includes_multi_generation_revisions -q`
