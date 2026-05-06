# PR172: Event-Edge Manifest Health Gate

## Context

PR170 started recording event-edge input manifests, and PR171 made those
manifests visible in the dashboard and operator console. The remaining gap was
health-check traceability: an event-edge evaluation could still claim input
event, market-reaction, or candle ids that no longer existed in storage.

For research quality, this is not just an operations issue. If a strategy
decision cites an event-edge result, the underlying event/reaction/candle sample
must still be auditable.

## Decision

`health-check` now treats event-edge manifest references as first-class artifact
links:

- `input_event_ids` must exist in `canonical_events.jsonl`.
- `input_reaction_check_ids` must exist in `market_reaction_checks.jsonl`.
- `input_candle_ids` must exist in `market_candles.jsonl`.

Missing references create blocking, repair-required findings:

- `event_edge_missing_event`
- `event_edge_missing_market_reaction`
- `event_edge_missing_candle`

## Boundaries

- Legacy event-edge artifacts without manifests are still accepted.
- This does not change event-edge scoring, decision gating, or UX formatting.
- This does not require raw manifest ids to be displayed in the primary UX.

## Verification

Red/green test:

```powershell
python -m pytest tests\test_m7_evidence_artifacts.py -q
```

Full PR gate:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```
