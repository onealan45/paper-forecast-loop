# PR72: Lineage Run Log Missing Input Copy

## Context

PR69 stored missing input codes in lineage research task run logs, and PR70 made
the field label readable. The missing input value was still a comma-separated
machine-code list such as `locked_evaluation, walk_forward_validation,
paper_shadow_outcome, research_autopilot_run`.

Those codes are useful for automation, but they make the read-only UX slower for
human operators who need to understand which evidence chain is missing.

## Decision

Dashboard and operator console rendering now add readable labels for known
lineage missing-input codes:

- `locked_evaluation` -> `鎖定評估`
- `walk_forward_validation` -> `walk-forward 驗證`
- `paper_shadow_outcome` -> `paper-shadow outcome`
- `research_autopilot_run` -> `research autopilot run`

The raw code list remains visible in parentheses for traceability. The
underlying `AutomationRun.steps` artifact is unchanged.

## Verification

- `python -m pytest .\tests\test_dashboard.py::test_dashboard_run_steps_translate_lineage_blocked_context -q`
- `python -m pytest .\tests\test_operator_console.py::test_operator_console_run_steps_translate_lineage_blocked_context -q`

