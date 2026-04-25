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

After reviewer P1 fixes:

- `python -m pytest tests\test_m1_strategy.py::test_health_check_flags_secret_leak_without_echoing_secret_value tests\test_m1_strategy.py::test_health_check_flags_prefixed_env_secret_names tests\test_m1_strategy.py::test_health_check_allows_non_secret_local_env tests\test_m1_strategy.py::test_health_check_allows_blank_example_secret_placeholders tests\test_m1_strategy.py::test_health_check_allows_example_config_env_variable_names -q`
  - Result: `5 passed in 0.41s`
- `python -m pytest -q`
  - Result: `196 passed in 7.14s`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Result: passed
- `python .\run_forecast_loop.py --help`
  - Result: passed
- `git diff --check`
  - Result: passed; only CRLF normalization warnings were printed

## Reviewer Status

Initial final reviewer subagent: `Carson`
(`019dc2b1-f581-7fb1-bd44-419f4a295652`).

Initial result: `BLOCKED`.

Blocking findings:

- Scanner missed prefixed env secret names such as `ALPACA_PAPER_API_KEY`,
  `BINANCE_TESTNET_API_SECRET`, and `TELEGRAM_BOT_TOKEN`.
- Scanner blocked any root `.env` file even when it contained only non-secret
  local settings.

Fix:

- Updated the scanner to match secret keywords inside longer env/key names.
- Changed `.env` handling to scan content instead of blocking the file solely
  because it exists.
- Added regression tests for prefixed secret names, non-secret `.env`, blank
  example placeholders, and `*_env` config values that point to env var names.

Final reviewer status after fix: `APPROVED`.

Re-review result:

- Both original P1s are resolved.
- Scanner flags prefixed env secret names.
- Scanner allows non-secret local `.env`.
- Scanner allows blank `.env.example` placeholders.
- Scanner treats `*_env` config values as env-var references.
- Safety boundary was rechecked: no real secrets, no secret loading, no external
  broker/exchange calls, no sandbox/testnet submit path, no live trading path,
  and no tracked runtime artifacts.

Residual non-blocking risk:

- The scanner remains heuristic. Before real external-paper or sandbox
  integrations, later milestones should add provider-specific credential
  pattern validation.

## Safety Status

No external broker/exchange path, no sandbox/testnet submit path, no live
trading path, no API key loading, and no secret storage are added in M6B.
