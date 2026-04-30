# PR56 Lineage Replacement Next Step

Date: 2026-04-30

## Context

PR54 and PR55 make replacement retest outcomes visible in lineage accounting and
operator UX. The next operational gap was the follow-up task prompt. When a
replacement retest improves the lineage, the plan correctly routes to
cross-sample validation, but the worker prompt previously only said that the
lineage was improving. It did not identify which replacement hypothesis
generated the improvement.

For a research-first strategy loop, the next task must keep the hypothesis,
evidence, and validation target explicit.

## Decision

`lineage-research-plan` now carries latest replacement context into
`verify_cross_sample_persistence` when the latest improving evidence came from a
replacement node.

The replacement context is emitted only when the replacement node's latest
outcome id exactly matches the lineage `latest_outcome_id` and the latest
lineage change label is `改善`. Older replacement evidence is not reused to
describe a newer root or revision outcome, and unknown replacement outcomes do
not get described as improvements.

The task prompt now names:

- replacement strategy card id
- latest replacement outcome id
- latest replacement excess return after costs
- original source outcome id

The task rationale also states that cross-sample validation should test the
replacement hypothesis directly.

## Non-Goals

- No promotion rule is changed.
- No strategy generation rule is changed.
- No order, broker, sandbox, live execution, or real-capital path is added.

## Verification

- Added regression coverage where a replacement retest improves the lineage and
  the next task prompt must name the replacement card, latest outcome, and
  excess return.
- Added regression coverage where an older replacement outcome exists but a
  newer root outcome is latest; replacement-specific prompt/rationale must not
  be emitted.
- Added regression coverage where the latest replacement outcome has unknown
  excess; replacement-specific prompt/rationale must not claim improvement.
- Verified existing improving-lineage routing still returns
  `verify_cross_sample_persistence`.
