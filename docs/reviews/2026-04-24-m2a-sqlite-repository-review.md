# M2A SQLite Repository Review

## Scope

- Stage: M2A SQLite Repository
- Branch: `codex/m2a-sqlite-repository`
- Boundary: paper-only; no paper order ledger, fills, NAV, risk gates, broker integration, secrets, or live trading.

## Implementation Summary

- Added `ArtifactRepository` protocol shape for repository-compatible load/save methods.
- Added `SQLiteRepository` with schema versioning.
- Added SQLite schema:
  - `schema_migrations`
  - `artifacts`
  - `idx_artifacts_type_sequence`
- Added M2A CLI commands:
  - `init-db`
  - `migrate-jsonl-to-sqlite`
  - `db-health`
  - `export-jsonl`
- Added migration from JSONL artifacts into SQLite.
- Added JSONL compatibility export from SQLite.
- Added SQLite health check for schema version, duplicate ids, and payload parseability.
- Added tests for repository parity, migration idempotency, export compatibility, and operator-friendly missing-db health output.
- Updated README, PRD, and architecture docs.

## Test Evidence

```powershell
python -m pytest tests/test_sqlite_repository.py -q
```

Result: `5 passed`.

```powershell
python -m pytest -q
```

Result: `77 passed`.

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
```

Result: passed.

```powershell
python .\run_forecast_loop.py --help
```

Result: passed and showed `init-db`, `migrate-jsonl-to-sqlite`, `export-jsonl`, and `db-health`.

```powershell
git diff --check
```

Result: passed.

## M2A Smoke Evidence

```powershell
python .\run_forecast_loop.py run-once --provider sample --symbol BTC-USD --storage-dir .\paper_storage\manual-m2a-check --also-decide
python .\run_forecast_loop.py init-db --storage-dir .\paper_storage\manual-m2a-check
python .\run_forecast_loop.py db-health --storage-dir .\paper_storage\manual-m2a-check
python .\run_forecast_loop.py migrate-jsonl-to-sqlite --storage-dir .\paper_storage\manual-m2a-check
python .\run_forecast_loop.py migrate-jsonl-to-sqlite --storage-dir .\paper_storage\manual-m2a-check
python .\run_forecast_loop.py db-health --storage-dir .\paper_storage\manual-m2a-check
python .\run_forecast_loop.py export-jsonl --storage-dir .\paper_storage\manual-m2a-check --output-dir .\paper_storage\manual-m2a-export
```

Results:

- sample run produced a pending forecast and `HOLD` decision;
- `init-db` created `forecast_loop.sqlite3` with schema version 1;
- `db-health` returned `healthy`;
- first migration inserted forecast, baseline, decision, and portfolio rows;
- second migration inserted zero rows, proving idempotency;
- export wrote JSONL compatibility artifacts from SQLite;
- generated `paper_storage` artifacts remained ignored by `.gitignore`.

## Known Deferrals

- The current hourly loop still writes JSONL artifacts by default.
- Dashboard and JSONL health-check reads are not switched to SQLite in M2A.
- Paper order ledger, fills, NAV, typed paper trading tables, and risk gates remain deferred to M2B-M2D.

## Final Reviewer

- Reviewer subagent: `019dc011-fd22-7393-a25e-b18b202a4709`
- Status: `APPROVED`
- Blocking findings: none

Reviewer confirmed:

- M2A scope is satisfied: repository protocol, SQLite schema/versioning,
  `init-db`, `migrate-jsonl-to-sqlite`, `export-jsonl`, `db-health`, and
  idempotency/parity tests.
- M2B/M2C/M2D scope was not implemented early.
- No live trading path, secret, `.env`, `.codex/`, `paper_storage/`, or tracked
  runtime artifact risk was found.

Nonblocking risks:

- Runtime loop, dashboard, and JSONL health-check still read/write JSONL by
  default; later M2 integration must test the switch.
- `export-jsonl` only writes artifact JSONL files that have data. Existing
  loaders treat missing files as empty collections, so this is acceptable for
  M2A.
