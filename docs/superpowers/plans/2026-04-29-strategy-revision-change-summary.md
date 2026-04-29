# Plan: Strategy Revision Change Summary

## Scope

Make strategy self-evolution more readable by showing what each revision is
trying to change or repair. Keep the feature read-only and based on existing
strategy-card fields.

## Steps

1. Add failing tests requiring lineage revision nodes to expose strategy name,
   status, hypothesis, source outcome id, and failure attributions.
2. Extend `StrategyLineageRevisionNode` from existing `StrategyCard` data.
3. Render revision change summary rows in dashboard and operator console.
4. Update README, PRD, architecture, and review archive.
5. Run full verification gates.
6. Request independent reviewer subagent review before PR/merge.

## Acceptance Criteria

- Nested revision rows show hypothesis, source outcome, and intended fixes.
- Dashboard and operator console expose the same revision-change context.
- Existing lineage counts, action counts, and edge-case regressions remain
  intact.
- No strategy mutation, promotion, execution, broker behavior, runtime artifact,
  or secret is introduced.
- Full gates and reviewer subagent pass.
