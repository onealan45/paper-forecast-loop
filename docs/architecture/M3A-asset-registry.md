# M3A Asset Registry Architecture

## Goal

M3A adds a small canonical asset registry for the next multi-asset stages.

This stage does not add ETF/stock providers, macro data, portfolio
optimization, `decide-all`, broker integration, sandbox/testnet execution, or
live trading.

## Registry

The registry is static code in `src/forecast_loop/assets.py`.

Required M3A assets:

- `BTC-USD`
- `ETH-USD`
- `SPY`
- `QQQ`
- `TLT`
- `GLD`
- `0050.TW`

Each asset records:

- symbol
- display name
- asset class
- market
- quote currency
- timezone
- status
- default provider
- data status
- notes

## Status Semantics

- `active`: public-data path exists in current code, but automation and strategy
  research remain conservative and paper-only.
- `planned`: asset is registered for future stages, but provider/calendar logic
  is not implemented yet.
- `inactive`: asset is visible in the roadmap but must not be used by current
  forecast or decision automation.

`BTC-USD` and `ETH-USD` are active because current CoinGecko mapping exists.
US ETFs are planned until M3D adds ETF/stock data handling. `0050.TW` is
inactive until Taiwan market calendar and provider support exist.

## CLI

```powershell
python .\run_forecast_loop.py list-assets
python .\run_forecast_loop.py list-assets --status planned --format text
```

The JSON output is intended for future automation and dashboards. The text
output is a compact operator view.

## Deferred

- provider audit runs;
- deterministic historical candle storage;
- ETF/stock CSV or public provider prototype;
- macro event model;
- per-symbol multi-asset decisions.
