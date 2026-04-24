# M4B Baseline Expansion

## Scope

M4B expands baseline evidence recorded in `baseline_evaluations.jsonl`. It does
not add model training, backtesting, walk-forward validation, portfolio
optimization, broker integration, sandbox/testnet access, secrets, or live
trading.

## Decision

The existing `BaselineEvaluation` artifact remains the compatibility surface
for M1 decision gates. `baseline_accuracy` and `model_edge` still refer to the
naive persistence baseline so the current BUY/SELL gate does not change in this
stage.

M4B adds `baseline_results` to record a research-audit suite:

- `naive_persistence`;
- `no_trade_cash`;
- `buy_and_hold`;
- `moving_average_trend`;
- `momentum_7d`;
- `momentum_14d`;
- `deterministic_random`.

Each baseline result records:

- baseline name;
- accuracy when a directional prediction exists;
- evaluated count;
- hit count;
- sample size;
- decision basis.

`no_trade_cash` intentionally records no directional prediction and therefore
has no directional accuracy.

## Deferred

- choosing the strongest baseline for BUY/SELL gating;
- return-based baseline metrics;
- backtest integration;
- walk-forward stability checks;
- research-based decision gates.
