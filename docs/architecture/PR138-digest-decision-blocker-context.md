# PR138 Digest Decision Blocker Context

## Problem

PR137 made the latest strategy decision name its main research blockers, but the
strategy research digest still focused on lineage, paper-shadow outcome, and
autopilot context. That meant the digest could summarize strategy research while
omitting the active decision blocker that is currently stopping BUY/SELL.

For an Alpha Factory loop, this weakens handoff quality: the next research step
should see both the historical strategy lineage and the current decision blocker
without scraping raw decision artifacts.

## Decision

`StrategyResearchDigest` now captures the latest same-symbol strategy decision
context:

- `decision_id`
- `decision_action`
- `decision_blocked_reason`
- `decision_research_blockers`
- `decision_reason_summary`

The digest builder links the latest decision id into `evidence_artifact_ids` and
extracts readable blockers from the `主要研究阻擋：...` reason summary.

Dashboard and operator-console strategy research digest panels now show a
`目前決策阻擋` row so the strategy UX surfaces the active blocker alongside
lineage and paper-shadow evidence.

## Scope

This is an additive schema and UX change. It does not change BUY/SELL gates,
risk gates, forecast scoring, broker behavior, or automation state.

Legacy digest rows remain readable because the new fields default to empty or
`None`.

## Verification

Regression coverage proves:

- recording a digest persists the latest decision context and blocker list;
- the digest links the decision id as evidence;
- the dashboard digest panel renders the decision blocker row;
- the operator console digest panel renders the same blocker context.
