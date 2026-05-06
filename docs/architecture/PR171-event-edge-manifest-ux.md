# PR171: Event-Edge Manifest UX

## Context

PR170 made event-edge evaluations more traceable by recording input manifests,
but the operator-facing surfaces still only showed event-edge score metrics. A
human reviewing blocker evidence could see the sample size and after-cost edge,
but not the size of the underlying event/reaction/candle input set or its
freshness watermark.

## Decision

Dashboard and operator console now display an event-edge input summary wherever
decision-blocker event-edge evidence is rendered:

- event count
- reaction count
- candle count
- input watermark

The formatting is shared through `format_event_edge_input_manifest()` so the two
read-only UX surfaces stay consistent.

## Boundaries

- This does not change event-edge scoring or decision gates.
- This does not expose raw candle ids in the primary UX.
- This does not require legacy event-edge artifacts to have manifests; legacy
  artifacts simply omit the manifest summary.

## Verification

- Red/green UI tests:
  `python -m pytest tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary -q`
  `python -m pytest tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q`
- Focused suites:
  `python -m pytest tests\test_dashboard.py tests\test_operator_console.py -q`
  `python -m pytest tests\test_strategy_research_display.py -q`
- Full gate:
  `python -m pytest -q`
  `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  `git diff --check`
