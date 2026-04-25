# M6F External Paper Execution Safety Gates Review

## Scope

Milestone: M6F External Paper Execution Safety Gates.

This review covers local safety-gate artifacts and CLI checks before a future
external paper/sandbox submit path may proceed.

It does not cover live broker calls, real API keys, real submit/cancel,
broker dashboard, or automatic execution.

## Implementation Summary

- Added `ExecutionSafetyGateStatus`.
- Added `ExecutionSafetyGate` artifact model.
- Added `execution_safety_gates.jsonl` support to JSONL storage.
- Added SQLite migration/export/db-health parity for execution gates.
- Added `execution_safety.py`.
- Added `execution-gate` CLI command.
- Added health-check bad-row and duplicate-id audit for execution gates.
- Added tests for passing gates, weak evidence, duplicate active broker order,
  unhealthy broker health, live-mode rejection, closed stock market, health
  audit, and SQLite parity.
- Kept the implementation local and gate-only; no submit/cancel call is made.
- Follow-up reviewer P1 fixed: `duplicate_active_broker_order` now blocks any
  active broker order on the same symbol/broker/mode, not only the same local
  paper order id.

## Verification

- `python -m pytest tests\test_execution_safety.py tests\test_sqlite_repository.py -q`
  - Result: `11 passed in 2.44s`
- `python -m pytest -q`
  - Result: `215 passed in 7.53s`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Result: passed
- `python .\run_forecast_loop.py --help`
  - Result: passed
- `git diff --check`
  - Result: passed; only CRLF normalization warnings were printed

## Reviewer Status

Reviewer subagent found a P1 duplicate active broker-order blocker. The blocker
was fixed and is pending re-review.

## Safety Status

No live trading path, no external broker call, no secret loading, no real API
key use, and no runtime artifacts are added in M6F.
