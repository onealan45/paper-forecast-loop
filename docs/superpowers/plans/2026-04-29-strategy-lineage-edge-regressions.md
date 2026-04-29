# Plan: Strategy Lineage Edge Regressions

## Scope

Convert PR33 reviewer residual risks into committed regression tests for
strategy lineage edge cases.

## Steps

1. Add tests for branching revision trees, missing parents, and parent cycles.
2. Run the tests and fix production code only if a real edge bug is exposed.
3. Update README, PRD, architecture, and review archive.
4. Run full verification gates.
5. Request independent reviewer subagent review before PR/merge.

## Acceptance Criteria

- Branching revision trees have deterministic parent/depth order.
- Missing-parent lineage anchors to the current card and still includes known
  descendants.
- Parent cycles terminate safely and do not move the root anchor to another
  cycle member.
- Full gates pass.
- Reviewer subagent reports no blocking findings.
