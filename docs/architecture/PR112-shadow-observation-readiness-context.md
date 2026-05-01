# PR112 Shadow Observation Readiness Context

## Problem

PR111 correctly blocks paper-shadow outcomes whose observation window starts
before the leaderboard entry exists. That prevents pre-entry candles or explicit
returns from being reused as if they were fresh shadow evidence.

After that fix, the active replacement retest chain could still look opaque: the
`record_paper_shadow_outcome` task was blocked, but the plan did not explain
whether the system had any post-entry candles yet.

## Decision

Revision retest planning now loads stored market candles for the requested
symbol and adds readiness context to the blocked paper-shadow task rationale:

- `earliest_window_start`: the leaderboard entry creation time, which is the
  first legal start for a paper-shadow observation window.
- `latest_stored_candle`: the newest stored candle for that symbol, or
  `missing` when no candles are present.

The planner remains read-only. It does not create candles, fabricate returns,
record a shadow outcome, or relax the PR111 post-entry enforcement.

## Active Storage Example

For the active BTC-USD CoinGecko storage, the current replacement retest chain
has:

- leaderboard entry: `leaderboard-entry:470e52be512676ef`
- earliest legal shadow window start: `2026-05-01T17:27:48.000589+00:00`
- latest stored candle: `2026-05-01T17:00:00+00:00`

Because the newest stored candle is still before the leaderboard entry, the
system should keep `record_paper_shadow_outcome` blocked with
`shadow_window_observation_required`.

## Acceptance

- A blocked paper-shadow task exposes both readiness timestamps.
- The readiness timestamps are informational only and do not make the task
  runnable.
- Existing explicit and candle-derived shadow outcome execution still rejects
  windows that begin before the leaderboard entry.
