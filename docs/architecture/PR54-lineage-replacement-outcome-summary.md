# PR54 Lineage Replacement Outcome Summary

Date: 2026-04-30

## Context

Replacement strategy cards are intentionally not child revisions. They point
back to a quarantined source lineage through:

- `decision_basis = lineage_replacement_strategy_hypothesis`;
- `parameters.replacement_source_lineage_root_card_id`;
- `parameters.replacement_source_outcome_id`.

After PR52 and PR53, replacement retest completion can be recorded and shown in
the UX. The remaining gap was lineage verdict continuity: the source lineage
summary counted only root and child-revision outcomes, so replacement retest
outcomes did not update the original lineage verdict.

## Decision

`build_strategy_lineage_summary` now includes paper-shadow outcomes from
replacement cards whose `replacement_source_lineage_root_card_id` matches the
source root card.

It also resolves a replacement card back to its source root when the replacement
card is supplied as the current card.

Dashboard and operator-console snapshots preserve replacement-card identity even
after the lineage latest outcome becomes the replacement retest outcome. They
first resolve the latest outcome's `strategy_card_id` when it points to a
root-linked replacement card, then fall back to the original
`replacement_source_outcome_id` lookup for pre-retest replacement hypotheses.

This means the source lineage summary can reflect:

- replacement outcome count;
- latest outcome id;
- action counts;
- best/worst excess return;
- improvement/worsening counts;
- next research focus.

## Non-Goals

- Replacement cards are not converted into child revisions.
- No strategy promotion, execution, paper order, broker, sandbox, live trading,
  or real-capital path is added.
- No new artifact schema is added.

## Verification

- Added coverage that a source lineage summary includes root-linked replacement
  outcomes.
- Added coverage that a replacement card resolves back to its source root when
  passed as the current card.
- Added dashboard and operator-console coverage that replacement panels remain
  visible after a replacement paper-shadow outcome becomes the lineage latest
  outcome.
- Existing lineage and replacement UX tests continue to pass.
