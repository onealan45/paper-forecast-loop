# M2B Paper Order Ledger Architecture

## Goal

M2B converts eligible paper-only strategy decisions into local paper order
ledger artifacts.

The stage does not simulate fills, update positions, calculate NAV, reconcile
brokers, or submit to any external system.

## Decision

Add `PaperOrder` plus enum-style models:

- `PaperOrderStatus`
- `PaperOrderSide`
- `PaperOrderType`

Orders are persisted as `paper_orders.jsonl` and included in SQLite
migration/export parity.

The only order type in M2B is `TARGET_PERCENT`. This keeps the order tied to
the strategy decision's recommended allocation change without pretending that a
market order has been filled.

## CLI

```powershell
python .\run_forecast_loop.py paper-order --storage-dir <path> --decision-id latest
```

`--decision-id latest` selects the newest decision for the requested symbol.
A concrete decision id can be passed for deterministic replay of operator
actions.

## Order Creation Rules

M2B creates an order only when:

- health-check is not blocking;
- the decision exists;
- the decision action is `BUY`, `SELL`, or `REDUCE_RISK`;
- the decision is `tradeable=true`;
- there is no active paper order for the same symbol.

M2B creates no order when:

- action is `HOLD`;
- action is `STOP_NEW_ENTRIES`;
- decision is non-tradeable;
- health-check is blocking or repair is required;
- an active order already exists for the symbol.

`REDUCE_RISK` maps to a `SELL` target-percent order.

## Safety Boundary

Paper orders are local artifacts only. They do not call
`BrokerAdapter.submit_order`, do not use API keys, and do not reach a broker,
exchange, sandbox, or testnet.

## Deferred

- fills and partial fills;
- order cancellation lifecycle;
- positions, cash, NAV, realized and unrealized PnL;
- risk gates that modify decisions;
- dashboard order/risk panels;
- external paper or sandbox broker integration.
