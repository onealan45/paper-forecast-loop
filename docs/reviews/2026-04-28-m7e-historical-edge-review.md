# M7E Historical Edge Review

## Summary

Review target: `codex/m7e-historical-edge`

Milestone: PR4 / M7E Historical Edge

Reviewer: independent Codex reviewer subagent `Kant`

Result: `APPROVED`

## Reviewed Scope

M7E adds:

- `forecast_loop.event_edge.build_event_edge_evaluations`
- `build-event-edge` CLI
- event-family historical edge evaluation from canonical events, market reaction
  checks, and stored candles
- point-in-time filters for events, reaction checks, candle timestamps, and
  candle import time
- exact event/horizon candle boundary handling
- after-cost excess return, hit rate, and adverse excursion summaries
- tests and architecture documentation

This review explicitly checked that the PR does not add M7F decision
integration, live fetching, secret handling, broker paths, or live order
submission.

## Review Findings And Resolution

Initial review found two blockers:

- `[P1] Latest failed reaction can be bypassed`
  - Issue: older passed `MarketReactionCheck` rows could enter the historical
    edge sample even when a newer check for the same event failed.
  - Fix: M7E now selects the latest reaction check per event as of `created_at`
    before requiring `passed=true`.
  - Regression: `test_build_event_edge_uses_latest_market_reaction_per_event`.

- `[P2] Non-hour events use floored candles as labels`
  - Issue: non-hour `event_timestamp_used` values were floored to the hourly
    boundary, contradicting the exact-label rule.
  - Fix: non-hour `event_timestamp_used` is excluded from the sample instead of
    being floored.
  - Regression: `test_build_event_edge_rejects_non_hour_event_timestamp_labels`.

Second-pass review result:

> APPROVED

The reviewer confirmed the previous P1/P2 were fixed and found no new blocking
finding.

## Reviewer Commands

The reviewer reported running:

```powershell
python -m pytest tests\test_event_edge.py -q
python -m pytest tests\test_event_edge.py tests\test_market_reaction.py tests\test_event_reliability.py tests\test_m7_evidence_artifacts.py -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
git diff --check
python .\run_forecast_loop.py --help
python .\run_forecast_loop.py build-event-edge --help
python .\run_forecast_loop.py build-event-edge --storage-dir . --created-at not-a-date
```

Reported results:

- `tests\test_event_edge.py`: `9 passed`
- M7 related tests: `28 passed`
- full pytest: `252 passed`
- compileall: passed
- diff check: passed with LF/CRLF warnings only
- CLI help: passed
- `build-event-edge --help`: passed
- malformed datetime: argparse error, no raw traceback
- latest-failed-reaction probe: `count=0`
- non-hour timestamp probe: `count=0`

## Merge Gate

M7E may proceed to PR/merge only if local and GitHub machine gates pass:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

M7E-specific smoke must also pass with a temporary storage directory containing
three passed market reaction samples and exact horizon candles.
