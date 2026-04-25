# M5F Automation Run Log

## Decision

M5F adds an append-only `automation_runs.jsonl` artifact for paper-only cycle
traceability.

Each `run-once` invocation writes one automation run row after the cycle
finishes. The row links:

- cycle status;
- provider and symbol;
- ordered step status;
- health-check id when a health check ran;
- strategy decision id when a decision was emitted;
- repair request id when health required repair.

## Status Values

- `completed`: the cycle finished without repair-required health findings.
- `repair_required`: the cycle finished, but health-check created or referenced
  a repair-required condition.
- `failed`: the run cycle raised an exception and wrote fail-closed metadata.

## Steps

Current step names:

- `forecast`
- `score`
- `review`
- `proposal`
- `health_check`
- `risk_check`
- `decide`

Each step records a status and optional artifact id. This is intentionally a
simple audit trail, not a workflow engine.

## Storage

`automation_runs.jsonl` is supported by:

- JSONL repository load/save;
- health-check bad-row and duplicate-id audit;
- SQLite migration/export/db-health parity;
- operator console overview display.

## Safety Boundary

M5F does not add:

- a scheduler;
- Codex automation TOML mutation;
- browser controls;
- broker/exchange integration;
- sandbox/testnet integration;
- live trading;
- secret handling.

## Deferred

- Cross-run metrics remain deferred.
- Scheduler orchestration remains outside this repo.
- Notification artifacts remain M5G.
- External broker reconciliation remains M6.
