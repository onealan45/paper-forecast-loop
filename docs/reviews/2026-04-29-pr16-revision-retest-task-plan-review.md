# PR16 Revision Retest Task Plan Review

## Scope

Branch: `codex/revision-retest-task-plan`

PR16 adds a read-only `revision-retest-plan` command and planner that turns a
DRAFT strategy revision and retest scaffold into ordered research tasks. The
planner must not write artifacts, run backtests, invent split windows, or
fabricate evaluation results.

## Reviewer Role

Role: `docs/roles/reviewer.md`

Review rule: review was performed by subagents only; implementation did not
self-approve.

## Findings And Fixes

### Finding 1: PASSED retest could be fake-completed without evidence

Severity: P1

Reviewer found that a `PASSED` retest trial without linked backtest and
walk-forward evidence could be treated as completed.

Fix:

- Added `test_revision_retest_task_plan_does_not_complete_malformed_passed_trial`.
- Planner now only recognizes `PASSED` retest trials when they include
  `dataset_id`, `backtest_result_id`, `walk_forward_validation_id`, matching
  symbol/protocol/source IDs, and resolved linked artifacts.

### Finding 2: Read-only CLI could create typo storage directories

Severity: P2

Reviewer found that constructing `JsonFileRepository` before validation could
create a nonexistent storage directory.

Fix:

- Added
  `test_cli_revision_retest_plan_rejects_missing_storage_without_creating_directory`.
- CLI now validates `storage_dir` exists and is a directory before constructing
  `JsonFileRepository`.

### Finding 3: PASSED retest evidence could come from the wrong split

Severity: P1

Reviewer found that a `PASSED` retest trial could link same-symbol evidence that
did not match the locked retest split window.

Fix:

- Added
  `test_revision_retest_task_plan_rejects_passed_trial_linked_to_wrong_split`.
- Planner now requires linked backtest `start/end` to match
  `split.holdout_start/holdout_end`.
- Planner now requires linked walk-forward `start/end` to match
  `split.train_start/holdout_end`.

### Finding 4: Planner could propose PASSED trial from unlinked evidence

Severity: P1

Reviewer found that `record_passed_retest_trial` could become ready from a
split-aligned backtest and walk-forward pair that were not internally linked.

Fix:

- Added
  `test_revision_retest_task_plan_does_not_record_passed_trial_from_unlinked_evidence`.
- Planner now requires `backtest.result_id in walk_forward.backtest_result_ids`
  before it can emit a `record-experiment-trial --status PASSED` command.

## Final Reviewer Result

Final reviewer result: `APPROVED`.

Final reviewer summary:

> No P1/P2 blocker remained in the working-tree PR16 changes. Planner/CLI paths
> remain read-only, missing storage does not create directories, missing split
> does not emit a command, and PASSED retest requires split-aligned,
> backtest/walk-forward-linked evidence. `command_args` did not fabricate split
> windows, directly run backtests, or pretend evaluation completed.

## Verification

Implementer verification:

```powershell
python -m pytest .\tests\test_research_autopilot.py -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Results:

- `tests/test_research_autopilot.py`: 32 passed
- Full pytest: 326 passed
- `compileall`: passed
- CLI help: passed and included `revision-retest-plan`
- `git diff --check`: exit 0; CRLF warnings only

Final reviewer verification:

- `python -m pytest -p no:cacheprovider .\tests\test_research_autopilot.py -q`
  returned 32 passed.
- `git diff --check` returned exit 0 with CRLF warnings only.

## Merge Recommendation

APPROVED for PR creation and merge after normal machine gates and GitHub checks
pass.
