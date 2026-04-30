# PR59: Lineage Cross-Sample Agenda UX

## Context

PR58 made `verify_cross_sample_persistence` executable by writing a
`lineage_cross_sample_validation_agenda` research handoff artifact. That agenda
was technically traceable through the lineage task artifact id, but the
dashboard and local operator console did not show its hypothesis, expected
artifacts, or acceptance criteria.

## Decision

Expose the latest lineage cross-sample validation agenda as first-class
read-only strategy research context in both UX surfaces.

The snapshot resolves the agenda only through the current lineage research task
plan:

- the task must be `verify_cross_sample_persistence`
- the task must have an artifact id
- the artifact id must point to a `ResearchAgenda`
- the agenda `decision_basis` must be `lineage_cross_sample_validation_agenda`

This avoids showing stale unrelated cross-sample agendas.

## UX Content

The panel shows:

- agenda id
- priority
- decision basis
- hypothesis
- expected artifacts
- acceptance criteria

The panel explicitly frames the agenda as a fresh-sample validation handoff, not
as passed validation evidence.

## Verification

- `python -m pytest tests\test_dashboard.py::test_dashboard_shows_lineage_cross_sample_validation_agenda -q`
- `python -m pytest tests\test_operator_console.py::test_operator_console_shows_lineage_cross_sample_validation_agenda -q`
- `python -m pytest tests\test_dashboard.py -q`
- `python -m pytest tests\test_operator_console.py -q`

