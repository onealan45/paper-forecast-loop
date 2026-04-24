# M4D Walk-Forward Validation

## Scope

M4D adds a local paper-only walk-forward validation artifact over stored
candles. It does not add model training, portfolio optimization, research-based
decision gates, broker integration, sandbox/testnet access, secrets, or live
trading.

## Decision

The walk-forward engine uses `market_candles.jsonl` as its market data source
and reuses the M4C paper-only backtest engine for validation and test segments.
It writes:

- `backtest_runs.jsonl`;
- `backtest_results.jsonl`;
- `walk_forward_validations.jsonl`.

Each rolling window records non-overlapping boundaries:

- train start/end;
- validation start/end;
- test start/end.

The current strategy is still the fixed moving-average trend rule from M4C.
The train segment is recorded as boundary context only; M4D does not tune
parameters or train a model.

## Metrics

Each walk-forward artifact records:

- window count;
- average validation return;
- average test return;
- average buy-and-hold benchmark return;
- average excess return;
- test win rate;
- overfit window count;
- aggregate overfit-risk flags;
- linked validation/test backtest result ids.

Window-level overfit flags include validation/test decay and test
underperformance versus benchmark. These are research warnings only in M4D.

## Command

```powershell
python .\run_forecast_loop.py walk-forward --storage-dir .\paper_storage\manual-replay --symbol BTC-USD --start 2026-04-01T00:00:00+00:00 --end 2026-04-30T00:00:00+00:00 --train-size 8 --validation-size 4 --test-size 4 --step-size 2
```

## Safety

- Stored candles must be unique and strictly increasing by timestamp for the
  selected symbol.
- Validation and test backtests remain local paper simulations.
- No broker, exchange, secret, sandbox, testnet, or live execution path is
  introduced.

## Deferred

- model training on the train segment;
- parameter optimization;
- research report generation;
- using walk-forward stability to gate BUY/SELL;
- multi-asset portfolio optimization.
