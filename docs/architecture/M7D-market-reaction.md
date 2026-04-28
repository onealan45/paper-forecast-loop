# M7D Market Reaction

## Summary

M7D adds the already-priced / market reaction gate for M7 canonical event
snapshots. It reads:

- `canonical_events.jsonl`
- `event_reliability_checks.jsonl`
- `market_candles.jsonl`

and writes:

- `market_reaction_checks.jsonl`

This stage asks whether a reliable event appears to have already moved price
before the local build timestamp. It is a research gate, not a trading signal by
itself.

## Implemented Scope

M7D adds:

- `forecast_loop.market_reaction.build_market_reactions`
- `build-market-reactions` CLI
- point-in-time candle filtering
- point-in-time reliability-check filtering
- exact hourly boundary returns
- pre-event 1h / 4h / 24h return fields when coverage exists
- post-event 1h return when point-in-time data exists
- volume shock z-score placeholder
- pre-event drift z-score placeholder
- already-priced blocking by pre-event 4h return threshold or volume shock
- idempotent replacement for fixed `event_id + created_at` checks

## Point-In-Time Contract

`build_market_reactions` requires `--created-at`.

The engine only uses:

- canonical events with `available_at <= created_at`;
- canonical event snapshots whose `created_at <= created_at`;
- canonical events whose `fetched_at <= created_at`;
- event reliability checks whose `created_at <= created_at`;
- market candles whose `timestamp <= created_at`;
- market candles whose `imported_at <= created_at`.

This prevents replay/backtest lookahead from candles or reliability checks that
were not yet available to the local system at the build timestamp.

## Candle Boundary Rule

Market reaction calculations use exact hourly candle boundaries.

For an event timestamp, the engine floors the timestamp to the UTC hourly
boundary and requires exact candle rows for the measured return windows. If the
4h pre-event boundary is missing, the check is blocked with:

- `insufficient_pre_event_coverage`

The engine does not silently substitute an older candle for a missing boundary.

## Blocking Semantics

A `MarketReactionCheck` is blocked when:

- no passed reliability check exists for the event snapshot;
- pre-event 4h coverage is missing;
- absolute pre-event 4h return exceeds `--already-priced-return-threshold`;
- volume shock z-score exceeds `--volume-shock-z-threshold`.

Blocking flags currently include:

- `event_reliability_not_passed`
- `insufficient_pre_event_coverage`
- `already_priced`

## CLI

Build market reaction checks:

```powershell
python .\run_forecast_loop.py build-market-reactions --storage-dir .\paper_storage\m7-fixture --symbol BTC-USD --created-at 2026-04-28T12:00:00+00:00
```

`--created-at` is required so reruns are deterministic and do not create a new
check id by accident.

## Deferred Scope

M7D intentionally does not implement:

- event-family historical edge evaluation;
- feature snapshot generation from market reactions;
- direct strategy decision integration;
- BUY/SELL promotion;
- live source fetching;
- broker/testnet/live order paths.

Those remain M7E and M7F work under the master decision sequence.

## Acceptance

M7D is complete when:

- reliable events with stable pre-event prices pass market reaction checks;
- already-priced events are blocked;
- unreliable events are blocked before price gates;
- future-imported candles and future reliability checks are ignored;
- missing pre-event boundaries do not silently use stale candles;
- `build-market-reactions` is idempotent for fixed input and `created_at`;
- tests, compile checks, CLI help, diff check, M7D smoke, and independent
  reviewer approval all pass.
