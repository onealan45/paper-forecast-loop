# M2C Paper Fills / Positions / NAV Architecture

## Goal

M2C turns local paper orders into local paper fills and portfolio accounting
artifacts.

This is still not broker, exchange, sandbox, testnet, or live execution.

## Models

M2C adds:

- `PaperFill`
- `EquityCurvePoint`

It also extends `PaperPortfolioSnapshot` with:

- `realized_pnl`
- `unrealized_pnl`
- `nav`

`PaperPosition` remains the per-symbol position view and now feeds NAV /
exposure calculations.

## CLI

```powershell
python .\run_forecast_loop.py paper-fill --storage-dir <path> --order-id latest
python .\run_forecast_loop.py portfolio-snapshot --storage-dir <path>
```

Optional pricing knobs:

```powershell
--market-price 100
--fee-bps 5
--slippage-bps 10
```

When no provider price artifact exists, M2C uses the explicit or default
synthetic paper mark price. This keeps the command deterministic and avoids
accidentally adding an external execution or quote dependency.

## Accounting Rules

- `BUY` fills use `market_price * (1 + slippage_bps / 10000)`.
- `SELL` fills use `market_price * (1 - slippage_bps / 10000)`.
- Fees are charged on gross filled value.
- `TARGET_PERCENT` orders fill only the difference between current market value
  and target paper allocation.
- Filled orders are marked `FILLED` so they no longer block as active orders.
- Portfolio snapshots update cash, quantity, average price, market value,
  realized PnL, unrealized PnL, equity/NAV, and exposure.

## Safety Boundary

M2C writes local artifacts only:

- `paper_fills.jsonl`
- `portfolio_snapshots.jsonl`
- `equity_curve.jsonl`

It does not call `BrokerAdapter.submit_order`, does not use API keys, and does
not contact any broker, exchange, sandbox, or testnet.

## Deferred

- partial fills;
- cancellation lifecycle;
- external paper/sandbox broker reconciliation;
- market calendar logic;
- risk gates that affect decisions, deferred to M2D;
- dashboard portfolio/risk panels, deferred to M2D.
