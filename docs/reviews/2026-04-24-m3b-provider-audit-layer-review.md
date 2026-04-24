# M3B Provider Audit Layer Review

## Scope

- Stage: M3B Provider Audit Layer
- Branch: `codex/m3b-provider-audit`
- Boundary: provider audit artifacts and visibility only; no deterministic candle store, no ETF/stock provider, no macro data, no broker submit, no sandbox/testnet, no live trading, no secrets.

## Implementation Summary

- Added `ProviderRun`.
- Added `provider_runs.jsonl` support to JSONL repository.
- Added SQLite migration/export/db-health parity for provider runs.
- Added `AuditedMarketDataProvider` wrapper.
- `run-once` now records provider audit artifacts for provider reads.
- Provider failures are recorded before exceptions are re-raised.
- `health-check` now detects:
  - `provider_failure`
  - `provider_empty_data`
  - `provider_schema_drift`
  - `provider_stale`
- Dashboard now renders a provider audit panel with provider, operation, status,
  candle count, data window, schema version, and error text.
- Updated README, PRD, and architecture docs.
- Final-review blocker remediation:
  - `ProviderRun.from_dict` now requires provider audit id, provider, symbol,
    operation, status, created/started/completed timestamps, candle count, and
    schema version instead of defaulting missing audit fields.
  - Provider run status is constrained to `success`, `empty`, or `error`.
  - Required provider run timestamps must include timezone information.
  - Malformed JSONL provider-run rows produce `bad_json_row`.
  - Malformed SQLite provider-run payloads produce `sqlite_bad_payload`.

## Test Evidence

```powershell
python -m pytest tests/test_provider_audit.py tests/test_sqlite_repository.py -q
```

Result: `14 passed`.

```powershell
python -m pytest -q
```

Result: `114 passed`.

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
```

Result: passed.

```powershell
python .\run_forecast_loop.py --help
git diff --check
```

Result: passed.

## Smoke Evidence

```powershell
python .\run_forecast_loop.py run-once --provider sample --symbol BTC-USD --storage-dir .\paper_storage\manual-m3b-check-20260424T1630Z --now 2026-04-24T16:30:00+00:00 --also-decide
python .\run_forecast_loop.py render-dashboard --storage-dir .\paper_storage\manual-m3b-check-20260424T1630Z
python .\run_forecast_loop.py migrate-jsonl-to-sqlite --storage-dir .\paper_storage\manual-m3b-check-20260424T1630Z
python .\run_forecast_loop.py db-health --storage-dir .\paper_storage\manual-m3b-check-20260424T1630Z
python .\run_forecast_loop.py export-jsonl --storage-dir .\paper_storage\manual-m3b-check-20260424T1630Z --output-dir .\paper_storage\manual-m3b-export-20260424T1630Z
```

Result:

- `run-once` created `decision:b29e8ee92641c60f` with action `HOLD`.
- SQLite migration/export reported `provider_runs: 3`.
- `db-health` returned `healthy`, `severity: none`, `repair_required: false`.
- Dashboard contained `資料來源健康`, `Provider Audit`, and `正常（success）`.
- Manual smoke storage/export paths are ignored by `.gitignore`.

## Known Deferrals

- deterministic historical candle storage and replay from stored candles;
- ETF/stock provider prototype;
- macro event provider audit;
- multi-asset provider health rollups;
- typed relational provider-run tables.

## Final Reviewer

- Reviewer subagent: Copernicus (`019dc0c8-4ae2-73e0-8dc8-9b3447e479a5`)
- First pass: `BLOCKED` on strict ProviderRun deserialization.
- Remediation: implemented and verified with the updated test evidence above.
- Re-review: `APPROVED`
- Status: approved; no blocking findings remain.
