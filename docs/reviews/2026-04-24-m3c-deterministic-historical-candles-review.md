# M3C Deterministic Historical Candles Review

## Scope

- Stage: M3C Deterministic Historical Candles
- Branch: `codex/m3c-deterministic-historical-candles`
- Boundary: stored candle artifacts, candle import/export, candle health, and
  stored-candle replay only; no ETF/stock provider, no macro data, no broker
  submit, no sandbox/testnet, no live trading, no secrets.

## Implementation Summary

- Added `MarketCandleRecord`.
- Added `market_candles.jsonl` support to JSONL repository.
- Added SQLite migration/export/db-health parity for market candles.
- Added `StoredCandleProvider`.
- Added CLI:
  - `import-candles`
  - `export-candles`
  - `candle-health`
- Added `replay-range --provider stored`.
- Kept `replay-range --provider sample` as deterministic fixture support.
- Kept CoinGecko replay disabled.
- Updated README, PRD, and architecture docs.
- Final-review blocker remediation:
  - stored candles must be hour-aligned;
  - OHLCV values must be finite;
  - `high` must be at least `open`, `close`, and `low`;
  - `low` must be at most `open`, `close`, and `high`;
  - volume must be non-negative;
  - `candle-health --interval-minutes` must be `60` and greater than zero.

## Test Evidence

```powershell
python -m pytest tests/test_candle_store.py tests/test_sqlite_repository.py tests/test_replay.py -q
```

Result: `40 passed`.

```powershell
python -m pytest -q
```

Result: `122 passed`.

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Result: passed.

## Smoke Evidence

```powershell
python .\run_forecast_loop.py import-candles --storage-dir .\paper_storage\manual-m3c-check-20260424T1830Z --input .\paper_storage\manual-m3c-candles-20260424T1830Z.jsonl --symbol BTC-USD --source fixture --imported-at 2026-04-24T18:30:00+00:00
python .\run_forecast_loop.py candle-health --storage-dir .\paper_storage\manual-m3c-check-20260424T1830Z --symbol BTC-USD --start 2026-04-21T00:00:00+00:00 --end 2026-04-21T10:00:00+00:00
python .\run_forecast_loop.py replay-range --provider stored --symbol BTC-USD --storage-dir .\paper_storage\manual-m3c-check-20260424T1830Z --start 2026-04-21T04:00:00+00:00 --end 2026-04-21T08:00:00+00:00 --horizon-hours 2
python .\run_forecast_loop.py render-dashboard --storage-dir .\paper_storage\manual-m3c-check-20260424T1830Z
python .\run_forecast_loop.py migrate-jsonl-to-sqlite --storage-dir .\paper_storage\manual-m3c-check-20260424T1830Z
python .\run_forecast_loop.py db-health --storage-dir .\paper_storage\manual-m3c-check-20260424T1830Z
python .\run_forecast_loop.py export-jsonl --storage-dir .\paper_storage\manual-m3c-check-20260424T1830Z --output-dir .\paper_storage\manual-m3c-export-20260424T1830Z
```

Result:

- `import-candles` imported 11 rows.
- `candle-health` returned `healthy`, `missing_count: 0`, `duplicate_count: 0`.
- `replay-range --provider stored` ran 5 cycles and created 3 scores.
- `last_replay_meta.json` recorded `provider: stored`.
- SQLite migration/export reported `market_candles: 11`.
- `db-health` returned `healthy`.
- Manual smoke storage/input/export paths are ignored by `.gitignore`.

## Known Deferrals

- provider-specific historical importers;
- CSV import;
- ETF/stock market calendars and adjusted closes;
- typed SQLite candle table specialization;
- multi-asset replay orchestration.

## Final Reviewer

- Reviewer subagent: Archimedes (`019dc0d6-6eab-7d43-9e27-0aa29cd18eca`)
- First pass: `BLOCKED` on non-hour-aligned candle acceptance, invalid OHLCV
  acceptance, and invalid interval hang risk.
- Remediation: implemented and verified with the updated test evidence above.
- Re-review: `APPROVED`
- Status: approved; no blocking findings remain.
