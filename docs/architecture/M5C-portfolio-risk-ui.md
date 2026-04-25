# M5C Portfolio / Risk UI

## Decision

M5C expands the local operator console `portfolio` page into a read-only paper
portfolio and risk inspection surface.

The page exposes:

- NAV;
- cash;
- realized PnL;
- unrealized PnL;
- current drawdown;
- portfolio max drawdown;
- recommended risk action;
- gross exposure;
- net exposure;
- per-symbol position exposure;
- risk gate current values and limits;
- risk findings;
- position quantity, average price, market price, market value, position %, and
  unrealized PnL.

## Implementation

- Module: `src/forecast_loop/operator_console.py`
- Page: `/portfolio`
- Data sources:
  - latest `PaperPortfolioSnapshot`
  - latest `RiskSnapshot` for the selected symbol

No new storage schema is introduced.

## Safety Boundary

M5C remains read-only.

It does not:

- create portfolio snapshots;
- evaluate new risk snapshots;
- create orders;
- fill orders;
- add controls;
- call brokers or exchanges;
- read secrets;
- execute live trading.

## Deferred

- Historical equity curve charting is deferred.
- Position drilldown is deferred.
- Control-plane behavior remains M5E.
- Broker/external reconciliation remains M6.
