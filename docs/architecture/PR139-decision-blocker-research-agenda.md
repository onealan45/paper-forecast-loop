# PR139 Decision Blocker Research Agenda

## Problem

PR137 made strategy decisions name their main research blockers and PR138
carried those blockers into the strategy research digest. The loop still needed
one more handoff step: turning the visible blocker list into an explicit
research agenda artifact.

Without that artifact, the next research worker can read the blocker text but
does not get a persisted task that says which evidence should be produced next.

## Decision

Add `create-decision-blocker-research-agenda`.

The command reads the latest same-symbol `StrategyDecision`, extracts the
`主要研究阻擋：...` list from `reason_summary`, and writes an idempotent
`ResearchAgenda` with:

- `decision_basis = decision_blocker_research_agenda`
- the latest decision id in the hypothesis
- expected artifacts derived from blocker labels, such as
  `event_edge_evaluation`, `backtest_result`, `walk_forward_validation`, or
  `baseline_evaluation`
- acceptance criteria requiring fresh evidence and updated decisions before
  BUY/SELL directionality is treated as usable

`run-once --also-decide` now attempts the same agenda creation after decision
generation. If the latest decision has no research blocker summary, the
automation run records a skipped step rather than failing the cycle.

## Scope

This PR creates research handoff artifacts only. It does not loosen decision
gates, create BUY/SELL recommendations, execute trades, mutate strategy cards,
or change broker behavior.

## Verification

Regression coverage proves:

- the CLI persists an idempotent same-symbol blocker agenda from the latest
  decision;
- unrelated-symbol and older decisions are ignored;
- missing blocker summaries return an operator-friendly CLI error;
- `run-once --also-decide` exposes the agenda id field and records a skipped
  step when no blocker agenda is available.
