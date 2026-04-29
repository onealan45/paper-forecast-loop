# PR30: Revision Retest Autopilot Run UX

## Goal

Expose the latest revision-scoped `ResearchAutopilotRun` in the dashboard and
operator console so completed revision retest loops are visible from the
read-only strategy surfaces.

## Scope

- Add snapshot field for latest revision retest autopilot run.
- Select only runs whose `strategy_card_id` matches the latest DRAFT revision
  card.
- Render the run beside the revision retest task plan and task-run log.
- Do not change the retest executor, autopilot recorder, strategy promotion, or
  broker/sandbox code paths.

## TDD Plan

1. Add failing dashboard test with a revision-scoped `ResearchAutopilotRun`.
2. Add failing operator console test for research and overview pages.
3. Add snapshot selection and render helpers.
4. Keep existing parent-strategy autopilot visibility intact.

## Verification

- `python -m pytest tests\test_dashboard.py -k "revision_retest_autopilot_run" tests\test_operator_console.py -k "revision_retest_autopilot_run" -q`
- `python -m pytest -q`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
- `python .\run_forecast_loop.py --help`
- `git diff --check`

## Acceptance Criteria

- Dashboard shows the latest revision retest autopilot run.
- Operator console research and overview surfaces show the same run.
- Parent strategy autopilot run is not mislabeled as revision retest evidence.
- Final review is performed by a reviewer subagent and archived under
  `docs/reviews/`.
