# M3C Deterministic Historical Candles

## Scope

M3C adds a deterministic stored-candle layer for replay. It does not add
ETF/stock providers, calendars, macro data, portfolio optimization, broker
integration, sandbox/testnet access, secrets, or live trading.

## Decision

Replay should no longer depend on moving public API windows. The repo now keeps
stored hourly market candles as auditable artifacts:

- `market_candles.jsonl` in JSONL storage;
- `market_candles` artifact type in SQLite export/migration/db-health;
- `StoredCandleProvider` for replay reads.

`replay-range --provider stored` reads candles from the base storage directory
and writes replay artifacts under `.replay/stored/<symbol>/<range>/`. The base
storage still receives `last_replay_meta.json` and the replay evaluation summary.

`replay-range --provider sample` remains available as a deterministic fixture
path for tests and local examples. `coingecko` remains unavailable for replay
because its market-chart response is a moving public window.

Research seeding may use `fetch-candles` to persist provider candles into
`market_candles.jsonl` with explicit `source` provenance. Those rows can seed
backtests and walk-forward checks, but moving provider snapshots are not treated
as deterministic replay inputs unless they are exported and pinned.

## Commands

```powershell
python .\run_forecast_loop.py import-candles --storage-dir <storage> --input <candles.jsonl> --symbol BTC-USD --source fixture
python .\run_forecast_loop.py fetch-candles --provider coingecko --storage-dir <storage> --symbol BTC-USD --lookback-candles 168 --source coingecko-runtime-seed
python .\run_forecast_loop.py candle-health --storage-dir <storage> --symbol BTC-USD --start 2026-04-21T04:00:00+00:00 --end 2026-04-21T08:00:00+00:00
python .\run_forecast_loop.py replay-range --provider stored --storage-dir <storage> --symbol BTC-USD --start 2026-04-21T04:00:00+00:00 --end 2026-04-21T08:00:00+00:00 --horizon-hours 2
python .\run_forecast_loop.py export-candles --storage-dir <storage> --symbol BTC-USD --output <export.jsonl>
```

## Candle Health

`candle-health` checks:

- storage directory exists;
- `market_candles.jsonl` exists;
- each candle row parses;
- duplicate timestamps for the requested symbol;
- missing hourly timestamps in the requested inclusive range.

Blocking findings return exit code `2`. Healthy coverage returns exit code `0`.

## Artifact Shape

Each stored candle row records:

- `candle_id`;
- `symbol`;
- `timestamp`;
- `open`, `high`, `low`, `close`, `volume`;
- `source`;
- `imported_at`.

The id is stable across symbol, timestamp, and source. Duplicate imports of the
same source are idempotent, while `candle-health` can still detect duplicate
timestamps across different sources.

## Deferred

- provider-specific historical importers;
- adjusted close and market calendar rules for ETFs/stocks;
- candle table specialization beyond the generic SQLite artifact table;
- multi-asset replay orchestration.
