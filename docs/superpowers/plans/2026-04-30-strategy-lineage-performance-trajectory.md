# Plan: Strategy Lineage Performance Trajectory

## Scope

Expose whether strategy revisions are improving or worsening paper-shadow
evidence. Keep the change read-only and based on existing `PaperShadowOutcome`
artifacts.

## Steps

1. Add failing tests for lineage outcome trajectory nodes and UX rendering.
2. Add `StrategyLineageOutcomeNode` and delta/change-label calculation.
3. Render `表現軌跡` in dashboard and operator console strategy surfaces.
4. Update README, PRD, architecture, and review archive.
5. Run full verification gates.
6. Request independent reviewer subagent review before PR/merge.

## Acceptance Criteria

- Each lineage outcome shows outcome id, strategy card id, excess return,
  delta versus the previous known excess, change label, action, and failure
  attributions.
- Dashboard and operator console expose the trajectory.
- Existing lineage structure, change summary, edge-case, and escaping tests keep
  passing.
- No strategy mutation, promotion, execution, broker behavior, runtime artifact,
  or secret is introduced.
- Full gates and reviewer subagent pass.
