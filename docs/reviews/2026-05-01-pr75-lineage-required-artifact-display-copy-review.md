# PR75: Lineage Required Artifact Display Copy Review

## Reviewer

- Harvey (`019ddad3-2758-75c1-bb0d-7046ffe645cc`)

## Scope

Review PR75 changes that add Traditional Chinese display copy for
`next_task_required_artifact` run-log steps through the shared
`forecast_loop.automation_step_display` helper.

## Initial Finding

### P2: Required artifact copy still leaves current task artifacts raw-only

Harvey found that the first implementation translated only `research_agenda`
and `research_autopilot_run`, while existing `LineageResearchTask` values also
include `strategy_card` and `paper_shadow_outcome`. That would still leave
dashboard and operator console run logs showing raw-only required artifact copy
for some lineage tasks.

## Resolution

- Added regression assertions for `strategy_card` and `paper_shadow_outcome`.
- Updated `_artifact_copy` to cover all currently emitted lineage
  `required_artifact` values:
  - `strategy_card`
  - `paper_shadow_outcome`
  - `research_agenda`
  - `research_autopilot_run`
- Updated the PR75 architecture note to list the full mapping.

## Verification

- `python -m pytest .\tests\test_automation_step_display.py -q`
- `python -m pytest -q`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
- `python .\run_forecast_loop.py --help`
- `git diff --check`
- `git ls-files .codex paper_storage reports output .env`

## Final Review

Harvey re-reviewed the corrected diff and replied: `APPROVED`.

