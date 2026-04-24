# M3E Macro Event Model Review

## Scope

- Stage: M3E Macro Event Model
- Branch: `codex/m3e-macro-event-model`
- Boundary: macro event fixture import, calendar inspection, JSONL/SQLite
  storage parity, and docs only; no live macro provider, no macro strategy
  features, no broker submit, no sandbox/testnet, no live trading, no secrets.

## Implementation Summary

- Added `MacroEvent` for CPI, PCE, FOMC, GDP, NFP, and unemployment events.
- Added `macro_events.jsonl` support to JSONL storage.
- Added SQLite migration/export/db-health parity for macro events.
- Added CLI:
  - `import-macro-events`
  - `macro-calendar`
- Macro imports are idempotent through stable `macro-event:*` IDs.
- `macro-calendar` is read-only and fails closed when the storage directory
  does not exist.
- Macro datetime fields must be timezone-aware.
- Macro numeric fields must be finite.
- Updated README, PRD, and architecture docs.

## Test Evidence

```powershell
python -m pytest tests/test_macro_events.py tests/test_sqlite_repository.py -q
```

Result: `13 passed`.

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
```

Result: passed.

```powershell
python -m pytest -q
```

Result: `136 passed`.

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Result: passed.

## Smoke Evidence

```powershell
python .\run_forecast_loop.py import-macro-events --storage-dir .\paper_storage\manual-m3e-check-20260424T1930Z --input .\paper_storage\manual-m3e-macro-20260424T1930Z.jsonl --source fixture --imported-at 2026-04-24T19:30:00+00:00
python .\run_forecast_loop.py macro-calendar --storage-dir .\paper_storage\manual-m3e-check-20260424T1930Z --start 2026-04-01T00:00:00+00:00 --end 2026-04-30T23:59:00+00:00 --region US
python .\run_forecast_loop.py migrate-jsonl-to-sqlite --storage-dir .\paper_storage\manual-m3e-check-20260424T1930Z
python .\run_forecast_loop.py db-health --storage-dir .\paper_storage\manual-m3e-check-20260424T1930Z
python .\run_forecast_loop.py export-jsonl --storage-dir .\paper_storage\manual-m3e-check-20260424T1930Z --output-dir .\paper_storage\manual-m3e-export-20260424T1930Z
```

Result:

- `import-macro-events` imported three rows.
- `macro-calendar` returned two April US events and excluded the May NFP row.
- Raw CLI JSON preserved UTC `+00:00` timestamps; PowerShell
  `ConvertFrom-Json` display conversion was not artifact drift.
- SQLite migration/export reported `macro_events: 3`.
- `db-health` returned `healthy`.
- Manual smoke storage/input/export paths are ignored by `.gitignore`.

## Known Deferrals

- provider-specific macro importers;
- macro surprise calculation;
- macro event linkage to research datasets;
- macro-aware baseline evaluation;
- decision gates based on macro state;
- multi-asset macro calendar views.

## Final Reviewer

- Reviewer subagent: Planck (`019dc0f3-d8de-74f1-af84-3be9219760ee`)
- Re-review needed: no
- Status: approved; no blocking findings.

Residual non-blocking risks:

- macro events are not yet visible in the dashboard;
- macro events do not yet influence research features, baselines, risk gates,
  or strategy decisions.
