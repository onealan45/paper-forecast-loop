# M6A Broker Adapter Contract V2 Review

## Scope

Milestone: M6A Broker Adapter Contract V2.

This review covers broker contract shape, internal paper adapter fail-closed
behavior, and safety boundary documentation.

It does not cover external paper adapters, sandbox adapters, API keys, secret
configuration, broker reconciliation, execution safety gates, broker dashboard,
or live trading.

## Implementation Summary

- Added `BrokerMode` with `INTERNAL_PAPER`, `EXTERNAL_PAPER`, and `SANDBOX`.
- Expanded `BrokerAdapter` contract to expose:
  - `mode`
  - `get_account_snapshot`
  - `get_positions`
  - `submit_order`
  - `cancel_order`
  - `get_order_status`
  - `get_fills`
  - `health_check`
- Kept `PaperBrokerAdapter` as the only implementation.
- Made adapter `submit_order` and `cancel_order` return blocked responses.
- Made `EXTERNAL_PAPER`, `SANDBOX`, and `live` modes fail closed in
  `build_broker_adapter`.
- Added tests proving only internal paper mode is available and live mode is
  unsupported.
- Updated README, PRD, and architecture docs.

## Verification

- `python -m pytest tests\test_m1_strategy.py::test_paper_broker_is_only_available_mode -q`
  - Result: `1 passed in 0.38s`
- `python -m pytest -q`
  - Result: `191 passed in 7.00s`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Result: passed
- `python .\run_forecast_loop.py --help`
  - Result: passed
- `git diff --check`
  - Result: passed; only CRLF normalization warnings were printed

## Reviewer Status

Pending final reviewer subagent.

## Safety Status

No external broker/exchange path, no live trading path, no API key handling, no
secret handling, and no runtime artifacts are added in M6A.
