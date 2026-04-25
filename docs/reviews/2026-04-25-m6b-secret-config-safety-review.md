# M6B Secret / Config Safety Review

## Scope

Milestone: M6B Secret / Config Safety.

This review covers safe example config files, `.env` ignore rules,
secret-management documentation, and health-check detection for obvious secret
leakage.

It does not cover external broker adapters, sandbox/testnet submission,
notification delivery, real API keys, secret loading, broker reconciliation,
or live trading.

## Implementation Summary

- Added `.env.example` with blank local placeholders.
- Added `config/brokers.example.yml` with non-secret internal paper,
  external-paper, and sandbox examples.
- Updated `.gitignore` so `.env` and `.env.*` are ignored while
  `.env.example` remains trackable.
- Added `docs/secrets-management.md`.
- Added health-check detection for obvious secret-looking assignments in repo
  safety files and selected storage artifacts.
- Ensured health findings do not echo detected secret values.
- Added tests for leak detection and blank placeholder safety.

## Verification

- `python -m pytest tests\test_m1_strategy.py::test_health_check_flags_secret_leak_without_echoing_secret_value tests\test_m1_strategy.py::test_health_check_allows_blank_example_secret_placeholders -q`
  - Result: `2 passed in 0.26s`
- `python -m pytest -q`
  - Result: `193 passed in 6.85s`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Result: passed
- `python .\run_forecast_loop.py --help`
  - Result: passed
- `git diff --check`
  - Result: passed; only CRLF normalization warnings were printed

## Reviewer Status

Pending final reviewer subagent.

## Safety Status

No external broker/exchange path, no sandbox/testnet submit path, no live
trading path, no API key loading, and no secret storage are added in M6B.
