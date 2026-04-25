# M6C First Sandbox Broker Adapter

## Scope

M6C adds the first external paper/sandbox broker adapter surface:
`BinanceTestnetBrokerAdapter`.

It does not add:

- live trading
- live Binance endpoint support
- order lifecycle tracking
- reconciliation
- execution safety gates
- broker dashboard
- secret storage
- automatic environment loading

## Why Binance Testnet

The project's current active symbol and automation storage are crypto-first
(`BTC-USD`). Binance testnet is therefore a smaller first sandbox surface than a
stock/ETF paper broker.

## Safety Model

The adapter:

- runs in `SANDBOX` mode only
- refuses non-testnet endpoints
- requires explicit API key and API secret values from the caller
- redacts secrets from health-check output
- defaults to a blocking HTTP client
- supports injected HTTP clients so tests can mock all external calls
- uses Binance `/api/v3/order/test` for submit smoke behavior
- leaves cancel/status/fills as blocked or unavailable until later milestones

`build_broker_adapter("SANDBOX", broker="binance_testnet", ...)` fails if keys
are missing.

## Deferred

M6D+ should add local-to-broker order lifecycle tracking.
M6E+ should add reconciliation.
M6F+ should add execution safety gates before any sandbox submit is allowed by a
control plane.

Live mode remains unavailable.
