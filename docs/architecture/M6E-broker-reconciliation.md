# M6E Broker Reconciliation

## Scope

M6E adds local reconciliation between the paper ledger and an external
paper/sandbox account snapshot fixture.

It does not add:

- live trading
- live broker endpoints
- real API key loading
- automatic order submission
- automatic repair execution
- broker dashboard

## Artifact

`broker_reconciliations.jsonl` stores `BrokerReconciliation` rows.

Each row records:

- local broker order ids checked
- external broker order references observed
- matched order references
- missing local tracked orders
- unknown external orders
- duplicate external broker order references
- broker status mismatches
- cash, equity, and position mismatches
- `repair_required`

## CLI

Run reconciliation from a fixture snapshot:

```powershell
python .\run_forecast_loop.py broker-reconcile --storage-dir <storage> --external-snapshot <snapshot.json> --broker-mode SANDBOX
```

The snapshot is local JSON and is expected to contain optional `orders`,
`positions`, `cash`, and `equity` fields.

Example:

```json
{
  "orders": [
    {"broker_order_ref": "testnet:123", "status": "ACKNOWLEDGED"}
  ],
  "positions": [
    {"symbol": "BTC-USD", "quantity": 0.1}
  ],
  "cash": 9000.0,
  "equity": 10000.0
}
```

The CLI accepts only `EXTERNAL_PAPER` or `SANDBOX`. `LIVE` and unknown modes
fail before `broker_reconciliations.jsonl` is written.

## Health Behavior

If the latest reconciliation has `repair_required=true` or blocking severity,
`health-check` emits `broker_reconciliation_blocking`. This keeps reconciliation
mismatches inside the existing Codex repair-request path.

## Safety

M6E uses fixture snapshots only. It does not call the M6C adapter, does not
reach a broker network endpoint, and does not read secrets.

## Deferred

M6F should use reconciliation status as one of the execution safety gates before
any sandbox submit path is enabled.

M6G should render broker/sandbox reconciliation status in the dashboard.
