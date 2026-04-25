# M6D External Paper Order Lifecycle

## Scope

M6D adds local broker order lifecycle tracking.

It does not add:

- real broker submission
- external network calls
- reconciliation
- execution safety gates
- broker dashboard
- live trading

## Artifact

`broker_orders.jsonl` stores `BrokerOrder` records linked to existing local
`paper_orders.jsonl` rows.

Statuses:

- `CREATED`
- `SUBMITTED`
- `ACKNOWLEDGED`
- `PARTIALLY_FILLED`
- `FILLED`
- `CANCELLED`
- `REJECTED`
- `EXPIRED`
- `ERROR`

## CLI

Create a local broker lifecycle record:

```powershell
python .\run_forecast_loop.py broker-order --storage-dir <storage> --order-id latest --mock-submit-status ACKNOWLEDGED
```

The command uses mock submit metadata only. It does not call the M6C adapter or
any external broker.

## Storage

M6D follows the existing artifact pattern:

- JSONL save/load
- SQLite migration/export/db-health parity
- health-check bad-row and duplicate-id audit

## Deferred

M6E should reconcile local broker lifecycle rows against external paper/sandbox
broker state.

M6F should add execution safety gates before any real sandbox submit path is
used by automation.

Live trading remains unavailable.
