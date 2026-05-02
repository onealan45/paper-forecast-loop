# PR143 Market-Derived Events

## Problem

After PR142, the active decision-blocker plan correctly refused to run
event-edge evaluation because active storage had candles but no canonical events
or market reaction checks. External source ingestion is useful, but it should
not be the only route to research evidence.

For strategy research, stored candles can also define deterministic market
events such as large hourly moves. Those events are not news. They are local,
auditable market-derived hypotheses that can be backtested by the existing
event-edge builder.

## Decision

Add `build-market-derived-events` and `market_derived_events.py`.

The builder:

- reads stored same-symbol market candles available by `created_at`;
- detects hourly moves whose absolute return is at least `min_abs_return`;
- requires an exact 24-hour forward candle before creating an event;
- writes a synthetic but auditable `SourceDocument` derived from the local
  candle artifact;
- writes a linked `CanonicalEvent` with event family
  `market_derived_move`;
- writes a passed `MarketReactionCheck` for that market-derived event;
- uses stable ids so repeated runs are idempotent.

## Scope

This PR does not fetch external data, scrape web sources, alter strategy cards,
run backtests, execute broker calls, or place orders. It only creates local
research evidence artifacts from existing candle data.

## Why This Is Valid For This Project

The project direction is research ability and prediction quality. Market-derived
events are not a substitute for macro/news/source ingestion, but they are a
valid event family for simulation: the system can ask whether a class of market
move has a repeatable forward edge after costs.

## Verification

Regression coverage proves:

- market-derived events create source document, canonical event, and market
  reaction artifacts;
- repeated runs are idempotent;
- moves without an exact forward horizon candle are ignored;
- decision-blocker event-edge planning becomes ready after market-derived
  events exist;
- the event-edge builder can create an evaluation from the generated artifacts;
- the CLI requires `--created-at` and returns JSON counts.
