# M3D ETF/Stock Data Prototype

## Scope

M3D adds a fixture-first US ETF/stock data path. It does not add paid providers,
live market data, broker integration, sandbox/testnet, secrets, macro events,
multi-asset decisions, or live trading.

Supported symbols in this prototype:

- `SPY`
- `QQQ`
- `TLT`
- `GLD`

`0050.TW` remains inactive until a Taiwan market calendar and provider path are
implemented.

## Decision

ETF/stock data should enter the repo through deterministic fixture files first,
not through an unstable or paid API. M3D therefore adds:

- US market calendar helper with `America/New_York` close converted to UTC;
- 2026 static US market holiday set for fixture validation;
- `import-stock-csv`;
- `stock-candle-health`;
- `market-calendar`;
- `StockCsvFixtureProvider`;
- `adjusted_close` on `MarketCandleRecord`.

The fixture importer stores daily sessions as `market_candles.jsonl` rows at
the US equity close boundary. `MarketCandleRecord.to_candle()` uses
`adjusted_close` when it is present, so model/replay consumers see adjusted
close behavior without changing the base `MarketCandle` type.

## CSV Contract

Required columns:

- `date`
- `open`
- `high`
- `low`
- `close`
- `adjusted_close`
- `volume`

Rows on weekends or configured US market holidays are skipped and counted as
`skipped_non_trading_day_count`.

## Commands

```powershell
python .\run_forecast_loop.py market-calendar --market US --start-date 2026-04-02 --end-date 2026-04-06
python .\run_forecast_loop.py import-stock-csv --storage-dir <storage> --input <spy.csv> --symbol SPY --source fixture
python .\run_forecast_loop.py stock-candle-health --storage-dir <storage> --symbol SPY --start-date 2026-04-02 --end-date 2026-04-06
```

## Health Rules

`stock-candle-health` checks:

- storage directory exists;
- `market_candles.jsonl` exists;
- stock candle rows parse;
- rows for the symbol include `adjusted_close`;
- duplicate session close timestamps;
- missing expected US trading sessions.

Weekends and configured US market holidays are not expected sessions.

## Deferred

- live stock/ETF provider;
- paid data integration;
- corporate-action provider;
- full exchange calendars beyond the static 2026 prototype set;
- Taiwan ETF calendar/provider;
- multi-asset decision generation.
