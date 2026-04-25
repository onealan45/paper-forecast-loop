# M6F External Paper Execution Safety Gates

## Scope

M6F adds a local safety gate artifact for future external paper/sandbox order
submission.

It does not add:

- live trading
- real broker endpoints
- real API key loading
- automatic submit/cancel
- automatic promotion from paper to live
- broker dashboard

## Artifact

`execution_safety_gates.jsonl` stores `ExecutionSafetyGate` rows.

Each row records:

- decision id
- paper order id
- broker and broker mode
- gate status: `PASS` or `BLOCKED`
- whether execution would be allowed
- per-check results
- linked health check id
- linked risk snapshot id
- linked broker reconciliation id

Blocked gates are expected operational outcomes and do not automatically make
storage unhealthy. `health-check` only audits malformed or duplicate gate rows.

## CLI

Run a gate check from local evidence and a broker-health fixture:

```powershell
python .\run_forecast_loop.py execution-gate --storage-dir <storage> --broker-health <broker-health.json> --broker-mode SANDBOX
```

The broker-health file is local JSON. It must report a healthy paper/sandbox
mode and `live_trading_available=false`.

Example:

```json
{
  "status": "healthy",
  "mode": "SANDBOX",
  "broker": "binance_testnet",
  "live_trading_available": false
}
```

The CLI accepts only `EXTERNAL_PAPER` or `SANDBOX`. `LIVE` and unknown modes
fail before `execution_safety_gates.jsonl` is written.

## Required Checks

M6F checks:

- health-check status is healthy
- operator controls allow the order
- decision is tradeable
- decision action is orderable
- evidence grade meets the configured minimum
- latest risk snapshot does not block execution
- broker health fixture is healthy and live trading is unavailable
- order size stays under `--max-order-position-pct`
- no duplicate active paper order exists
- no duplicate active broker order exists
- latest broker reconciliation is not blocking
- ETFs/stocks are on a trading day; crypto is continuous

## Safety

The gate performs no submit/cancel operation. It writes only a local paper-only
artifact and is intended to be consumed by M6G and later sandbox execution code.

## Deferred

M6G should show the latest gate result in the broker dashboard.
