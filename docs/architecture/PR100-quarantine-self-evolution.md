# PR100 Quarantine Self-Evolution Bridge

## Purpose

PR99 produced the first active BTC-USD strategy research seed and correctly
blocked it: the candidate did not beat the active baseline and the paper-shadow
outcome recommended `QUARANTINE`.

That exposed a loop gap. `record-paper-shadow-outcome` can produce
`recommended_strategy_action = QUARANTINE`, but `propose-strategy-revision`
previously rejected that action. The weakest strategies therefore stopped at an
audit label instead of entering the self-evolution loop.

## Decision

`QUARANTINE` is now treated as a revision-required action for strategy
evolution. This does not promote or reactivate the strategy. It only permits a
DRAFT child strategy card and retest agenda to be created from the quarantined
paper-shadow outcome.

## Behavior

- `PROMOTION_READY` outcomes still cannot create revisions.
- `RETIRE`, `REVISE`, `REVISE_STRATEGY`, and `QUARANTINE` can create DRAFT
  revision candidates.
- Revision cards remain DRAFT and must pass locked retest, leaderboard gate, and
  a later paper-shadow cycle before any later promotion workflow may trust them.
- Existing lineage replacement behavior for `QUARANTINE_STRATEGY` is unchanged.
- Revision retest planning now requires the selected walk-forward validation to
  include the selected backtest result id before marking `run_walk_forward`
  completed. Matching only by time window is not enough.
- The revision retest executor links the selected holdout backtest into the
  generated walk-forward validation artifact when the walk-forward engine's
  internal rolling windows do not naturally include that longer holdout result.

## Why This Matters

The project direction is research-first and prediction-first. A poor strategy
should not merely be labeled as bad; it should create a concrete next hypothesis
that can be tested, rejected, or improved. This bridge keeps the loop moving
from failed evidence into the next research artifact without weakening gates.
The linked backtest/walk-forward guard also keeps the self-evolution executor
from skipping a required retest step and then blocking later on inconsistent
evidence pairs.
