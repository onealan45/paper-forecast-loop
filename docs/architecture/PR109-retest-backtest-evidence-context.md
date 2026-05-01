# PR109 Retest Backtest Evidence Context

## Purpose

PR108 prevented stale pre-trial backtest and walk-forward artifacts from
closing newer revision or replacement retest chains. Active BTC-USD runtime
then exposed the next blocker: executing `run_backtest` for the replacement
retest returned the old generic same-window `backtest_result_id`.

The generic backtest engine builds deterministic IDs from the symbol, window,
strategy parameters, candles, and simulated result. That is correct for generic
research runs, but it means a retest executor cannot create fresh chain-local
evidence if an older generic artifact already exists for the same window.

## Decision

Backtest and walk-forward engines now accept an optional `id_context`.

The generic CLI path leaves `id_context` unset, preserving existing generic
artifact identity. The revision/replacement retest executor passes a context
derived from:

- strategy card id;
- current retest trial id;
- source paper-shadow outcome id.

This makes executor-created retest evidence distinct from generic same-window
research artifacts while keeping the artifact schema unchanged.

## Non-Goals

- Do not change generic CLI backtest identity.
- Do not rewrite existing runtime artifacts.
- Do not add new artifact schema fields in this PR.
- Do not weaken split, baseline, leaderboard, or paper-shadow gates.

## Runtime Evidence

Before PR109, active replacement retest execution returned the old
`backtest-result:540075f557412322` and the plan stayed on `run_backtest`.

With PR109 logic, the same active replacement retest creates
`backtest-result:1910f46757fd4133` and the task plan advances to
`run_walk_forward`.

## Verification

Regression coverage proves that:

- `execute_revision_retest_next_task` writes a retest-specific backtest result
  when a generic same-window backtest result already exists;
- `execute_revision_retest_next_task` writes a retest-specific walk-forward
  validation when a generic same-window walk-forward validation already exists.
