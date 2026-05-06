# PR180: Dashboard Baseline Symbol And Created Time Selection

## Context

PR179 made the dashboard strategy decision selector use the dashboard symbol and
max `created_at`. The adjacent prediction-quality panel still selected the
latest baseline evaluation by JSONL tail. In multi-symbol storage, or when an
older baseline row is appended after the current one, the dashboard could show a
strategy decision for one symbol next to baseline quality evidence from another
symbol or from stale evidence.

## Decision

Dashboard snapshot construction now filters baseline evaluations to the
dashboard symbol first, then selects `latest_baseline_evaluation` by max
`created_at`.

This keeps the strategy decision and "prediction quality vs baseline" panel on
the same symbol and prevents stale file-tail rows from replacing the current
quality evidence.

## Boundaries

- This only changes dashboard baseline evaluation selection.
- It does not change baseline generation, decision gating, health-check logic,
  or storage schema.
- It does not infer whether the baseline belongs to the selected decision's
  exact evidence chain; it only prevents stale-tail and cross-symbol display
  mistakes.

## Verification

```powershell
python -m pytest tests\test_dashboard.py::test_dashboard_baseline_evaluation_uses_latest_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_baseline_evaluation_is_scoped_to_dashboard_symbol -q
python -m pytest tests\test_dashboard.py::test_dashboard_prioritizes_strategy_decision_and_health_status tests\test_dashboard.py::test_dashboard_strategy_decision_uses_latest_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_strategy_decision_is_scoped_to_dashboard_symbol tests\test_dashboard.py::test_dashboard_baseline_evaluation_uses_latest_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_baseline_evaluation_is_scoped_to_dashboard_symbol tests\test_dashboard.py::test_dashboard_uses_specific_blocked_decision_reason_summary tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

