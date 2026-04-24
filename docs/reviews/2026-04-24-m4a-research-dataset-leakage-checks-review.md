# M4A Research Dataset + Leakage Checks Review

## Scope

- Stage: M4A Research Dataset + Leakage Checks
- Branch: `codex/m4a-research-dataset-leakage`
- Boundary: research dataset artifact, no-lookahead leakage checker,
  `build-research-dataset` CLI, JSONL/SQLite parity, health-check links,
  docs/tests only; no model training, no backtest, no optimizer, no broker
  submit, no sandbox/testnet, no live trading, no secrets.

## Implementation Summary

- Added `ResearchDataset` and `ResearchDatasetRow`.
- Added `research_datasets.jsonl` support to JSONL storage.
- Added SQLite migration/export/db-health parity for research datasets.
- Added `build-research-dataset` CLI command.
- Dataset rows are built only from forecasts that have scores.
- Dataset features use immutable forecast-decision-time fields only.
- `provider_data_through` is excluded from features because the forecast field
  is mutated during scoring to reflect realized target-window coverage.
- Leakage checker enforces:
  - `feature_timestamp <= decision_timestamp`;
  - `label_timestamp > decision_timestamp`.
- CLI fails closed with argparse-style errors when storage is missing, no scored
  forecasts exist, or leakage is detected.
- Health-check validates dataset links to forecast and score artifacts, and
  flags stored datasets with failed or invalid leakage status.
- Updated README, PRD, and architecture docs.

## Test Evidence

```powershell
python -m pytest tests/test_research_dataset.py tests/test_sqlite_repository.py -q
```

Result: `14 passed`.

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
```

Result: passed.

```powershell
python -m pytest -q
```

Result: `148 passed`.

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Result: passed.

## Smoke Evidence

```powershell
python .\run_forecast_loop.py build-research-dataset --storage-dir .\paper_storage\manual-m4a-check-20260424T2035Z --symbol BTC-USD --created-at 2026-04-24T20:35:00+00:00
python .\run_forecast_loop.py health-check --storage-dir .\paper_storage\manual-m4a-check-20260424T2035Z --symbol BTC-USD --now 2026-04-22T00:00:00+00:00
python .\run_forecast_loop.py migrate-jsonl-to-sqlite --storage-dir .\paper_storage\manual-m4a-check-20260424T2035Z
python .\run_forecast_loop.py db-health --storage-dir .\paper_storage\manual-m4a-check-20260424T2035Z
python .\run_forecast_loop.py export-jsonl --storage-dir .\paper_storage\manual-m4a-check-20260424T2035Z --output-dir .\paper_storage\manual-m4a-export-20260424T2035Z
```

Result:

- `build-research-dataset` wrote one dataset with three rows.
- Leakage status was `passed`.
- Health-check returned `degraded` with only `dashboard_missing` warning.
- SQLite migration, db-health, and export all reported `research_datasets: 1`.
- Manual smoke storage/export paths are ignored by `.gitignore`.

## Known Deferrals

- richer feature sets;
- train/validation/test splits;
- model training;
- backtesting;
- walk-forward validation;
- research report generation;
- research-based BUY/SELL gates.

## Final Reviewer

- Reviewer subagent: Darwin (`019dc10f-15f0-7851-8c6d-f5ba4aca751a`)
- First pass: blocked on using scoring-time `forecast.provider_data_through`
  as a dataset feature timestamp.
- Remediation: feature timestamp now uses immutable `forecast.anchor_time`,
  mutable `provider_data_through` is excluded from features, and regression
  coverage verifies resolved/scored forecasts can be converted without
  lookahead.
- Re-review: approved.
- Status: approved; no blocking findings remain.

Residual non-blocking risks:

- dataset features are intentionally minimal forecast-artifact fields;
- no train/validation/test split exists yet;
- no model training, backtesting, or research-based decision gate exists yet.
