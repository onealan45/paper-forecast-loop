# PR27: Revision Retest Completed Chain Visibility

## Goal
Make the strategy research resolver and read-only UX treat a completed revision
retest chain as completed evidence, not as a missing or never-started scaffold.

## Scope
- Update resolver-level revision retest selection so a valid `PASSED` retest
  trial can be attached to the latest DRAFT revision candidate.
- Derive coarse `Next Required` artifacts from available retest evidence:
  split, linked backtest, walk-forward, locked evaluation, leaderboard entry,
  and paper-shadow outcome.
- Keep the command/task-plan executor unchanged; this PR is visibility and
  traceability only.
- Do not add live trading, broker execution, secrets, or runtime artifacts.

## TDD Plan
1. Add a failing resolver regression using the existing end-to-end revision
   retest helper through leaderboard and explicit shadow outcome.
2. Assert the resolved revision candidate shows the `PASSED` retest trial.
3. Assert `retest_next_required_artifacts` is empty after the completed shadow
   outcome exists.
4. Implement the smallest resolver change to pass.
5. Add docs and archive subagent review.

## Verification
- `python -m pytest tests\test_research_autopilot.py -k "completed_revision_retest_chain" -q`
- `python -m pytest -q`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
- `python .\run_forecast_loop.py --help`
- `git diff --check`

## Acceptance Criteria
- Completed revision retest chains no longer look missing in strategy research
  state.
- Pending retest scaffold behavior remains unchanged.
- Final review is performed by a reviewer subagent and archived under
  `docs/reviews/`.
