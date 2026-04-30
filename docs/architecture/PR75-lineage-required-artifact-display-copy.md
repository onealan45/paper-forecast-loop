# PR75: Lineage Required Artifact Display Copy

## Context

PR74 made each lineage task run log explicitly carry the next task's required
artifact. The new step was machine-readable, but without display copy the
dashboard and operator console could still show raw-only values such as
`next_task_required_artifact` and `research_autopilot_run`.

## Decision

The shared `forecast_loop.automation_step_display` helper now translates:

- `next_task_required_artifact` -> `下一個任務要求產物`
- `strategy_card` -> `策略卡`
- `paper_shadow_outcome` -> `paper-shadow 結果`
- `research_agenda` -> `研究議程`
- `research_autopilot_run` -> `研究自動化執行紀錄`

The raw artifact code is still rendered in parentheses. This keeps the operator
view readable while preserving traceability for automation consumers.

## Verification

- `python -m pytest .\tests\test_automation_step_display.py -q`
