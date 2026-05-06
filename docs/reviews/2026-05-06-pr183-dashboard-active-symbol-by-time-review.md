# PR183 Dashboard Active Symbol By Time Review

## Scope

Review target: `codex/pr183-dashboard-active-symbol-by-time`.

This review covers dashboard active forecast and active symbol selection.

## Reviewer

Final reviewer: Kepler.

Verdict: `APPROVED`.

## Findings

No blocker or important findings.

## Evidence Reviewed

Kepler reviewed committed diff `d21312d..f8d26cc` and confirmed:

- expected files are included;
- `build_dashboard_snapshot()` selects latest forecast by max `created_at`;
- no-forecast symbol fallback uses the max-`created_at` strategy decision;
- tests cover both forecast file-tail regression and no-forecast decision
  fallback regression;
- architecture docs match implementation without overclaiming.

The reviewer reran:

```powershell
git diff --check d21312d..f8d26cc
python -m pytest tests\test_dashboard.py::test_dashboard_latest_forecast_uses_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_symbol_fallback_uses_latest_decision_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_strategy_decision_is_scoped_to_dashboard_symbol tests\test_dashboard.py::test_dashboard_review_score_and_proposal_are_scoped_to_dashboard_symbol tests\test_dashboard.py::test_dashboard_baseline_evaluation_is_scoped_to_dashboard_symbol tests\test_dashboard.py::test_dashboard_risk_snapshot_is_scoped_to_symbol_and_created_at -q
```

## Residual Risks

- Equal `created_at` tie behavior remains intentionally unspecified.

