# M4C Backtest Engine

## Scope

M4C adds a local paper-only backtest engine over stored candle artifacts. It
does not add model training, walk-forward validation, portfolio optimization,
broker integration, sandbox/testnet access, secrets, or live trading.

## Decision

The first backtest engine uses `market_candles.jsonl` as its only market data
source. It writes:

- `backtest_runs.jsonl`;
- `backtest_results.jsonl`.

The default strategy is a fixed moving-average trend rule:

- target 100% long when the previous candle close is at or above its prior
  moving average;
- otherwise target cash.

This is intentionally simple. The goal of M4C is the backtest machinery and
metrics, not strategy sophistication.

The signal uses only candles that are earlier than the simulated execution
candle. The engine does not use the current execution candle to both decide and
fill the trade.

## Metrics

Each result records:

- strategy return;
- buy-and-hold benchmark return;
- max drawdown;
- Sharpe;
- turnover;
- win rate;
- trade count;
- final equity;
- an equity curve.

Fees and slippage are configurable and applied to local simulated fills only.

## Command

```powershell
python .\run_forecast_loop.py backtest --storage-dir .\paper_storage\manual-replay --symbol BTC-USD --start 2026-04-01T00:00:00+00:00 --end 2026-04-30T00:00:00+00:00
```

## Deferred

- forecast/decision-driven strategy replay;
- multi-asset backtests;
- train/validation/test splits;
- walk-forward validation;
- research report generation;
- broker or sandbox reconciliation.
