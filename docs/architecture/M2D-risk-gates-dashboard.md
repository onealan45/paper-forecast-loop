# M2D Risk Gates + Portfolio Dashboard Architecture

## Goal

M2D makes paper portfolio risk visible and lets risk state influence strategy
decisions.

This remains internal paper research only. It does not add broker submit,
exchange access, sandbox/testnet adapters, live trading, or secrets.

## Models

M2D adds `RiskSnapshot`.

Each risk snapshot records:

- symbol
- status: `OK`, `REDUCE_RISK`, or `STOP_NEW_ENTRIES`
- severity: `none`, `warning`, or `blocking`
- current and max drawdown
- gross and net exposure
- per-symbol position percentage
- configured drawdown and exposure thresholds
- findings and decision basis

## CLI

```powershell
python .\run_forecast_loop.py risk-check --storage-dir <path> --symbol BTC-USD
```

Optional gate knobs:

```powershell
--max-position-pct 0.15
--max-gross-exposure-pct 0.20
--reduce-risk-drawdown-pct 0.05
--stop-new-entries-drawdown-pct 0.10
```

`risk-check` returns exit code `2` when the risk snapshot severity is
`blocking`.

## Gate Rules

- current drawdown >= stop-new-entries threshold -> `STOP_NEW_ENTRIES`
- current drawdown >= reduce-risk threshold -> `REDUCE_RISK`
- gross exposure > max gross exposure -> `REDUCE_RISK`
- symbol position > max position -> `REDUCE_RISK`

Decision generation now consumes the latest risk snapshot or a freshly computed
one from CLI paths:

- `STOP_NEW_ENTRIES` risk overrides directional BUY/SELL.
- `REDUCE_RISK` risk overrides BUY and recommends reducing current paper
  position by half.
- If there is no position to reduce, the decision is not tradeable and explains
  that the risk gate cannot generate a local reduction order.

## Dashboard

The static dashboard now includes a portfolio/risk section with:

- NAV / equity
- cash
- realized and unrealized PnL
- risk status
- gross and net exposure
- drawdown thresholds

## Repository Compatibility

`risk_snapshots.jsonl` is supported by:

- JSONL repository
- SQLite migration/export
- `db-health`
- `health-check` bad-row and duplicate-id detection

## Deferred

- operator control gates
- portfolio optimizer
- multi-asset risk aggregation
- external broker or sandbox reconciliation
- typed relational risk tables
