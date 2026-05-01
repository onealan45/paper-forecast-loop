# PR118 Market Candle Timestamp Integrity

## Problem

`MarketCandleRecord.build_id` includes `source`, so the same
`symbol + timestamp` can be written twice when a seeded historical candle and a
later provider refresh overlap. `candle-health` already treats that as a
blocking duplicate timestamp, but `health-check` only checked duplicate
`candle_id` values and therefore missed the active corruption mode.

The active BTC-USD storage exposed this issue after a CoinGecko refresh:

- seed rows used source `coingecko-runtime-seed-20260501`
- refreshed rows used source `provider-runtime`
- overlapping hourly timestamps produced different `candle_id` values

## Decision

Market-candle ingestion now treats `symbol + timestamp` as the canonical
dedupe boundary:

- `import-candles` skips rows when the same symbol/timestamp already exists,
  even if the source differs
- `fetch-candles` applies the same source-agnostic boundary check
- `health-check` emits blocking `duplicate_candle_timestamp` findings for any
  existing duplicate symbol/timestamp rows

This keeps source metadata useful without allowing multiple canonical candles
for the same observed market boundary.

## Runtime Repair

The active BTC-USD storage was repaired by backing up the original
`market_candles.jsonl` under `paper_storage/.../quarantine/` and keeping the
first row per `symbol + timestamp`. No committed files include runtime storage.

## Boundary

This does not change candle IDs for existing rows. It prevents future duplicate
timestamp writes and makes already-corrupted stores fail health-check until
repaired.

## Acceptance

- Importing the same timestamps from a different source skips duplicates.
- Fetching the same timestamps from a different source skips duplicates.
- Health-check catches duplicate market-candle timestamps.
- Active BTC-USD storage reports healthy candle coverage after repair.
