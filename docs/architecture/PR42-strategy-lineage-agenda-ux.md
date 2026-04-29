# PR42 Strategy Lineage Agenda UX

## Purpose

PR42 makes lineage-derived research agendas visible in the read-only strategy
surfaces.

PR41 can persist the latest lineage `next_research_focus` as a
`strategy_lineage_research_agenda`. Without PR42, that artifact is present in
JSONL but easy to miss because the strategy resolver may still show the normal
autopilot agenda as the latest research chain agenda.

## Design

Dashboard and operator console snapshots now track:

- normal `latest_research_agenda`
- separate `latest_lineage_research_agenda`

The lineage agenda is selected from symbol-scoped agendas where:

- `decision_basis == "strategy_lineage_research_agenda"`
- the agenda references the current lineage root or revision card IDs when a
  lineage summary exists

This avoids replacing the normal research chain while still making the
self-evolution agenda visible.

## UX

Dashboard and operator console research pages now render a dedicated:

```text
Lineage 研究 agenda
```

block with:

- agenda ID
- priority
- decision basis
- hypothesis
- acceptance criteria

## Non-Goals

PR42 does not:

- create a research agenda
- change lineage scoring
- change strategy decisions
- mutate strategy cards
- submit any paper, sandbox, or live order

## Verification

Tests cover dashboard and operator console rendering of a lineage-derived
agenda next to a multi-generation lineage summary.
