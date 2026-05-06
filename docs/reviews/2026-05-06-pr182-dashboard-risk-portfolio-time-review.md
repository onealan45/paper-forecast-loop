# PR182 Dashboard Risk And Portfolio Time Review

## Scope

Review target: `codex/pr182-dashboard-risk-portfolio-time`.

This review covers dashboard selection for portfolio and risk context.

## Reviewer History

- Meitner: `CHANGES_REQUESTED`
  - P1: committed architecture doc had a blank line at EOF, so
    `git diff --check aba4282..HEAD` failed.
- Linnaeus: `APPROVED`
  - No blocker or changes requested after the EOF whitespace fix.

## Final Reviewer Evidence

Linnaeus reviewed:

- `git diff aba4282..HEAD`
- `src/forecast_loop/dashboard.py`
- `tests/test_dashboard.py`
- `docs/architecture/PR182-dashboard-risk-portfolio-time.md`

The reviewer confirmed:

- `latest_portfolio_snapshot` is selected by max `created_at`;
- `latest_risk_snapshot` is filtered to the dashboard symbol, then selected by
  max `created_at`;
- the PR does not break PR181 score/review filtering;
- docs reflect the implementation without overclaiming.

The reviewer reran:

```powershell
git diff --check aba4282..HEAD
python -m pytest tests\test_dashboard.py::test_dashboard_renders_portfolio_nav_pnl_and_risk tests\test_dashboard.py::test_dashboard_portfolio_snapshot_uses_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_risk_snapshot_is_scoped_to_symbol_and_created_at tests\test_dashboard.py::test_dashboard_renders_broker_sandbox_state tests\test_dashboard.py::test_dashboard_review_score_and_proposal_are_scoped_to_dashboard_symbol tests\test_dashboard.py::test_dashboard_review_and_score_use_created_times_not_scoped_file_tail -q
python -m pytest -q
```

## Final Verdict

`APPROVED`.

No blocker or important findings remain.

## Residual Risks

- Dashboard active symbol still follows the existing latest forecast / strategy
  decision fallback. That is outside PR182.
- Equal `created_at` tie behavior remains unspecified.

