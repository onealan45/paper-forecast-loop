# M4A Research Dataset + Leakage Checks

## Scope

M4A adds a leakage-checked research dataset artifact built from scored
forecasts. It does not add model training, feature engineering beyond existing
forecast artifacts, backtesting, portfolio optimization, broker integration,
sandbox/testnet access, secrets, or live trading.

## Decision

The first research dataset is intentionally conservative:

- input rows come only from forecasts that already have scores;
- feature data is limited to information available at forecast decision time;
- labels come from the target-window outcome recorded by the score;
- the dataset is saved as `research_datasets.jsonl`;
- SQLite migration/export/db-health includes the dataset artifact.

## No-Lookahead Rules

Each dataset row records:

- `decision_timestamp`: the forecast anchor time;
- `feature_timestamp`: the latest timestamp used by features;
- `label_timestamp`: the target-window end from the score.

The leakage checker requires:

- `feature_timestamp <= decision_timestamp`;
- `label_timestamp > decision_timestamp`.

If either rule is violated, `build-research-dataset` exits with an
operator-friendly CLI error and does not save the dataset.

## Command

```powershell
python .\run_forecast_loop.py build-research-dataset --storage-dir <storage> --symbol BTC-USD
```

## Deferred

- richer feature sets;
- train/validation/test splits;
- model training;
- backtesting;
- walk-forward validation;
- research report generation;
- research-based BUY/SELL gates.
