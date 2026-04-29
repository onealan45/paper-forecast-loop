# PR14 Strategy Revision Retest Scaffold Review

## Scope

Reviewed PR14 implementation for `create-revision-retest-scaffold`.

Files reviewed:

- `src/forecast_loop/revision_retest.py`
- `src/forecast_loop/cli.py`
- `tests/test_research_autopilot.py`
- `README.md`
- `docs/PRD.md`
- `docs/architecture/PR14-strategy-revision-retest-scaffold.md`
- `docs/architecture/alpha-factory-research-background.md`
- `docs/superpowers/plans/2026-04-29-strategy-revision-retest-scaffold.md`

## Reviewer

- Subagent reviewer: `019dd90f-fea4-7142-aa4c-a2a0a286465d`
- Mode: review-only
- Final result: `APPROVED`

## Initial Findings

### P1 Scaffold wrote an extra budget artifact

The initial scaffold used `record_experiment_trial`, which also persisted an `ExperimentBudget`. This violated the PR14 contract: scaffold should only create or return one `PENDING` experiment trial plus optional split/cost protocol artifacts.

Resolution:

- `revision_retest.py` now directly constructs and saves a `PENDING` `ExperimentTrial`.
- Regression test confirms no revision-specific experiment budget is created.

### P2 Idempotent protocol reruns returned non-persisted metadata

Duplicate split/cost protocol runs could return newly constructed objects with a newer `created_at` even when the disk write no-oped because the IDs already existed.

Resolution:

- After `lock_evaluation_protocol`, PR14 reloads the persisted `SplitManifest` and `CostModelSnapshot` by ID.
- Regression test reruns with a later `created_at` and confirms returned metadata matches the persisted rows.

### P2 Revision validation accepted cards without a parent

A revision-like DRAFT card with the revision decision basis and source outcome ID could pass without `parent_card_id`, weakening source outcome alignment.

Resolution:

- `_is_revision_card` now requires a non-empty `parent_card_id`.
- `_source_outcome` always enforces `outcome.strategy_card_id == card.parent_card_id`.
- Regression tests cover missing parent and parent/source mismatch.

## Verification

Commands run after fixes:

```powershell
python -m pytest -q .\tests\test_research_autopilot.py -k "revision_retest"
python -m pytest -q .\tests\test_research_autopilot.py
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Results:

- `8 passed, 17 deselected` for revision retest tests.
- `25 passed` for research autopilot tests.
- `317 passed` for full test suite.
- Compileall passed.
- CLI help lists `create-revision-retest-scaffold`.
- `git diff --check` passed with line-ending warnings only.

## Final Reviewer Decision

`APPROVED`

No blocking findings remain. The reviewer confirmed:

- no experiment budget artifact is created by the scaffold;
- split/cost reruns return persisted rows;
- missing parent and parent/source mismatch are rejected;
- scaffold does not create baseline, backtest, walk-forward, locked evaluation, leaderboard, promotion, or real-capital paths.
