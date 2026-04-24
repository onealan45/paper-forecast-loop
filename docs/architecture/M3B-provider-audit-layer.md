# M3B Provider Audit Layer Architecture

## Goal

M3B records every market-data provider read as an auditable artifact and makes
provider health visible to health-check and the static dashboard.

This stage does not add deterministic historical candle storage, ETF/stock
providers, macro data, broker integration, sandbox/testnet execution, or live
trading.

## Model

M3B adds `ProviderRun`.

Each provider run records:

- provider name
- symbol
- operation
- status: `success`, `empty`, or `error`
- start and completion timestamps
- candle count
- data window start/end when available
- schema version
- error type/message when failed

The current schema version is:

```text
market_candles_v1
```

## Recording Path

`AuditedMarketDataProvider` wraps the underlying provider used by `run-once`.

It records:

- `get_latest_candle_boundary`
- `get_recent_candles`
- `get_candles_between`

Failures are recorded before the exception is re-raised, so the normal
fail-closed run metadata and repair request path can still see the provider
failure.

## Health Rules

`health-check` now inspects `provider_runs.jsonl`:

- latest provider run status `error` -> blocking `provider_failure`
- latest provider run status `empty` -> blocking `provider_empty_data`
- unexpected schema version -> blocking `provider_schema_drift`
- latest provider run older than 24 hours -> warning `provider_stale`

## Dashboard

The dashboard includes a read-only provider audit panel showing:

- provider and operation
- status
- candle count
- data window
- schema version
- error text when present

## Repository Compatibility

`provider_runs.jsonl` is supported by:

- JSONL repository
- SQLite migration/export
- `db-health`
- `health-check` bad-row and duplicate-id detection

## Deferred

- deterministic candle storage and replay from stored candles;
- provider run typed relational tables;
- provider audit for macro events;
- ETF/stock provider prototype;
- multi-asset provider health rollups.
