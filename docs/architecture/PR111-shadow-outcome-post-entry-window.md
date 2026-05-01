# PR111 Shadow Outcome Post-Entry Window

## Purpose

After PR110, the active replacement retest chain reached
`record_paper_shadow_outcome`. The newest leaderboard entry was created at
`2026-05-01T17:27:48Z`, but stored BTC-USD candles only covered through
`2026-05-01T09:00:00Z`.

Without an explicit guard, an operator or automation could pass an older
complete candle window and record it as if it were a fresh paper-shadow
observation for the new leaderboard candidate. That would leak pre-entry
information into the shadow outcome and make the retest chain look more
complete than it really is.

## Decision

Paper-shadow outcomes now require `window_start >= leaderboard_entry.created_at`.

The guard exists in two places:

- the revision retest executor checks before deriving returns from stored
  candles, so rejected derived windows do not write incidental backtest
  artifacts;
- the generic `record_paper_shadow_outcome` path checks the same invariant so
  direct CLI/API use cannot bypass it.

## Non-Goals

- Do not fabricate shadow returns.
- Do not infer a post-entry window when no candles exist after the leaderboard
  entry.
- Do not change completed historical shadow outcomes.
- Do not alter leaderboard scoring.

## Runtime Impact

For the active BTC-USD replacement retest, the correct next state remains
blocked until a complete candle window exists after
`leaderboard-entry:470e52be512676ef` was created. The chain should not use the
older `2026-04-29T10:00Z` to `2026-05-01T09:00Z` stored candle window for that
new entry.

## Verification

Regression coverage proves that:

- a pre-leaderboard derived candle window is rejected before derived backtest
  side effects are written;
- direct paper-shadow outcome recording rejects windows that start before the
  leaderboard entry;
- valid derived shadow windows use post-leaderboard candles;
- incomplete post-leaderboard candle windows still fail with the candle
  coverage error.

