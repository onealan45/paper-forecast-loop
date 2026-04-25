# M4F Research Decision Gates

## Scope

M4F makes research quality influence paper-only strategy decisions. It does not
add live trading, broker integration, sandbox/testnet behavior, secrets,
automatic strategy promotion, or real order execution.

## Decision

BUY/SELL now require the existing baseline gate and an additional research gate.
The research gate checks:

- minimum scored forecast sample size;
- positive model edge over baseline;
- latest backtest beats benchmark;
- latest backtest drawdown is acceptable;
- latest walk-forward average excess return is positive;
- latest walk-forward test return beats its benchmark;
- no walk-forward overfit-risk flags are present.

If the research gate fails:

- missing or weak research evidence blocks BUY/SELL and emits `HOLD`;
- overfit risk, high drawdown, or recent degradation emits `REDUCE_RISK`;
- health and risk STOP gates still take priority when already blocking.

## Rationale

M4E made research evidence visible. M4F makes it operationally meaningful while
remaining paper-only and fail-closed.

## Deferred

- configurable thresholds by asset;
- per-strategy research gate profiles;
- using research reports as canonical inputs;
- portfolio optimizer integration.
