# PR137 Decision Blocker Synthesis

## Problem

`generate_strategy_decision()` already records detailed research-gate failures
in `decision_basis`, but the user-facing `reason_summary` could collapse a
blocked HOLD decision into a generic baseline warning. In active storage, the
decision basis showed missing event edge, negative walk-forward evidence, and
overfit risk, while the visible summary only said the model did not beat naive
persistence.

That weakens strategy visibility. The operator sees that BUY/SELL is blocked,
but not which research work should improve prediction quality next.

## Decision

Decision generation now converts research-gate flags into a short Traditional
Chinese blocker summary and appends it to HOLD/REDUCE_RISK reasons when
research evidence is blocking directionality.

Examples:

- `research_event_edge_missing` -> `event edge 缺失`
- `research_backtest_missing` -> `backtest 缺失`
- `research_walk_forward_overfit_risk` -> `walk-forward overfit risk`
- `research_model_edge_not_positive` -> `model edge 不為正`

The action and gating logic do not change. This PR only makes the reason
summary more diagnostic so dashboard/operator-console surfaces can show the
actual research blockers without parsing raw `decision_basis`.

## Scope

This does not loosen BUY/SELL gates, create new strategy evidence, or change
artifact schemas. It is a strategy visibility improvement for existing decision
artifacts.

## Verification

Regression coverage proves:

- a model-not-beating-baseline HOLD decision includes concrete research
  blockers such as missing event edge and missing backtest;
- dashboard rendering uses the specific blocked decision `reason_summary`
  instead of hiding those blockers behind a generic baseline sentence.
