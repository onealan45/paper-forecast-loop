# M6C First Sandbox Broker Adapter Review

## Scope

Milestone: M6C First Sandbox Broker Adapter.

This review covers the first mockable sandbox/testnet broker adapter and its
safety boundary.

It does not cover live trading, real order execution, order lifecycle tracking,
broker reconciliation, execution safety gates, broker dashboard, or secret
storage.

## Implementation Summary

- Added `BrokerHttpClient` protocol.
- Added default `BlockingBrokerHttpClient`.
- Added `BinanceTestnetBrokerAdapter`.
- Kept adapter mode as `SANDBOX`.
- Required explicit API key and API secret constructor inputs.
- Rejected non-testnet endpoints.
- Used `/api/v3/order/test` for mocked submit behavior.
- Kept cancel/status/fills blocked or unavailable.
- Added tests for missing key fail-safe, live endpoint refusal, mocked submit,
  health secret redaction, and default HTTP blocking.
- Updated README, PRD, architecture docs, and broker example config.

## Verification

- `python -m pytest tests\test_broker.py tests\test_m1_strategy.py::test_paper_broker_is_only_available_mode -q`
  - Result: `5 passed in 0.32s`
- `python -m pytest -q`
  - Result: `200 passed in 7.04s`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Result: passed
- `python .\run_forecast_loop.py --help`
  - Result: passed
- `git diff --check`
  - Result: passed; only CRLF normalization warnings were printed

After reviewer P1 fix:

- `python -m pytest tests\test_broker.py -q`
  - Result: `4 passed in 0.09s`
- `python -m pytest -q`
  - Result: `200 passed in 7.08s`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Result: passed
- `python .\run_forecast_loop.py --help`
  - Result: passed
- `git diff --check`
  - Result: passed; only CRLF normalization warnings were printed

## Reviewer Status

Initial final reviewer subagent: `Laplace`
(`019dc2bf-b332-7dc1-b276-2095d4c8d530`).

Initial result: `BLOCKED`.

Blocking finding:

- `BinanceTestnetBrokerAdapter` used default dataclass repr, so `repr(adapter)`
  included `api_key` and `api_secret`.

Fix:

- Marked `api_key` and `api_secret` with `field(repr=False)`.
- Added regression coverage proving the adapter repr does not contain key or
  secret values.

Final reviewer status after fix: `APPROVED`.

Re-review result:

- P1 is resolved.
- `api_key` and `api_secret` now use `field(repr=False)`.
- Regression test and direct probe confirm `repr(adapter)` no longer contains
  key or secret values.
- Safety boundary was rechecked: no real secrets, no secret loading, no usable
  live endpoint path, no live trading path, broker calls go through injected
  `http_client`, tests use fake clients, and no runtime artifacts are tracked.

Residual non-blocking risk:

- Actual Binance signing and real testnet smoke behavior remain deferred. M6C
  is a mockable `/api/v3/order/test` adapter surface, not a production-ready
  broker lifecycle.

## Safety Status

No live trading path, no live Binance endpoint, no real secret committed, no
secret loading, no unmocked external call in tests, and no runtime artifacts are
added in M6C.
