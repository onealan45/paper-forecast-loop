# PR108 Retest Evidence Card Ownership

## Purpose

After PR107, active BTC-USD storage could finally create a replacement retest
scaffold for `strategy-card:98d8cf7e57414c4f`. The next runtime step exposed a
new evidence-chain bug: the retest planner selected old split-aligned
backtest and walk-forward artifacts from an earlier revision card because the
symbol and split window matched.

That allowed a replacement card to record a PASSED retest trial using evidence
that was generated before the replacement retest trial existed.

## Decision

Revision and replacement retest plans now require selected backtest and
walk-forward evidence to belong temporally to the current retest chain:

- fallback split-aligned evidence is eligible only when it was created at or
  after the current pending retest trial started;
- linked evidence on a PASSED retest trial is valid only when it was created at
  or after that trial started;
- stale PASSED trials that link pre-trial evidence are ignored by the planner.

This keeps the existing symbol/window checks but prevents newer strategy cards
from inheriting older strategy evidence.

## Non-Goals

- Do not rewrite existing runtime JSONL artifacts.
- Do not add new artifact schema fields in this PR.
- Do not change the backtest or walk-forward engines.
- Do not weaken split, baseline, leaderboard, or paper-shadow gates.

## Runtime Evidence

Active BTC-USD storage currently contains stale linked evidence from a manual
runtime attempt. With PR108 logic, the replacement retest plan ignores that
stale PASSED trial and reports:

- `passed_trial_id = null`
- `backtest_result_id = null`
- `walk_forward_validation_id = null`
- `next_task_id = run_backtest`

## Verification

Regression coverage proves that:

- a new retest card does not reuse preexisting split-aligned backtest and
  walk-forward evidence created before the pending retest trial;
- a PASSED retest trial linking pre-trial evidence is ignored and does not close
  the retest chain.
