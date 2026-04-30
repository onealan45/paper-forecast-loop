# PR51 Replacement Retest Scaffold UX

Date: 2026-04-30

## Context

PR49 allowed lineage replacement strategy cards to enter the existing retest
scaffold, and PR50 let the retest executor create the pending scaffold. The UX
still stopped at showing the replacement hypothesis itself, so an operator could
not see whether the replacement strategy had actually entered the retest chain.

## Decision

Dashboard and operator console snapshots now expose replacement-retest state
separately from traditional revision-candidate state:

- latest lineage replacement strategy card;
- replacement retest task plan;
- latest replacement retest executor run.

The replacement strategy panel now shows:

- pending retest trial id;
- dataset id;
- scaffold task status;
- `lineage_replacement` retest kind;
- next retest task;
- latest executor run id/status.

This keeps replacement visibility close to the concrete strategy hypothesis
instead of burying it under the older revision-candidate panel.

## Non-Goals

- No retest execution behavior changes.
- No backtest, walk-forward, promotion, order, broker, sandbox, live trading, or
  real-capital path is added.
- No new replacement-only pipeline is introduced.

## Verification

- Added dashboard coverage for a replacement card that has been scaffolded by
  `execute_revision_retest_next_task`.
- Added operator console coverage for the same state.
- The tests assert the pending trial id, dataset id, `lineage_replacement`
  marker, and executor run visibility.
