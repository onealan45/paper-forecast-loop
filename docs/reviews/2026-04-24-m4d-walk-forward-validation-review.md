# M4D Walk-Forward Validation Review

## Scope

Milestone: M4D Walk-Forward Validation.

This review archive covers the paper-only walk-forward validation artifact
added after M4C. It does not cover walk-forward-driven decision gates,
portfolio optimization, live broker integration, sandbox/testnet brokers, or
real execution.

## Implementation Summary

- Added `WalkForwardWindow` and `WalkForwardValidation` artifacts.
- Added JSONL and SQLite repository support for
  `walk_forward_validations.jsonl`.
- Added `python .\run_forecast_loop.py walk-forward`.
- Added rolling train / validation / test windows over stored candles.
- Reused the paper-only M4C backtest engine for validation and test windows.
- Added aggregate validation/test/benchmark/excess metrics, test win rate, and
  overfit-risk flags.
- Added health-check integrity checks for walk-forward links to backtest
  results.
- Kept the engine local and paper-only; no broker, exchange, secret, sandbox,
  testnet, or live trading path was added.

## Verification

- `python -m pytest -q`
  - Result: `162 passed in 5.49s`
- `python -m pytest tests/test_walk_forward.py tests/test_sqlite_repository.py -q`
  - Result: `10 passed in 1.89s`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Result: passed
- `python .\run_forecast_loop.py --help`
  - Result: passed; `walk-forward` appears in the command list
- `git diff --check`
  - Result: passed; only CRLF normalization warnings were printed

## Smoke Evidence

Storage: `paper_storage\manual-m4d-check-20260424` (ignored by git).

- Seeded 12 BTC-USD fixture candles.
- Ran `python .\run_forecast_loop.py walk-forward --storage-dir .\paper_storage\manual-m4d-check-20260424 --symbol BTC-USD --start 2026-04-01T00:00:00+00:00 --end 2026-04-12T00:00:00+00:00 --created-at 2026-04-24T22:15:00+00:00 --train-size 3 --validation-size 3 --test-size 3 --step-size 2 --moving-average-window 2`.
- Result summary:
  - `window_count=2`
  - `average_validation_return=-0.0007491259365321468`
  - `average_test_return=-0.0007491259365321468`
  - `average_benchmark_return=0.023634775010921816`
  - `average_excess_return=-0.024383900947453963`
  - `overfit_risk_flags=["aggregate_underperforms_benchmark", "majority_windows_flagged", "test_underperforms_benchmark"]`
- Ran `migrate-jsonl-to-sqlite`; inserted `market_candles=12`,
  `backtest_runs=4`, `backtest_results=4`, and
  `walk_forward_validations=1`.
- Ran `db-health`; result was `healthy`, `repair_required=false`,
  `walk_forward_validations=1`.
- Ran `export-jsonl`; exported `market_candles=12`, `backtest_runs=4`,
  `backtest_results=4`, and `walk_forward_validations=1`.
- Ran `git check-ignore -v` for smoke storage and export directories; both are
  ignored by `paper_storage/`.

Execution lesson: `migrate-jsonl-to-sqlite`, `db-health`, and `export-jsonl`
must be run sequentially when a new SQLite DB is being created. Running them in
parallel can produce transient stale/missing DB observations unrelated to code
correctness.

Final reviewer approval is pending before merge.

## Reviewer Status

Final reviewer subagent result: `APPROVED`.

Reviewer notes:

- No blocking findings.
- M4D remains paper-only.
- No broker/exchange, secrets, sandbox/testnet, live trading, or BUY/SELL gate
  changes were introduced.
- Rolling train/validation/test boundaries, duplicate timestamp rejection,
  aggregate metrics, overfit flags, artifact traceability, health links,
  SQLite/JSONL parity, CLI, and docs were in scope and accepted.

Reviewer-rerun verification:

- `python -m pytest -q`
  - Result: `162 passed in 5.48s`
- focused tests
  - Result: `10 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Result: passed
- `python .\run_forecast_loop.py --help`
  - Result: passed; `walk-forward` visible
- `git diff --check`
  - Result: passed with CRLF warnings only

## Automation Status

Hourly paper automation must remain paper-only. This milestone does not resume,
promote, or alter live execution because no live execution exists.
