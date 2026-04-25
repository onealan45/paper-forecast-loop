# M5B Decision Timeline

## Decision

M5B turns the operator console `decisions` page from a basic table into a
read-only decision timeline.

Each timeline card exposes:

- latest decision marker;
- action and symbol;
- decision timestamp and horizon;
- reason summary;
- evidence grade;
- risk level;
- tradeable status;
- recommended/current/max paper position;
- blocked reason;
- linked forecast ids;
- linked score ids;
- linked review ids;
- linked baseline ids;
- invalidation conditions.

## Implementation

- Module: `src/forecast_loop/operator_console.py`
- Page: `/decisions`
- Renderer helpers:
  - `_latest_decision_summary`
  - `_decision_card`
  - `_evidence_links`
  - `_conditions`

No new storage schema is introduced. The page reads existing
`strategy_decisions.jsonl` artifacts through `JsonFileRepository`.

## Safety Boundary

M5B remains read-only.

It does not:

- create decisions;
- alter decisions;
- submit orders;
- add controls;
- call brokers or exchanges;
- read secrets;
- promote paper strategy changes.

## Deferred

- Deep artifact drilldown is deferred.
- Filtering and search are deferred.
- Portfolio/risk UI depth remains M5C.
- Health/repair queue workflow remains M5D.
