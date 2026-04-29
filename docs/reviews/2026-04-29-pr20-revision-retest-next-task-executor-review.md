# PR20 Revision Retest Next Task Executor Review

## Scope

PR20 adds `execute-revision-retest-next-task` for the revision retest chain.
This PR supports only `lock_evaluation_protocol` and writes an execution
`AutomationRun`.

## Review Status

Reviewer subagent found one P2:

- The executor discarded the deterministic split manifest returned by
  `lock_evaluation_protocol` and reported the pre-existing plan split id in
  `created_artifact_ids`.

Resolution:

- `_execute_lock_evaluation_protocol` now returns the actual split id returned
  by `lock_evaluation_protocol`.
- Regression coverage now asserts `created_artifact_ids` matches the
  `after_plan` split id and cost model id.

Final re-review:

- `APPROVED`.
- Original P2 is closed.
- No remaining blocking findings.

## Verification To Archive

- `python -m pytest .\tests\test_research_autopilot.py -k "execute_revision_retest_next_task" -q`
- `python -m pytest -q`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
- `python .\run_forecast_loop.py --help`
- `git diff --check`

## Results

- Focused executor tests: `3 passed, 35 deselected`.
- Full pytest: `338 passed`.
- Compileall: passed.
- CLI help: passed.
- `git diff --check`: exit 0, LF/CRLF warnings only.
