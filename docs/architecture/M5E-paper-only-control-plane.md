# M5E Paper-Only Control Plane

## Decision

M5E adds an audited paper-only control plane backed by local artifacts.

Controls are written through:

```powershell
python run_forecast_loop.py operator-control
```

The local operator console remains read-only. Its `control` page shows current
control state, recent audit events, and CLI command examples, but it does not
render forms or execute controls from the browser.

## Control Actions

Supported actions:

- `PAUSE`
- `RESUME`
- `STOP_NEW_ENTRIES`
- `REDUCE_RISK`
- `EMERGENCY_STOP`
- `SET_MAX_POSITION`

`RESUME`, `EMERGENCY_STOP`, and `SET_MAX_POSITION` require `--confirm`.
All successful controls write `control_events.jsonl`.

## Paper Execution Gates

Control events affect local paper order creation only:

- `EMERGENCY_STOP` blocks every local paper order.
- `PAUSE` blocks every local paper order.
- `STOP_NEW_ENTRIES` blocks BUY paper orders.
- `REDUCE_RISK` blocks BUY paper orders and still allows risk-reducing SELL
  paper orders.
- `SET_MAX_POSITION` blocks BUY paper orders whose target position exceeds the
  current control cap.

These gates do not submit, cancel, reconcile, or communicate with any broker,
exchange, sandbox, or testnet.

## Storage

`control_events.jsonl` is supported by:

- JSONL repository load/save;
- health-check bad-row and duplicate-id audit;
- SQLite migration/export/db-health parity;
- operator console read-only display.

## Safety Boundary

M5E does not add:

- live trading;
- real broker or exchange execution;
- sandbox/testnet broker integration;
- secret handling;
- browser form submission;
- automatic strategy promotion.

## Deferred

- Browser-based control forms remain deferred.
- Control status mutation beyond append-only events remains deferred.
- Multi-operator authorization remains deferred.
- Broker/sandbox reconciliation remains M6.
