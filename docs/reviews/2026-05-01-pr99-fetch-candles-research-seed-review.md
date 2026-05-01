# PR99 Fetch Candles Research Seed Review

## Scope

- Branch: `codex/pr99-fetch-candles-research-seed`
- Reviewer: subagent `Ptolemy`
- Review date: 2026-05-01
- Review type: final code and artifact-integrity review

## Reviewed Changes

- Added `fetch-candles` CLI for provider-to-`market_candles.jsonl` research seeding.
- Added `CandleFetchResult` and `fetch_market_candles`.
- Added tests for provider candle fetch, dedupe, and provider audit recording.
- Updated README and M3C architecture docs to document `fetch-candles` and preserve the deterministic replay distinction.
- Reviewed the active BTC-USD runtime research seed flow:
  - CoinGecko candles fetched and stored.
  - Candle health passed.
  - Backtest and walk-forward evidence recorded.
  - Strategy card, locked evaluation, leaderboard entry, and paper-shadow outcome recorded.
  - Latest decision remained blocked from BUY/SELL because model evidence did not beat baseline.

## Verification Evidence

- `python -m pytest tests\test_candle_store.py -q` -> `9 passed`
- `python -m pytest -q` -> `455 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed and listed `fetch-candles`
- `git diff --check` -> passed with CRLF warnings only
- Active storage health-check after dataset-link repair -> healthy
- Latest decision after repair -> `HOLD`, `blocked_reason=model_not_beating_baseline`

## Reviewer Result

APPROVED

The reviewer reported no blocking correctness, test coverage, artifact integrity, or docs mismatch finding.

## Reviewer Notes

- `fetch-candles` does not re-enable `replay-range --provider coingecko`; replay choices remain `stored` and `sample`.
- Provider snapshots become deterministic only after they are persisted as stored artifacts.
- Active storage evidence is intentionally blocked/quarantined, not promoted.

## Residual Risks

- Dedupe uses `symbol + timestamp + source`; changing `--source` can store multiple rows for the same timestamp, which must remain guarded by `candle-health`.
- The runtime dataset pointer `market-candles:BTC-USD:coingecko-runtime-seed-20260501` is a 0-row provenance pointer for stored candles, not a full typed research dataset.
- The current evidence is weak: baseline edge is negative, holdout excess is negative, and walk-forward has overfit flags.

## Outcome

No blocking finding. PR99 may be pushed as a draft PR after the final local gate passes.
