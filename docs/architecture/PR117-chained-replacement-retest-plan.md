# PR117 Chained Replacement Retest Plan

## Problem

The lineage executor can draft a new replacement strategy after a replacement
strategy is itself quarantined. That is the expected self-evolution path:

`root lineage -> replacement -> replacement outcome -> next replacement`

However, the revision retest scaffold and task-plan validators only walked
`parent_card_id` links when deciding whether a source paper-shadow outcome
belonged to the replacement lineage. Replacement strategy cards intentionally
have `parent_card_id = null`, because they are not child revisions of the failed
rules. As a result, a second replacement could be drafted but could not start a
retest scaffold or plan.

## Decision

Replacement lineage membership now accepts either:

- a normal parent chain that reaches the root card id, or
- a replacement strategy card whose
  `replacement_source_lineage_root_card_id` matches the current replacement's
  root id.

The same rule is applied in:

- `create_revision_retest_scaffold`
- `revision-retest-plan`
- `health-check` research-autopilot agenda membership validation

This keeps scaffold and plan behavior aligned.

## Boundary

This does not weaken outcome gating. The source outcome must still:

- exist
- match the requested symbol
- belong to the same lineage root
- have a replacement-required action such as `QUARANTINE`

It also does not auto-promote or execute real orders.

## Acceptance

- First-generation replacement strategies can still start retest scaffolds.
- Replacement strategies created from prior replacement outcomes can start
  retest scaffolds and task plans.
- Replacement retest autopilot runs linked to a lineage agenda do not trigger a
  false `research_autopilot_run_agenda_strategy_card_mismatch` finding when the
  agenda contains the lineage root.
- Non-replacement source outcomes remain rejected.
- The existing retest protocol fields stay unchanged.
