# Paper Forecast Loop

Paper-only public-data forecasting and strategy-research loop for BTC-USD.

## What It Does

- ingests public market data from CoinGecko
- creates immutable forecast artifacts
- resolves matured forecasts into scores
- writes review artifacts and defensive strategy proposals
- stays paper-only with no live trading or automatic promotion

## Project Layout

- `src/forecast_loop/`: forecasting loop, providers, storage, models, CLI
- `tests/`: pipeline and provider tests
- `run_forecast_loop.py`: repo-root entrypoint for local runs

## Local Commands

Run tests:

```powershell
pytest -q
```

Run one sample cycle:

```powershell
python run_forecast_loop.py run-once --provider sample --symbol BTC-USD --storage-dir .\paper_storage\manual-sample
```

Run one public-data cycle:

```powershell
python run_forecast_loop.py run-once --provider coingecko --symbol BTC-USD --storage-dir .\paper_storage\manual-coingecko
```

## Current Scope

- single symbol: `BTC-USD`
- public data provider: CoinGecko
- paper-only artifacts: forecasts, scores, reviews, proposals

## Review Focus

The current implementation is intentionally small. Good review targets are:

- forecast horizon alignment versus provider candle timestamps
- resolution safety when market data has not fully covered the forecast window
- proposal and review thresholds for paper-only adjustment logic
