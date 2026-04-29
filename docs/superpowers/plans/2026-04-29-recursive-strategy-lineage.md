# Plan: Recursive Strategy Lineage

## Scope

Follow up PR31's accepted residual risk: strategy lineage currently covers only
the root strategy card and direct revisions. This PR makes lineage recursive so
multi-generation self-evolution history remains visible.

## Steps

1. Add failing tests for a second-generation revision tree.
2. Update `forecast_loop.strategy_lineage` to resolve the original root and
   collect all descendants.
3. Ensure dashboard and operator console snapshots/rendering include nested
   revision outcomes without extra UI code paths.
4. Update project and architecture docs.
5. Run targeted and full verification gates.
6. Send the branch to a reviewer subagent and archive the review.

## Acceptance Criteria

- A current card that is a second-generation revision resolves to the original
  root strategy.
- `revision_card_ids`, action counts, failure-attribution counts, best/worst
  excess returns, and latest outcome include nested revision outcomes.
- Dashboard and operator console show nested lineage evidence.
- No strategy execution, promotion, broker behavior, or runtime artifact is
  introduced.
- Full test and compile gates pass.
