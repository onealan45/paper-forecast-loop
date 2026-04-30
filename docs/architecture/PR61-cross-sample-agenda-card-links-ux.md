# PR61: Cross-Sample Agenda Card Links UX

## Context

PR60 made `lineage_cross_sample_validation_agenda.strategy_card_ids` include both
the lineage root strategy and the exact improving replacement strategy when the
latest improvement came from a replacement retest. The dashboard and local
operator console still rendered the agenda hypothesis and acceptance criteria,
but not those structured strategy links.

## Decision

Render `strategy_card_ids` in the cross-sample validation agenda panel in both
read-only UX surfaces:

- static dashboard
- local operator console research page

This keeps the research operator view aligned with the structured artifact:
the target root and replacement strategy cards are visible without opening raw
JSON.

## Verification

- `python -m pytest tests\test_dashboard.py::test_dashboard_shows_lineage_cross_sample_validation_agenda -q`
- `python -m pytest tests\test_operator_console.py::test_operator_console_shows_lineage_cross_sample_validation_agenda -q`
- `python -m pytest tests\test_dashboard.py -q`
- `python -m pytest tests\test_operator_console.py -q`

