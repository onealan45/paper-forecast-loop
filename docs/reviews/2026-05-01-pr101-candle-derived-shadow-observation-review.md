# PR101 Candle-Derived Shadow Observation Review

## Scope

- Branch: `codex/pr101-shadow-observation-from-candles`
- Reviewer: subagent `Sartre`
- Review date: 2026-05-01
- Review type: final code, test, runtime-evidence, and repository-hygiene review

## Reviewed Changes

- Added `--derive-shadow-returns-from-candles` to
  `execute-revision-retest-next-task`.
- Added candle-derived paper-shadow observation behavior for explicit shadow
  windows.
- Added tests and docs for derived observations and incomplete window rejection.

## Initial Reviewer Result

CHANGES_REQUESTED

## Blocking Finding

- P1: Derived candle window accepted missing interior candles. The first
  implementation only verified that the first selected candle matched
  `window_start` and the last selected candle matched `window_end`. A window with
  start/end candles present but a missing intermediate expected timestamp could
  still run `run_backtest` and record a shadow observation from incomplete data.

## Required Fix

- Add a regression test where an explicit derived shadow window has start/end
  candles present but one interior expected candle is missing.
- Reject that window before recording a paper-shadow outcome.

## Fix Applied

- Added `test_execute_revision_retest_shadow_outcome_rejects_missing_interior_derived_candle`.
- `_derive_shadow_observation_from_stored_candles` now infers the candle cadence
  from stored same-symbol candles and requires every expected timestamp between
  `window_start` and `window_end` to exist.
- Incomplete boundary or interior coverage raises
  `revision_retest_shadow_window_candles_incomplete` before any paper-shadow
  outcome is written.

## Verification Evidence

- `python -m pytest tests\test_research_autopilot.py -q` -> `68 passed`
- `python -m pytest -q` -> `461 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> passed with CRLF warnings only
- Runtime smoke on active BTC-USD storage created
  `paper-shadow-outcome:4869dea3bf0fe39a` using
  `--derive-shadow-returns-from-candles`; the refreshed digest kept the revision
  strategy `BLOCKED` / `QUARANTINE`.

## Final Reviewer Result

APPROVED

The reviewer confirmed the P1 blocker was fixed and reported no blocking
findings on re-review.
