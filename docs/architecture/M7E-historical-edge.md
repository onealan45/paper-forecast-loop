# M7E Historical Edge

## Summary

M7E adds event-family historical edge evaluation. It reads:

- `canonical_events.jsonl`
- `market_reaction_checks.jsonl`
- `market_candles.jsonl`

and writes:

- `event_edge_evaluations.jsonl`

This stage checks whether an event family has positive after-cost forward return
in the available historical sample. It does not directly promote BUY/SELL and
does not integrate with M1 strategy decisions; that remains M7F.

## Implemented Scope

M7E adds:

- `forecast_loop.event_edge.build_event_edge_evaluations`
- `build-event-edge` CLI
- point-in-time filters for events, market reaction checks, and candle imports
- exact event and horizon candle boundary requirements
- forward return calculation
- benchmark return placeholder `0.0`
- after-cost excess return
- hit rate
- max adverse excursion summaries
- sample-size / after-cost / hit-rate blocking flags
- idempotent replacement for fixed evaluation id

## Point-In-Time Contract

`build_event_edge_evaluations` requires `--created-at`.

The engine only uses:

- canonical events with `available_at <= created_at`;
- canonical event snapshots whose `created_at <= created_at`;
- canonical events whose `fetched_at <= created_at`;
- market reaction checks with `created_at <= created_at`;
- only the latest market reaction check per event as of `created_at`;
- market reaction checks where `passed=true`;
- market candles whose `timestamp <= created_at`;
- market candles whose `imported_at <= created_at`.

This prevents historical edge samples from using labels or intermediate gates
that were not locally available at the build timestamp.

## Candle Boundary Rule

For each sample, M7E requires exact candles at:

- `event_timestamp_used`
- `event_timestamp_used + horizon_hours`

`event_timestamp_used` must already be an exact UTC hourly boundary. If the
market reaction timestamp is non-hourly, or if either candle boundary is
missing, the event is excluded from the edge sample. The engine does not floor a
non-hourly event timestamp or substitute older candles for missing horizon
labels.

## Passing Rules

An `EventEdgeEvaluation` passes only when all are true:

- `sample_n >= --min-sample-size`
- average after-cost excess return is positive
- hit rate is at least `0.5`

Blocking flags currently include:

- `insufficient_sample_size`
- `non_positive_after_cost_edge`
- `low_hit_rate`

## CLI

Build event-family historical edge evaluations:

```powershell
python .\run_forecast_loop.py build-event-edge --storage-dir .\paper_storage\m7-fixture --symbol BTC-USD --created-at 2026-04-28T12:00:00+00:00 --horizon-hours 24
```

`--created-at` is required so fixed reruns produce stable evaluation ids.

## Deferred Scope

M7E intentionally does not implement:

- richer benchmark suites;
- White's Reality Check or deflated Sharpe calculations beyond placeholders;
- walk-forward integration;
- feature snapshot generation from edge results;
- direct strategy decision integration;
- BUY/SELL promotion;
- live source fetching;
- broker/testnet/live order paths.

Those remain later Alpha Factory work, especially M7F decision integration and
the locked evaluation / leaderboard stages.

## Acceptance

M7E is complete when:

- positive after-cost event-family samples can pass;
- low sample size is blocked;
- failed market reaction checks are excluded;
- future reaction checks and future-imported candles are ignored;
- missing forward horizon labels are not silently substituted;
- `build-event-edge` is idempotent for fixed input and `created_at`;
- tests, compile checks, CLI help, diff check, smoke, and independent reviewer
  approval all pass.
