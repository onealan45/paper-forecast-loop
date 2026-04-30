# PR64 Cross-Sample Plan Autopilot Task Review

## Scope

Reviewed branch: `codex/cross-sample-plan-autopilot-task`

PR64 extends the lineage research task plan so cross-sample validation does not
stop at agenda creation. Once a `lineage_cross_sample_validation_agenda` exists,
the plan now requires a linked `research_autopilot_run` with valid
paper-shadow outcome evidence before the cross-sample chain is fully complete.

## Reviewer

- Harvey subagent
- Initial result: `BLOCKED`
- Final result after fixes: `APPROVED`

## Blockers Resolved

Harvey found three issues in earlier drafts:

- The plan lost the original cross-sample agenda after a distinct fresh-sample
  outcome advanced `latest_outcome_id`.
- Blocked runs or runs pointing at missing paper-shadow outcomes could be
  treated as completed validation.
- A stale completed cross-sample run for an older lineage outcome could
  incorrectly complete a newer same-lineage improvement.

Fixes:

- recover the original agenda through linked cross-sample autopilot runs for the
  current lineage;
- require the run to be unblocked and to link an existing paper-shadow outcome
  for the current lineage;
- require the run's `paper_shadow_outcome_id` to match the current
  `summary.latest_outcome_id`.

## Verification Evidence

- `python -m pytest .\tests\test_lineage_research_plan.py::test_lineage_research_task_plan_does_not_reuse_stale_cross_sample_run_for_newer_outcome .\tests\test_lineage_research_plan.py::test_lineage_research_task_plan_marks_cross_sample_autopilot_task_complete .\tests\test_lineage_research_plan.py::test_lineage_research_task_plan_marks_cross_sample_task_complete_when_agenda_exists -q` -> `3 passed`
- `python -m pytest .\tests\test_lineage_research_plan.py .\tests\test_lineage_research_executor.py -q` -> `28 passed`
- `python -m pytest -q` -> `426 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> CRLF warnings only
- `git ls-files .codex paper_storage reports output .env` -> empty

## Findings

No remaining blocking findings.

