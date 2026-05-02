# PR133 Reuse Retest Split Windows Review

## Reviewer

- Subagent reviewer: Helmholtz (`gpt-5.5`, `xhigh`)
- Role: final reviewer plus contract/replay risk reviewer
- Scope: PR133 uncommitted diff

## Initial Blocking Findings

### P1: Cross-card retest evidence can still be selected

The first review found that the pending-trial selector could accept same-window
backtest and walk-forward evidence created for a different strategy card because
selection only checked symbol, window, and timestamp.

Resolution:

- Pending-trial backtest selection now checks the linked `BacktestRun`
  `decision_basis` for the current revision-retest `id_context`.
- Pending-trial walk-forward selection now checks
  `WalkForwardValidation.decision_basis` for the current revision-retest
  `id_context`.
- Added regression tests for cross-card backtest and walk-forward rejection.

### P1: PASSED-trial path can still inherit cross-card evidence

The second review found that `_latest_valid_passed_retest_trial` could accept a
current-card `PASSED` trial pointing at another card's retest evidence.

Resolution:

- PASSED-trial validation now requires linked backtest and walk-forward evidence
  to carry the same retest chain context.
- Because valid evidence is produced while the source trial is still `PENDING`,
  PASSED-trial validation accepts the source pending-trial context only when the
  pending trial matches strategy card, symbol, dataset, trial index, protocol,
  source card, and source outcome.
- Added regression coverage for a polluted PASSED trial with cross-card evidence.

## Final Result

Final reviewer response: `APPROVED`.

Reviewer verification:

- Reproduced cross-context PASSED pollution in a temporary directory and
  confirmed `plan_passed=None`.
- Confirmed a legitimate `run_backtest -> run_walk_forward ->
  record_passed_retest_trial` chain still advances to `evaluate_leaderboard_gate`.
- Ran targeted pytest: `3 passed`.
- Ran `git diff --check`: exit 0 with CRLF warnings only.
- Did not modify files.

## Local Verification

- `python -m pytest tests\test_research_autopilot.py::test_revision_retest_task_plan_reuses_existing_dataset_split_windows tests\test_research_autopilot.py::test_execute_revision_retest_next_task_locks_protocol_from_reusable_split -q` -> `2 passed`
- `python -m pytest tests\test_research_autopilot.py::test_revision_retest_plan_rejects_passed_trial_with_cross_card_evidence_context tests\test_research_autopilot.py::test_revision_retest_task_plan_does_not_record_passed_trial_from_unlinked_evidence tests\test_research_autopilot.py::test_revision_retest_autopilot_helper_records_latest_completed_chain -q` -> `3 passed`
- `python -m pytest tests\test_research_autopilot.py -q` -> `90 passed`
- `python -m pytest -q` -> `510 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> pass
- `python .\run_forecast_loop.py --help` -> pass
- `git diff --check` -> exit 0 with CRLF warnings only

## Decision

PR133 is approved for publish and merge after normal GitHub checks pass.
