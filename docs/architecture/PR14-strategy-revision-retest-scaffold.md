# PR14 Strategy Revision Retest Scaffold

## Purpose

PR12 can turn a failed simulated paper-shadow outcome into a DRAFT child strategy card. PR13 makes that DRAFT revision visible in the dashboard and operator console. PR14 adds the next controlled step: a retest scaffold that starts a new research trial without pretending the revision has already passed.

## New Capability

`create-revision-retest-scaffold` creates or returns one `PENDING` `ExperimentTrial` for a DRAFT revision card.

The trial links back to:

- `revision_retest_source_card_id`
- `revision_source_outcome_id`
- `revision_parent_card_id`
- `revision_retest_protocol = pr14-v1`

When the caller provides a complete train / validation / holdout window, the command also locks a `SplitManifest` and `CostModelSnapshot` through the existing `lock_evaluation_protocol` path.

## Deliberate Non-Goals

PR14 does not create:

- `BaselineEvaluation`
- `BacktestResult`
- `WalkForwardValidation`
- `LockedEvaluationResult`
- `LeaderboardEntry`
- new `PaperShadowOutcome`
- promotion from `DRAFT` to `ACTIVE`

Those artifacts still require real research evidence. The scaffold only gives the next research worker a traceable starting point.

## Why This Shape

The project direction is research-first and self-evolving, but the evaluation path must stay fixed after a hypothesis is generated. A DRAFT strategy mutation can be broad; its retest must be explicit, repeatable, and unable to create an alpha score until baseline, backtest, walk-forward, and locked evaluation artifacts exist.

## CLI

```powershell
python run_forecast_loop.py create-revision-retest-scaffold --storage-dir .\paper_storage\manual-research --revision-card-id strategy-card:revision --symbol BTC-USD --dataset-id research-dataset:revision-retest --max-trials 20 --created-at 2026-04-28T14:00:00+00:00
```

Optional protocol locking:

```powershell
python run_forecast_loop.py create-revision-retest-scaffold --storage-dir .\paper_storage\manual-research --revision-card-id strategy-card:revision --symbol BTC-USD --dataset-id research-dataset:revision-retest --train-start 2026-01-01T00:00:00+00:00 --train-end 2026-02-01T00:00:00+00:00 --validation-start 2026-02-02T00:00:00+00:00 --validation-end 2026-03-01T00:00:00+00:00 --holdout-start 2026-03-02T00:00:00+00:00 --holdout-end 2026-04-01T00:00:00+00:00
```

## Acceptance

- Re-running the command for the same DRAFT revision and source outcome returns the existing pending trial.
- Non-revision strategy cards are rejected.
- Split/cost protocol artifacts are optional and require a complete window.
- No locked evaluation result is created by this scaffold.
