# M3D ETF/Stock Data Prototype Review

## Scope

- Stage: M3D ETF/Stock Data Prototype
- Branch: `codex/m3d-etf-stock-data-prototype`
- Boundary: US ETF/stock CSV fixtures, market calendar, adjusted close, and
  fixture health only; no live stock API, no paid provider, no macro data, no
  broker submit, no sandbox/testnet, no live trading, no secrets.

## Implementation Summary

- Added optional `adjusted_close` to `MarketCandleRecord`.
- `MarketCandleRecord.to_candle()` uses `adjusted_close` when present.
- Added US market calendar helper:
  - `America/New_York` close converted to UTC;
  - weekend filtering;
  - static 2026 US equity holiday set.
- Added `StockCsvFixtureProvider`.
- Added CLI:
  - `market-calendar`
  - `import-stock-csv`
  - `stock-candle-health`
- US ETF fixture symbols: `SPY`, `QQQ`, `TLT`, `GLD`.
- `0050.TW` remains inactive/deferred.
- Updated README, PRD, asset registry, and architecture docs.

## Test Evidence

```powershell
python -m pytest tests/test_stock_data.py tests/test_assets.py tests/test_candle_store.py tests/test_sqlite_repository.py -q
```

Result: `26 passed`.

```powershell
python -m pytest -q
```

Result: `129 passed`.

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Result: passed.

## Smoke Evidence

```powershell
python .\run_forecast_loop.py market-calendar --market US --start-date 2026-04-02 --end-date 2026-04-06
python .\run_forecast_loop.py import-stock-csv --storage-dir .\paper_storage\manual-m3d-check-20260424T1915Z --input .\paper_storage\manual-m3d-spy-20260424T1915Z.csv --symbol SPY --source fixture --imported-at 2026-04-24T19:15:00+00:00
python .\run_forecast_loop.py stock-candle-health --storage-dir .\paper_storage\manual-m3d-check-20260424T1915Z --symbol SPY --start-date 2026-04-02 --end-date 2026-04-06
python .\run_forecast_loop.py migrate-jsonl-to-sqlite --storage-dir .\paper_storage\manual-m3d-check-20260424T1915Z
python .\run_forecast_loop.py db-health --storage-dir .\paper_storage\manual-m3d-check-20260424T1915Z
python .\run_forecast_loop.py export-jsonl --storage-dir .\paper_storage\manual-m3d-check-20260424T1915Z --output-dir .\paper_storage\manual-m3d-export-20260424T1915Z
```

Result:

- `market-calendar` returned two sessions for 2026-04-02 and 2026-04-06,
  skipping Good Friday and weekend dates.
- `import-stock-csv` imported two SPY rows and skipped one non-trading day.
- `stock-candle-health` returned `healthy`.
- SQLite migration/export reported `market_candles: 2`.
- `market_candles.jsonl` stored `adjusted_close` values.
- Manual smoke storage/input/export paths are ignored by `.gitignore`.

## Known Deferrals

- live stock or ETF provider;
- paid provider integration;
- full exchange calendar beyond the static 2026 prototype;
- corporate-action provider;
- Taiwan ETF provider/calendar;
- multi-asset decisions.

## Final Reviewer

- Reviewer subagent: Hypatia (`019dc0e5-aaf6-7730-b47b-b49ad5fc5f5d`)
- Re-review needed: no
- Status: approved; no blocking findings.

Residual non-blocking risks:

- US calendar is a static 2026 prototype with regular 16:00 ET closes only.
- `stock-candle-health` does not flag extra off-calendar rows yet.
- `csv-fixture` is not a `run-once` provider yet.
- Daily stock fixture flow is not wired into audited forecasting/replay yet.
