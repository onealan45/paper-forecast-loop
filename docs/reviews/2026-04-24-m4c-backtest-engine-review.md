# M4C Backtest Engine Review

## Scope

Milestone: M4C Backtest Engine.

This review archive covers the paper-only backtest engine added after M4B. It
does not cover walk-forward validation, portfolio optimization, live broker
integration, sandbox/testnet brokers, or real execution.

## Implementation Summary

- Added `BacktestRun` and `BacktestResult` artifacts.
- Added JSONL and SQLite repository support for `backtest_runs` and
  `backtest_results`.
- Added `python .\run_forecast_loop.py backtest`.
- Added a fixed paper-only moving-average trend simulator with configurable
  initial cash, fee bps, slippage bps, and moving-average window.
- Added metrics for strategy return, buy-and-hold benchmark return, max
  drawdown, Sharpe, turnover, win rate, trade count, final equity, and an
  equity curve.
- Added health-check integrity checks for backtest result-to-run links and
  backtest run-to-candle links.
- Kept the simulator local and paper-only; no broker, exchange, secret, or live
  trading path was added.

## Verification

- `python -m pytest -q`
  - Result: `156 passed in 7.10s`
- `python -m pytest tests/test_backtest.py tests/test_sqlite_repository.py -q`
  - Result: `11 passed in 2.36s`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Result: passed
- `python .\run_forecast_loop.py --help`
  - Result: passed; `backtest` appears in the command list
- `git diff --check`
  - Result: passed; only CRLF normalization warnings were printed

## Smoke Evidence

Storage: `paper_storage\manual-m4c-check-20260424b` (ignored by git).

- Seeded 6 BTC-USD fixture candles.
- Ran `python .\run_forecast_loop.py backtest --storage-dir .\paper_storage\manual-m4c-check-20260424b --symbol BTC-USD --start 2026-04-01T00:00:00+00:00 --end 2026-04-06T00:00:00+00:00 --created-at 2026-04-24T21:15:00+00:00 --initial-cash 10000 --fee-bps 5 --slippage-bps 10 --moving-average-window 2`.
- Result summary:
  - `trade_count=3`
  - `final_equity=9859.385123375148`
  - `benchmark_return=0.06000000000000005`
  - `max_drawdown=0.030301186915187465`
  - `turnover=2.974336569734697`
- Ran `migrate-jsonl-to-sqlite`; inserted `backtest_runs=1` and
  `backtest_results=1`.
- Ran `db-health`; result was `healthy`, `repair_required=false`,
  `backtest_runs=1`, `backtest_results=1`.
- Ran `export-jsonl`; exported `backtest_runs=1` and `backtest_results=1`.
- Ran `git check-ignore -v` for both smoke storage and export directory; both
  are ignored by `paper_storage/`.

Full gate passed locally before final reviewer handoff. It should be rerun once
more after any reviewer-driven changes and before commit.

## Reviewer Status

First final reviewer pass returned blocking findings:

- P1: `moving_average_window` was not recorded in `BacktestRun` or
  `backtest_id`.
- P1: duplicate same-symbol candle timestamps could allow same-time signal/fill
  behavior.
- P2: architecture doc command used a raw `<storage>` placeholder.

Fixes applied:

- Added `moving_average_window` to `BacktestRun`, artifact serialization, and
  stable ID generation.
- Added strict increasing timestamp validation for selected backtest candles.
- Replaced the raw doc placeholder with an executable PowerShell path.
- Added regression tests for window identity and duplicate timestamp rejection.

Post-fix targeted verification:

- `python -m pytest tests/test_backtest.py tests/test_sqlite_repository.py -q`
  - Result: `13 passed in 2.45s`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Result: passed

Second final reviewer pass is pending.

Second final reviewer pass result: `APPROVED`.

Reviewer note:

- Previous blockers are closed.
- No new blocking findings found.
- Reviewer did not modify files.
- Reviewer extra smoke: `python -m pytest tests/test_backtest.py -q` returned
  `7 passed in 0.33s`.

## Automation Status

Hourly paper automation must remain paper-only. This milestone does not resume,
promote, or alter live execution because no live execution exists.
