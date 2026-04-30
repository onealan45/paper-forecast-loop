# PR48 Lineage Replacement Strategy UX

## Purpose

PR47 can create a DRAFT replacement strategy card for a quarantined lineage.
PR48 makes that concrete strategy hypothesis visible in the dashboard and local
operator console, so the research UX shows the actual new idea rather than only
the task status.

## Selection

Both UX snapshots now expose:

```text
latest_lineage_replacement_strategy_card
```

The selected card must:

- use `decision_basis = lineage_replacement_strategy_hypothesis`;
- match the current lineage task plan's `latest_outcome_id` through
  `parameters.replacement_source_outcome_id`;
- match the current lineage task plan's root strategy through
  `parameters.replacement_source_lineage_root_card_id`.

This avoids showing an unrelated replacement card from another lineage or an
older outcome.

## UI

Dashboard and operator console render:

- replacement card id and status;
- decision basis;
- source lineage root;
- source paper-shadow outcome;
- failure attributions;
- replacement hypothesis;
- signal description;
- entry, exit, and risk rules;
- parameters.

The panel is read-only. It does not run the strategy, evaluate it, promote it,
or create orders.

## Non-Goals

PR48 does not:

- create replacement strategy cards;
- execute lineage tasks;
- run backtests or walk-forward validation;
- create paper, sandbox, broker, or live orders;
- promote a strategy.

## Verification

Tests cover dashboard and operator console visibility after
`execute_lineage_research_next_task` creates a replacement strategy card.
