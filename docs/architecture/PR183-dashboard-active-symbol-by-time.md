# PR183: Dashboard Active Symbol By Time

## Context

PR179 through PR182 aligned many dashboard evidence panels to the active
dashboard symbol and artifact timestamps. The active symbol itself still came
from `forecasts[-1]`, and the no-forecast fallback came from
`strategy_decisions[-1]`.

That left a root stale-tail risk: an older forecast or decision appended at the
end of JSONL could choose the dashboard symbol and cause every symbol-scoped
panel to align to the wrong asset.

## Decision

Dashboard snapshot construction now selects:

- `latest_forecast` by max `created_at`;
- the no-forecast symbol fallback from the max-`created_at` strategy decision.

The downstream symbol-scoped selectors added in PR179 through PR182 then use
that time-selected active symbol.

## Boundaries

- This only changes dashboard snapshot selection.
- It does not change forecast generation, storage ordering, health-check
  semantics, replay summaries, or operator-console behavior.
- Equal `created_at` tie behavior remains unspecified and should not be used as
  an ordering contract.

## Verification

```powershell
python -m pytest tests\test_dashboard.py::test_dashboard_latest_forecast_uses_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_symbol_fallback_uses_latest_decision_created_at_not_file_tail -q
python -m pytest tests\test_dashboard.py::test_dashboard_latest_forecast_uses_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_symbol_fallback_uses_latest_decision_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_strategy_decision_is_scoped_to_dashboard_symbol tests\test_dashboard.py::test_dashboard_review_score_and_proposal_are_scoped_to_dashboard_symbol tests\test_dashboard.py::test_dashboard_baseline_evaluation_is_scoped_to_dashboard_symbol tests\test_dashboard.py::test_dashboard_risk_snapshot_is_scoped_to_symbol_and_created_at -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

