# M6D External Paper Order Lifecycle Review

## Scope

Milestone: M6D External Paper Order Lifecycle.

This review covers local broker order lifecycle artifacts and CLI creation from
existing paper orders.

It does not cover external broker calls, broker reconciliation, execution safety
gates, broker dashboard, or live trading.

## Implementation Summary

- Added `BrokerOrderStatus`.
- Added `BrokerOrder` artifact model.
- Added `broker_orders.jsonl` support to JSONL storage.
- Added SQLite migration/export/db-health parity for broker orders.
- Added health-check bad-row and duplicate-id audit for broker orders.
- Added `broker_lifecycle.py`.
- Added `broker-order` CLI command.
- Added tests for lifecycle creation, duplicate blocking, CLI rejected
  lifecycle record, health audit, and SQLite parity.
- Kept the implementation local and mock-only; no external broker call is made.

## Verification

- `python -m pytest tests\test_broker_lifecycle.py tests\test_sqlite_repository.py -q`
  - Result: `10 passed in 2.23s`
- `python -m pytest -q`
  - Result: `204 passed in 7.45s`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Result: passed
- `python .\run_forecast_loop.py --help`
  - Result: passed
- `git diff --check`
  - Result: passed; only CRLF normalization warnings were printed

## Reviewer Status

Pending final reviewer subagent.

## Safety Status

No live trading path, no external broker call, no secret loading, no real API
key use, and no runtime artifacts are added in M6D.
