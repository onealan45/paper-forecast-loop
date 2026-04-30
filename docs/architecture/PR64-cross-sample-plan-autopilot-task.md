# PR64: Cross-Sample Plan Autopilot Task

## Context

The lineage research task plan previously treated
`verify_cross_sample_persistence` as complete once a
`lineage_cross_sample_validation_agenda` existed. That was enough for the
handoff artifact, but it made the plan layer stop before the actual
fresh-sample validation run was linked back into the research loop.

PR63 made the UX display linked cross-sample autopilot runs when they exist.
PR64 brings the planning layer into the same shape.

## Decision

For improving or strengthening lineages, the plan now emits two cross-sample
tasks:

- `verify_cross_sample_persistence`: create or find the cross-sample validation
  agenda.
- `record_cross_sample_autopilot_run`: require the linked
  `research_autopilot_run` with paper-shadow outcome evidence.

If the agenda exists but no linked run exists, the second task is blocked with
`cross_sample_autopilot_run_missing`. If the linked run exists, the second task
is completed and the plan has no next task for that cross-sample chain.

## Verification

- `python -m pytest tests\test_lineage_research_plan.py::test_lineage_research_task_plan_marks_cross_sample_task_complete_when_agenda_exists tests\test_lineage_research_plan.py::test_lineage_research_task_plan_marks_cross_sample_autopilot_task_complete -q`
- `python -m pytest tests\test_lineage_research_plan.py -q`

