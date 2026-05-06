# PR184: Dashboard Replay And Provider Symbol Time Selection

## Context

The dashboard active symbol now uses timestamp semantics, and major evidence
panels are symbol-scoped. Replay and provider panels still used JSONL tail
selection:

- a replay summary for another symbol could appear as the latest historical
  context;
- a stale provider run, or a provider run for another symbol, could dominate the
  provider health panel.

## Decision

Dashboard snapshot construction now selects:

- `latest_replay_summary` from summaries whose `forecast_ids` or
  `scored_forecast_ids` intersect the active symbol's forecast ids, then max
  `generated_at`;
- `latest_provider_run` from provider runs matching the active symbol, then max
  `created_at`.

If no active-symbol forecast ids exist, replay summary selection preserves the
legacy unscoped fallback because there is no reliable forecast-id mapping.
If active-symbol forecast ids exist but no replay summary references them, the
dashboard also falls back to the latest replay summary so historical replay
context can still render as stale background instead of disappearing. That
fallback is forced-stale and must not be labeled as aligned with current active
forecast evidence.

## Boundaries

- This only changes dashboard snapshot selection.
- It does not change replay generation, provider-run creation, storage schema,
  or health-check behavior.
- Provider runs remain symbol-scoped. Broker/execution/fill display selection
  is handled separately.

## Verification

```powershell
python -m pytest tests\test_dashboard.py::test_dashboard_unmatched_replay_fallback_is_marked_historical -q
python -m pytest tests\test_dashboard.py::test_render_dashboard_includes_latest_artifacts tests\test_dashboard.py::test_dashboard_latest_forecast_uses_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_replay_summary_is_scoped_to_active_forecast_and_generated_at tests\test_dashboard.py::test_dashboard_provider_run_is_scoped_to_symbol_and_created_at tests\test_dashboard.py::test_dashboard_unmatched_replay_fallback_is_marked_historical -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```
