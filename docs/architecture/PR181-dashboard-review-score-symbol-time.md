# PR181: Dashboard Review And Score Symbol Selection

## Context

PR179 and PR180 aligned dashboard strategy decisions and baseline evaluations
to the active dashboard symbol. The adjacent forecast-score and review panels
still used JSONL tail selection. In multi-symbol storage, the dashboard could
show the latest SPY forecast with a BTC-USD score, review, and proposal.

That weakens operator interpretation because the decision panel and evidence
snapshot can describe a different symbol from the current dashboard state.

## Decision

Dashboard snapshot construction now derives the active symbol's forecast ids,
then uses those ids to filter:

- `latest_score`, by matching `ForecastScore.forecast_id`;
- `latest_review`, by matching `Review.forecast_ids` or `Review.score_ids`;
- `latest_proposal`, by keeping the existing proposal-for-latest-review rule.

Scores are selected by max `scored_at`. Reviews are selected by max
`created_at`.

If storage has reviews but no forecasts, the dashboard preserves the legacy
fallback and uses the latest review/proposal without symbol filtering because
there is no reliable forecast-to-symbol mapping.

## Boundaries

- This only changes dashboard artifact selection.
- It does not change scoring, review generation, proposal generation, storage
  schema, replay summaries, or health-check logic.
- It does not infer a complete strategy decision evidence chain; it keeps the
  dashboard score/review/proposal surfaces aligned with the active symbol.
- Legacy no-forecast review storage keeps the previous unscoped latest-review
  behavior.

## Verification

```powershell
python -m pytest tests\test_dashboard.py::test_dashboard_review_score_and_proposal_are_scoped_to_dashboard_symbol -q
python -m pytest tests\test_dashboard.py::test_dashboard_review_and_score_use_created_times_not_scoped_file_tail -q
python -m pytest tests\test_dashboard.py::test_render_dashboard_includes_latest_artifacts tests\test_dashboard.py::test_render_dashboard_uses_only_proposal_for_latest_review tests\test_dashboard.py::test_dashboard_review_score_and_proposal_are_scoped_to_dashboard_symbol tests\test_dashboard.py::test_dashboard_review_and_score_use_created_times_not_scoped_file_tail tests\test_dashboard.py::test_dashboard_strategy_decision_uses_latest_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_strategy_decision_is_scoped_to_dashboard_symbol tests\test_dashboard.py::test_dashboard_baseline_evaluation_uses_latest_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_baseline_evaluation_is_scoped_to_dashboard_symbol -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```
