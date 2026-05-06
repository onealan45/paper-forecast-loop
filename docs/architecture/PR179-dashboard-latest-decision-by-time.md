# PR179: Dashboard Latest Strategy Decision By Created Time

## Context

The operator console selects the latest strategy decision by `created_at`, but
the dashboard still used the last JSONL row. If an older decision was appended
after a current decision, the dashboard could show a stale action and reason
summary on the most important strategy panel.

## Decision

Dashboard snapshot construction now filters strategy decisions to the dashboard
symbol first, then selects `latest_strategy_decision` by max `created_at`. This
matches the operator console convention and avoids cross-symbol decisions
appearing in multi-asset storage.

## Boundaries

- This only changes dashboard strategy decision selection.
- It does not change decision generation, health-check behavior, or other
  dashboard latest fields.
- This does not infer the matching baseline/review chain; it only prevents an
  older appended decision from replacing the current strategy decision.

## Verification

```powershell
python -m pytest tests\test_dashboard.py::test_dashboard_strategy_decision_uses_latest_created_at_not_file_tail -q
python -m pytest tests\test_dashboard.py::test_dashboard_strategy_decision_uses_latest_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_strategy_decision_is_scoped_to_dashboard_symbol -q
python -m pytest tests\test_dashboard.py::test_dashboard_prioritizes_strategy_decision_and_health_status tests\test_dashboard.py::test_dashboard_strategy_decision_uses_latest_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_strategy_decision_is_scoped_to_dashboard_symbol tests\test_dashboard.py::test_dashboard_uses_specific_blocked_decision_reason_summary tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```
