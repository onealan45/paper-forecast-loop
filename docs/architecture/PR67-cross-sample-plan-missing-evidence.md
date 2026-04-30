# PR67: Cross-Sample Plan Missing Evidence

## Context

The lineage research task plan already blocks cross-sample validation until a
valid linked research autopilot run exists. Before PR67, the blocked task only
reported `research_autopilot_run` as missing, even though the agenda itself
declares the evidence expected before confidence can increase.

That made the plan less useful as an automation handoff: the next worker could
see that a run was missing, but not which fresh-sample evidence had to be linked
into that run.

## Decision

When `record_cross_sample_autopilot_run` is blocked, its `missing_inputs` now
include the cross-sample agenda's `expected_artifacts` followed by
`research_autopilot_run`.

For the current executor-created agenda, this yields:

- `locked_evaluation`
- `walk_forward_validation`
- `paper_shadow_outcome`
- `research_autopilot_run`

The task rationale also states that the linked run must carry the agenda's
expected fresh-sample evidence before the lineage can treat the validation as
complete.

## Verification

- `python -m pytest .\tests\test_lineage_research_plan.py::test_lineage_research_task_plan_marks_cross_sample_task_complete_when_agenda_exists -q`

