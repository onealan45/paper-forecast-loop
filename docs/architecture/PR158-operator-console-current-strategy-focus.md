# PR158 Operator Console Current Strategy Focus

## Problem

The research operator console could mix three different strategy contexts in the
same action layer:

- the latest `strategy_research_digest` selected a new replacement strategy,
- the current strategy panel still used the latest autopilot-linked chain card,
- the lineage replacement panel could select the replacement card that just
  failed its latest shadow outcome instead of the newer replacement generated
  from that outcome.

This made the page look as if stale retest tasks were still the active next
research step, even when the current digest was waiting for a paper-shadow
window on a newer replacement card.

## Decision

The operator console now treats the latest strategy digest as the owner of the
current strategy slot when its referenced strategy card exists. The underlying
research chain and lineage summary are still used as historical evidence, but
the top-level current strategy display should follow the digest because the
digest is the newest synthesized research judgment.

The current next-action slot follows the same source. When the digest-selected
strategy card owns the current strategy slot, the action display uses
`StrategyResearchDigest.next_research_action` and the digest ID as its source.
The older autopilot-linked action remains historical evidence, not the active
operator instruction.

For lineage replacement selection, a replacement generated from
`task_plan.latest_outcome_id` is preferred over the outcome card itself. The
outcome card is only used as a fallback when no newer replacement exists for the
latest failed outcome.

Older revision candidates are hidden from the current-action panel when a newer
digest-selected strategy card exists. They remain visible through lineage
history, so auditability is preserved without making stale tasks look current.

## Acceptance

- Current strategy panel shows the digest-selected strategy card.
- Current next-action panel and overview preview use the digest action/source
  when the digest-selected card owns the current strategy.
- Lineage replacement panel shows the newest replacement generated from the
  latest failed replacement outcome.
- Stale revision candidate panels are suppressed when a newer digest-selected
  replacement owns the current action.
- Historical lineage still retains older revision/replacement IDs.
- Operator console tests cover all three behaviors.
