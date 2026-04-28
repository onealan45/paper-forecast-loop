# PR13 Strategy Revision Visibility

## Status

Implemented after PR12 Strategy Revision Candidates.

PR13 does not create a new strategy mutation engine. It makes the existing PR12
DRAFT revision artifacts visible in the operator UX.

## Purpose

The user wants the project to emphasize research strength, prediction strength,
and self-evolving strategy reflection. PR12 creates a DRAFT child strategy card
and retest agenda from a failed paper-shadow outcome. Without PR13, those
artifacts can exist but remain easy to miss because the existing UX focuses on
the latest autopilot chain.

PR13 separates two concepts:

- current strategy research chain: the parent strategy, locked evaluation,
  leaderboard, paper-shadow outcome, and autopilot next action;
- latest DRAFT revision candidate: the concrete strategy mutation that should
  be retested next.

## Resolver Behavior

`forecast_loop.strategy_research.resolve_latest_strategy_research_chain` now
also resolves a `StrategyRevisionCandidate`.

A revision candidate is selected when a `StrategyCard` matches:

- `status == "DRAFT"`
- `decision_basis == "paper_shadow_strategy_revision_candidate"`
- `parameters.revision_source_outcome_id` exists
- requested symbol is in `symbols`

The resolver links:

- source outcome by `revision_source_outcome_id`;
- latest revision agenda where the revision card id is in `strategy_card_ids`
  and `decision_basis == "paper_shadow_strategy_revision_agenda"`.

This lets the UI show a revision candidate even when the latest autopilot run
still points to the parent strategy chain.

## UX Behavior

Dashboard:

- `策略研究焦點` now includes a `策略修正候選` block.
- The block shows revision card id, DRAFT status, parent strategy id, source
  failed paper-shadow outcome, failure attribution, mutation rules, and retest
  agenda.

Operator console:

- Research page shows the same revision candidate details.
- Overview page preview includes the latest revision candidate so the first
  screen shows what the system is trying to fix next.

## Boundaries

PR13 does not:

- run the retest;
- promote the revision;
- mutate an existing ACTIVE strategy card;
- add a scheduler;
- add model training;
- add any execution or order path.

It is purely visibility over existing research artifacts.

## Acceptance

PR13 is complete when:

- dashboard tests prove revision candidates are visible even when autopilot
  points to the parent strategy chain;
- operator console tests prove research and overview pages show the revision;
- standard gates pass;
- independent reviewer subagent approves;
- review is archived under `docs/reviews/`.
