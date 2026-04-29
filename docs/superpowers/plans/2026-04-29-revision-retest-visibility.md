# PR15 Revision Retest Visibility Plan

## Scope

Expose PR14 retest scaffolds in the read-only inspection surfaces.

PR14 creates a pending experiment trial for a DRAFT strategy revision candidate. PR15 makes that state visible so the user can see what the AI is preparing to retest and which evidence artifacts are still missing.

## Implementation

1. Extend `StrategyRevisionCandidate` with:
   - latest pending retest `ExperimentTrial`;
   - matching locked `SplitManifest` when available;
   - derived `retest_next_required_artifacts`.
2. Update dashboard snapshot and operator console snapshot to load/pass split manifests and retain retest fields.
3. Update dashboard `策略修正候選` block to show:
   - retest trial id/status/dataset;
   - locked split manifest if present;
   - next required artifacts.
4. Update operator console research/overview revision panel similarly.
5. Add regression tests for dashboard and operator console visibility.

## Boundaries

- Read-only UX only.
- No new artifacts are written.
- No fake evaluation, leaderboard, promotion, or order path.
- No browser automation required unless a later visual review is requested.

## Acceptance

- Dashboard and operator console show the pending retest scaffold when present.
- Existing revision-candidate visibility tests still pass.
- Full gates pass.
- Reviewer subagent approves and review is archived.
