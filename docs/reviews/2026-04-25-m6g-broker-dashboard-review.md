# M6G Broker Dashboard Review

## Scope

Milestone: M6G Broker Dashboard.

This review covers read-only broker/sandbox visibility in the static dashboard.

It does not cover live broker calls, real API keys, submit/cancel controls,
external network calls, or automatic execution.

## Implementation Summary

- Added broker/sandbox fields to `DashboardSnapshot`.
- Added a `Broker / Sandbox` sidebar link and dashboard section.
- Rendered broker mode, broker health gate, execution gate, reconciliation,
  local paper account snapshot, positions, open orders, fills, mismatch
  warnings, and execution enabled/disabled state.
- Added dashboard test coverage for blocked execution, reconciliation mismatch,
  active broker rows, paper fills, and position display.
- Updated README, PRD, and architecture docs.
- Kept the dashboard read-only and local-artifact-only.

## Verification

- `python -m pytest tests\test_dashboard.py -q`
  - Result: `12 passed in 0.55s`
- `python -m pytest -q`
  - Result: `216 passed in 7.99s`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Result: passed
- `python .\run_forecast_loop.py --help`
  - Result: passed
- `git diff --check`
  - Result: passed; only CRLF normalization warnings were printed
- `python .\run_forecast_loop.py render-dashboard --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD`
  - Result: passed; dashboard regenerated in ignored runtime storage

## Reviewer Status

Pending final reviewer subagent.

## Safety Status

No live trading path, no external broker call, no secret loading, no real API
key use, and no runtime artifacts are added in M6G.
