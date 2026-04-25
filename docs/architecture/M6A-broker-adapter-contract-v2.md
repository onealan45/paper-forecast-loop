# M6A Broker Adapter Contract V2

## Scope

M6A defines a broker adapter contract for future paper/sandbox execution work.

It does not add:

- live trading
- real broker or exchange submission
- external API calls
- API key handling
- secret configuration
- sandbox adapter implementation
- broker reconciliation
- execution safety gates

## Modes

The contract names three modes:

- `INTERNAL_PAPER`
- `EXTERNAL_PAPER`
- `SANDBOX`

Only `INTERNAL_PAPER` is implemented in M6A.

`EXTERNAL_PAPER`, `SANDBOX`, and `live` fail closed through
`build_broker_adapter(...)`.

## Contract Methods

`BrokerAdapter` now exposes:

- `mode`
- `get_account_snapshot`
- `get_positions`
- `submit_order`
- `cancel_order`
- `get_order_status`
- `get_fills`
- `health_check`

## Internal Paper Adapter

`PaperBrokerAdapter` is a safe internal stub:

- account snapshot returns an empty paper portfolio
- positions return the snapshot positions
- fills return an empty list
- submit returns `status=blocked`
- cancel returns `status=blocked`
- order status returns `status=unavailable`
- health-check reports live trading and external submit unavailable

This keeps future adapter callers explicit about what they need while preventing
accidental external execution.

## Deferred

Later M6 milestones may add:

- safe config and secret rules
- one sandbox/external paper adapter
- external paper order lifecycle
- reconciliation
- execution safety gates
- broker dashboard

Live mode remains out of scope.
