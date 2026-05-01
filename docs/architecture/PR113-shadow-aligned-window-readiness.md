# PR113 Shadow Aligned Window Readiness

## Problem

PR112 made blocked paper-shadow tasks more transparent by showing the earliest
legal post-leaderboard window start and the latest stored candle. After a new
post-entry candle arrives, that still does not necessarily mean a
candle-derived shadow observation can be recorded.

The derived mode requires a complete candle boundary pair. With hourly provider
candles, a leaderboard entry can occur between candle boundaries, so the first
legal derived window may need to start at the first candle at or after the
leaderboard entry. A single post-entry candle is only a possible start; it is
not a complete observation window.

## Decision

Revision retest planning now adds three more read-only fields to the blocked
paper-shadow task rationale:

- `first_aligned_window_start`: first stored candle timestamp for the symbol at
  or after the leaderboard entry creation time.
- `next_required_window_end`: next stored candle timestamp after that aligned
  start, or `missing` when the end boundary is not yet present.
- `candidate_window_ready`: `true` only when both aligned start and end boundary
  candles are present.

This does not populate command args automatically and does not record a
paper-shadow outcome. The operator or automation still needs to execute the
explicit `record_paper_shadow_outcome` step with concrete window inputs, and the
executor still enforces PR111 post-entry window rules.

## Active Storage Example

For the active BTC-USD CoinGecko storage after the latest fetch:

- leaderboard entry: `leaderboard-entry:470e52be512676ef`
- earliest legal shadow window start: `2026-05-01T17:27:48.000589+00:00`
- latest stored candle: `2026-05-01T18:00:00+00:00`
- first aligned window start: `2026-05-01T18:00:00+00:00`
- next required window end: `missing`
- candidate window ready: `false`

The correct state is still blocked until another post-entry candle supplies a
complete candle boundary pair.

## Acceptance

- Blocked paper-shadow tasks expose aligned window readiness.
- A single post-entry candle is reported as `candidate_window_ready=false`.
- Two post-entry candle boundaries are reported as `candidate_window_ready=true`.
- The planner remains read-only and does not weaken shadow outcome execution
  gates.
