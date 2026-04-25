# M5D Health / Repair Queue

## Decision

M5D expands the local operator console `health` page into a read-only health and
repair-request inspection surface.

The page exposes:

- current health status;
- health severity;
- whether repair is required;
- blocking findings before the raw finding table;
- repair request queue status;
- repair request prompt path;
- reproduction command;
- affected artifacts;
- recommended tests;
- acceptance criteria.

## Implementation

- Module: `src/forecast_loop/operator_console.py`
- Page: `/health`
- Data sources:
  - `run_health_check(..., create_repair_request=False)` for current health;
  - existing `repair_requests.jsonl` rows for the repair queue.

The page intentionally does not create new repair requests while rendering.
Rendering an operator console page must not mutate health state or trigger
automation side effects.

## Safety Boundary

M5D remains read-only.

It does not:

- execute repairs;
- update repair request status;
- run Codex;
- start automation;
- pause or resume automation;
- create orders;
- call brokers or exchanges;
- read secrets;
- execute live trading.

## Deferred

- Repair request status mutation remains deferred.
- Automatic repair execution is out of scope for this repo.
- Health notifications remain M5G.
- Audited operator controls remain M5E.
