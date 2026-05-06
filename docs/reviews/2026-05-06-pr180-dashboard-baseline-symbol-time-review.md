# PR180 Dashboard Baseline Symbol And Time Review

## Scope

Review target: `codex/pr180-dashboard-baseline-symbol-time`.

This review covers the dashboard baseline evaluation selector and its
regression tests. The intent is to keep the dashboard's prediction-quality
panel aligned with the active dashboard symbol and to prevent stale JSONL tail
rows from replacing the current baseline evidence.

## Reviewer

Final reviewer: Schrodinger.

Verdict: `APPROVED`.

## Findings

No blocker or important findings.

The reviewer confirmed that `build_dashboard_snapshot()` filters baseline
evaluations by `dashboard_symbol` before selecting the max `created_at`.

## Evidence Reviewed

The reviewer inspected:

- `src/forecast_loop/dashboard.py`
- `tests/test_dashboard.py`
- `docs/architecture/PR180-dashboard-baseline-symbol-time.md`

The reviewer reran:

```powershell
python -m pytest tests\test_dashboard.py::test_dashboard_baseline_evaluation_uses_latest_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_baseline_evaluation_is_scoped_to_dashboard_symbol -q
python -m pytest tests\test_dashboard.py::test_dashboard_prioritizes_strategy_decision_and_health_status tests\test_dashboard.py::test_dashboard_strategy_decision_uses_latest_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_strategy_decision_is_scoped_to_dashboard_symbol tests\test_dashboard.py::test_dashboard_baseline_evaluation_uses_latest_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_baseline_evaluation_is_scoped_to_dashboard_symbol tests\test_dashboard.py::test_dashboard_uses_specific_blocked_decision_reason_summary tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q
python -m pytest -q
python .\run_forecast_loop.py --help
git diff --check fe16d59 -- src\forecast_loop\dashboard.py tests\test_dashboard.py
```

## Residual Risks

- Tie-breaking for same-symbol baselines with identical `created_at` remains
  unspecified.
- This PR does not prove that the selected baseline belongs to the selected
  decision's exact evidence chain; it only prevents stale-tail and cross-symbol
  dashboard display mistakes.

