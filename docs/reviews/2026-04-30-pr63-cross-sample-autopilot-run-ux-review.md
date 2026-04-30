# PR63 Cross-Sample Autopilot Run UX Review

## Scope

Reviewed branch: `codex/cross-sample-autopilot-run-ux`

PR63 keeps the `lineage_cross_sample_validation_agenda` visible after task-plan
advancement by recovering it from a linked research autopilot run. The dashboard
and operator console cross-sample panels now show linked autopilot run status,
paper-shadow outcome, and next research action.

## Reviewer

- Harvey subagent
- Initial result: `BLOCKED`
- Final result after fix: `APPROVED`

## Blocker Resolved

Harvey found that the first implementation selected the newest same-symbol
cross-sample autopilot run too broadly. That could pair a visible lineage agenda
with an unrelated same-symbol run.

Fix:

- when the current task-plan agenda exists, select the linked autopilot run only
  for that exact agenda;
- when recovering after task-plan advancement, scope candidate cross-sample
  agendas to the current lineage root/revision/replacement ids and task-plan
  root id;
- add same-symbol unrelated-run regressions for both dashboard and operator
  console.

## Verification Evidence

- `python -m pytest .\tests\test_dashboard.py::test_dashboard_shows_lineage_cross_sample_validation_agenda .\tests\test_operator_console.py::test_operator_console_shows_lineage_cross_sample_validation_agenda -q` -> `2 passed`
- `python -m pytest .\tests\test_dashboard.py .\tests\test_operator_console.py -q` -> `66 passed`
- `python -m pytest -q` -> `424 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> CRLF warnings only
- `git ls-files .codex paper_storage reports output .env` -> empty

## Findings

No remaining blocking findings.

