# PR170 Event-Edge Input Manifest Review

## Scope

Branch: `codex/pr170-event-edge-input-manifest`

Reviewed changes:

- `src/forecast_loop/models.py`
- `src/forecast_loop/event_edge.py`
- `src/forecast_loop/decision_research_plan.py`
- `tests/test_event_edge.py`
- `tests/test_decision_research_plan.py`
- `docs/architecture/PR170-event-edge-input-manifest.md`

Goal: add an explicit input manifest to event-edge evaluations so
decision-blocker research can reuse event-edge evidence only when the exact
event/reaction/candle input set still matches current data.

## Review Method

Per repo rule, final review was performed by a subagent only. The controller did
not self-review.

Reviewer: `Newton`

## Findings And Resolution

First review result: `APPROVED`.

Reviewer residual risk: add committed tests for:

- manifest exactly matching current inputs can be reused;
- stale manifest watermark cannot be reused.

Resolution:

- Added `test_decision_blocker_research_plan_reuses_event_edge_when_manifest_matches`.
- Added `test_decision_blocker_research_plan_does_not_reuse_event_edge_when_manifest_watermark_is_stale`.
- Re-ran gates and requested follow-up review.

Final review result: `APPROVED`.

## Verification

Commands verified:

```powershell
python -m pytest tests\test_decision_research_plan.py -q
python -m pytest tests\test_event_edge.py -q
python -m pytest tests\test_decision_research_executor.py -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Results:

- Planner suite: `21 passed`
- Event-edge suite: `9 passed`
- Executor suite: `8 passed`
- Full test suite: `585 passed`
- Compileall: passed
- CLI help: passed
- Diff check: passed with CRLF warnings only

Active storage smoke:

```powershell
python .\run_forecast_loop.py decision-blocker-research-plan --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD --symbol BTC-USD
```

Result: latest blocker plan returned `next_task_id=null`; old active event-edge
artifact remains reusable through the legacy watermark fallback.

## Automation Impact

This improves research traceability and prevents manifested event-edge evidence
from being reused against a different event/reaction/candle input set. It does
not change event-edge scoring math, strategy decision gates, or execution
boundaries.
