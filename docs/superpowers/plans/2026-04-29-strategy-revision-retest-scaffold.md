# PR14 Strategy Revision Retest Scaffold Plan

## Scope

Move the PR12/PR13 self-evolving strategy flow from "visible DRAFT revision candidate" to "ready for a controlled retest".

This PR adds a scaffold only. It must not fabricate backtest, walk-forward, locked evaluation, leaderboard, or paper-shadow success artifacts.

## Implementation

1. Add a `revision_retest` module that:
   - accepts a DRAFT strategy revision card created from a failed paper-shadow outcome;
   - verifies the source outcome still exists and matches the card's symbol;
   - creates or returns one idempotent `PENDING` `ExperimentTrial`;
   - optionally locks split and cost protocol artifacts when explicit date ranges are provided;
   - returns next required artifacts so the next worker knows whether to build dataset/backtest/walk-forward evidence.
2. Add CLI command `create-revision-retest-scaffold`.
3. Add tests for:
   - scaffold creation from a valid revision card;
   - idempotency;
   - rejection of non-revision cards;
   - optional split/cost locking without creating locked evaluation results;
   - CLI JSON output and persistence.
4. Update README, PRD, and architecture docs with the new PR14 step.

## Boundaries

- No real orders or real capital.
- No fake evaluation result.
- No automatic promotion from DRAFT to ACTIVE.
- No runtime storage, reports, output screenshots, secrets, `.env`, or `.codex/` committed.

## Acceptance

- Targeted tests pass.
- Full test suite passes.
- `compileall`, `run_forecast_loop.py --help`, and `git diff --check` pass.
- A reviewer subagent approves or findings are fixed and archived under `docs/reviews/`.
