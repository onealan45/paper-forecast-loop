# Plan: Strategy Lineage Tree Visibility

## Scope

Follow up the PR32 reviewer residual risk: recursive lineage is now collected,
but the UX still flattens branching or nested revision trees. Add parent/depth
visibility without changing strategy execution behavior.

## Steps

1. Add failing tests requiring lineage revision nodes with `parent_card_id` and
   `depth`.
2. Extend `StrategyLineageSummary` to include revision tree nodes while keeping
   existing summary fields.
3. Render `Revision Tree` rows in dashboard and operator console strategy
   surfaces.
4. Update README, PRD, architecture, plan, and review archive.
5. Run targeted and full verification gates.
6. Request independent reviewer subagent review before PR/merge.

## Acceptance Criteria

- A second-generation revision records depth `2` and its immediate parent.
- Dashboard and operator console display depth/parent rows for nested
  revisions.
- Existing flat counts and action/failure summaries remain available.
- No strategy mutation, promotion, execution, broker behavior, runtime artifact,
  or secret is introduced.
- Full gates and reviewer subagent pass.
