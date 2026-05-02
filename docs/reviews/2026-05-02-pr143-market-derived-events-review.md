# PR143 Market-Derived Events Review

## Reviewer

- Subagent: `019de769-9090-7522-9a80-f4f871387836`
- Role: final reviewer
- Scope: PR143 diff only

## Initial Result

`CHANGES_REQUESTED`

### P1 Finding

The first implementation wrote `forward_return_24h` into the synthetic
`SourceDocument.summary` and then copied that text into `CanonicalEvent.summary`.
Because the document and event were marked available at the event timestamp,
this exposed the future 24-hour label as decision-time text and created
lookahead leakage for downstream research, prompts, or feature builders.

Required fix:

- remove future-return labels from event-time source/canonical text, or
- mark the artifacts available only after the forward horizon and separate them
  from event-time features.

## Fix Applied

- Added regression coverage proving `SourceDocument.summary`,
  `SourceDocument.body_excerpt`, and `CanonicalEvent.summary` do not contain
  `forward_return_24h`.
- Removed `forward_return_24h` from market-derived event source text.
- Kept event-time text limited to hourly return, close, previous close, and
  volume.
- Left forward-return label calculation inside `build_event_edge_evaluations`,
  where it is derived from candles during evaluation.

## Final Result

`APPROVED`

Blocking findings: none.

Residual risks:

- `max_events=20` may bias large-history samples toward recent events unless
  the operator overrides it.
- Market-derived events are synthetic market events, not external news or macro
  sources. Docs describe this explicitly.

## Verification Observed

- `python -m pytest tests\test_market_derived_events.py tests\test_decision_research_plan.py tests\test_event_edge.py tests\test_m7_evidence_artifacts.py -q`
  -> `24 passed`
- `python -m pytest -q`
  -> `537 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  -> passed
- `python .\run_forecast_loop.py build-market-derived-events --help`
  -> passed
- `git diff --check`
  -> passed with LF/CRLF warnings only
