# M2A SQLite Repository Architecture

## Goal

M2A introduces a SQLite repository for canonical M2 state while preserving JSONL
as the compatibility and audit export format.

This stage does not implement paper order creation, fills, NAV, risk gates,
multi-asset support, or broker integration.

## Decision

Add `SQLiteRepository` behind the same load/save method shape used by
`JsonFileRepository`.

The initial schema uses:

- `schema_migrations`: records applied schema versions.
- `artifacts`: stores each artifact payload as canonical JSON with
  `artifact_type`, `artifact_id`, insertion order, optional artifact timestamp,
  and a uniqueness constraint on `(artifact_type, artifact_id)`.

This is intentionally a narrow M2A step. Typed relational tables for paper
orders, fills, positions, risk snapshots, provider runs, and research datasets
belong to their later milestones.

## Why Not Remove JSONL

JSONL remains useful for:

- audit exports;
- backward compatibility with existing dashboards and health checks;
- safe migration rollback;
- human-readable artifact inspection.

The current hourly loop still writes JSONL by default while M2A proves SQLite
migration, health, idempotency, and export parity.

## CLI Surface

M2A adds:

```powershell
python .\run_forecast_loop.py init-db --storage-dir <path>
python .\run_forecast_loop.py migrate-jsonl-to-sqlite --storage-dir <path>
python .\run_forecast_loop.py db-health --storage-dir <path>
python .\run_forecast_loop.py export-jsonl --storage-dir <path> --output-dir <path>
```

`db-health` is intentionally separate from `health-check` because it inspects
SQLite schema and payload integrity rather than the active JSONL operational
loop.

## Migration Rules

- Migration is idempotent.
- Duplicate artifact IDs are ignored rather than inserted twice.
- Score migration preserves the existing rule that a forecast should have at
  most one score.
- Export writes JSONL files with the same artifact families used by the M1
  repository.

## Deferred

- Switching the hourly automation to SQLite-backed execution.
- Dual-write from every loop command.
- Typed relational paper order and portfolio tables.
- SQLite-backed dashboard and health-check reads.
- SQLite-backed replay run registry.
