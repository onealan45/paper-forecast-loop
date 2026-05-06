# PR182: Dashboard Risk And Portfolio Time Selection

## Context

The dashboard now selects decisions, baselines, scores, and reviews by active
symbol and artifact time. The adjacent portfolio and risk surfaces still used
JSONL tail selection:

- portfolio snapshots could show an older account snapshot appended after the
  current one;
- risk snapshots could show another symbol's risk state, or an older risk row
  for the active symbol.

That can mislead the strategy page because current decision evidence may appear
beside stale NAV, exposure, or risk posture.

## Decision

Dashboard snapshot construction now selects:

- `latest_portfolio_snapshot` by max `created_at`, because portfolio snapshots
  are account-level rather than symbol-specific;
- `latest_risk_snapshot` by first filtering to the dashboard symbol, then max
  `created_at`.

## Boundaries

- This only changes dashboard snapshot selection.
- It does not change portfolio accounting, risk-check generation, storage
  schema, broker state, or execution gates.
- Portfolio snapshots remain account-level. This PR does not introduce
  per-symbol portfolio snapshot semantics.

## Verification

```powershell
python -m pytest tests\test_dashboard.py::test_dashboard_portfolio_snapshot_uses_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_risk_snapshot_is_scoped_to_symbol_and_created_at -q
python -m pytest tests\test_dashboard.py::test_dashboard_review_score_and_proposal_are_scoped_to_dashboard_symbol tests\test_dashboard.py::test_dashboard_review_and_score_use_created_times_not_scoped_file_tail tests\test_dashboard.py::test_dashboard_portfolio_snapshot_uses_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_risk_snapshot_is_scoped_to_symbol_and_created_at -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

