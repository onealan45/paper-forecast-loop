# PR102 Cross-Sample Targets Latest Strategy Card

## Purpose

PR101 let a revised strategy close its shadow observation from stored candles.
The active BTC lineage then moved to an improving but still quarantined
revision. The follow-up `verify_cross_sample_persistence` handoff created a
cross-sample agenda, but that agenda named only the root strategy card. That
would send downstream research to validate the stale root instead of the latest
strategy card that actually produced the improvement.

## Decision

`execute-lineage-research-next-task` now builds cross-sample validation agenda
strategy targets from the latest lineage outcome:

- always include the lineage root card;
- include the latest outcome card when it belongs to the root revision tree;
- keep including lineage replacement cards via their explicit root link;
- reject unrelated latest cards by leaving the agenda root-only.

`lineage-research-plan` also validates existing cross-sample agendas against
those expected target ids. A stale root-only agenda for a latest revision or
replacement outcome no longer marks `verify_cross_sample_persistence` complete;
the executor can create a corrected agenda that names the current target card.

The cross-sample agenda hypothesis now also names the target strategy cards, so
research workers can read the intended validation target without opening raw
JSON.

## Non-Goals

- Do not promote the latest revision.
- Do not weaken locked evaluation, leaderboard, or paper-shadow gates.
- Do not execute the blocked cross-sample autopilot run automatically.

## Verification

Added regression coverage proving an improving DRAFT revision creates a
`lineage_cross_sample_validation_agenda` with both root and latest revision
card ids. Additional coverage proves stale root-only agendas are ignored for
latest revision outcomes, and corrupted/fake latest outcome references do not
pull unrelated cards into the target list. Existing replacement cross-sample
behavior remains covered.
