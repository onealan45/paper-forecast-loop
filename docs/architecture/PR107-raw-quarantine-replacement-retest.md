# PR107 Raw Quarantine Replacement Retest

## Purpose

PR105 made lineage planning treat raw paper-shadow `QUARANTINE` as a
replacement-required strategy action. Active BTC-USD storage then produced a
lineage replacement card from that raw `QUARANTINE` outcome.

The replacement retest scaffold and read-only task planner still accepted only
the older `QUARANTINE_STRATEGY` action. That meant the line correctly routed to
replacement research, but the replacement card could not enter the retest
chain.

## Decision

Lineage replacement retest source checks now accept both replacement-required
action forms:

- `QUARANTINE`
- `QUARANTINE_STRATEGY`

This matches lineage routing while keeping revision candidate checks and
replacement lineage ownership checks unchanged.

## Non-Goals

- Do not broaden replacement retesting to `RETIRE`, `REVISE`,
  `REVISE_STRATEGY`, or promotion-ready outcomes.
- Do not weaken lineage ownership checks between the replacement card and its
  source root.
- Do not change artifact schemas or rewrite existing runtime storage.

## Verification

Regression coverage proves that a lineage replacement card sourced from raw
`QUARANTINE` can:

- create a pending replacement retest scaffold;
- build a read-only revision/replacement retest task plan whose first next task
  is protocol locking.
