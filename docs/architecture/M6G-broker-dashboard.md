# M6G Broker Dashboard

## Scope

M6G adds broker/sandbox visibility to the existing read-only static dashboard.

It does not add:

- live trading
- broker network calls
- real API key loading
- order submission
- order cancellation
- automatic repair execution

## Dashboard Section

The dashboard now includes `Broker / Sandbox 狀態`.

It shows:

- broker mode
- broker health from the latest execution gate
- latest execution gate status
- latest broker reconciliation status
- local paper account snapshot
- local paper positions
- open paper order count
- active broker lifecycle row count
- latest paper fill
- reconciliation mismatch warnings
- execution enabled/disabled
- failed execution gate checks

## Data Sources

The section reads only local artifacts:

- `portfolio_snapshots.jsonl`
- `paper_orders.jsonl`
- `broker_orders.jsonl`
- `paper_fills.jsonl`
- `broker_reconciliations.jsonl`
- `execution_safety_gates.jsonl`

No broker adapter is called during dashboard rendering.

## Safety

The dashboard is read-only. It does not expose secrets and does not provide a
submit/cancel control. It is an inspection layer for M6C-M6F artifacts.

## Deferred

Future work can add richer drill-down tables in the local operator console, but
M6G completes the static read-only broker/sandbox visibility requirement.
