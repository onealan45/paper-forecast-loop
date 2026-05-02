# PR148 Digest Blocker Evidence Metrics

## Context

The operator surfaces already showed the latest strategy research digest, but
the digest could summarize a blocked strategy without exposing the concrete
event-edge, backtest, and walk-forward metrics behind the blocker. That made the
UX read like a status panel instead of a research console.

## Decision

`strategy-research-digest` now enriches the existing digest fields instead of
adding a new schema:

- `evidence_artifact_ids` includes the latest same-symbol event-edge,
  backtest-result, and walk-forward artifact ids available at digest time.
- `research_summary` appends a concise evidence line with event-edge sample and
  after-cost edge, backtest strategy versus benchmark return, and walk-forward
  excess/window/overfit context.
- Evidence selection is point-in-time: artifacts created after the digest
  timestamp are ignored.

## Operator Impact

Dashboard and operator console already render `research_summary` and
`evidence_artifact_ids`, so the newest digest immediately shows concrete
strategy evidence without changing read-only UI structure.

## Deferred

This PR does not add a new first-class metric table to the digest schema. If the
summary grows too dense, a later PR should add structured digest evidence cards
while preserving JSONL/SQLite compatibility.
