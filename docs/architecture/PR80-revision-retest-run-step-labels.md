# PR80: Revision Retest Run Step Labels

## Context

Revision retest task-plan panels and scaffold summaries now use readable copy,
but revision retest task run logs still displayed raw step names such as
`revision_card`, `source_outcome`, and `lock_evaluation_protocol`.

## Decision

The shared `display_step_name()` helper now translates those revision retest
run-step names:

- `revision_card` -> `修正策略卡`
- `source_outcome` -> `來源 paper-shadow 結果`
- `lock_evaluation_protocol` -> `鎖定評估協議`

Dashboard and operator console run-log renderers already use this helper, so
both views receive the labels without separate UI logic.

## Verification

- `python -m pytest .\tests\test_automation_step_display.py .\tests\test_dashboard.py::test_dashboard_run_steps_translate_revision_retest_context -q`
- `python -m pytest .\tests\test_operator_console.py::test_operator_console_run_steps_translate_revision_retest_context -q`

