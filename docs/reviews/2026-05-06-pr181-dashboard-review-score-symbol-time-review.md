# PR181 Dashboard Review And Score Symbol Time Review

## Scope

Review target: `codex/pr181-dashboard-review-score-symbol-time`.

This review covers dashboard selection for score, review, and proposal evidence.
The intent is to keep the decision and evidence panels aligned with the active
dashboard symbol.

## Reviewer History

- Aristotle: `CHANGES_REQUESTED`
  - P1: the first review inspected an uncommitted working-tree diff, so the
    committed branch diff was empty.
  - P3: the first regression only covered cross-symbol contamination, not
    same-symbol stale file-tail ordering.
- Ohm: `APPROVED`
  - No blocker or important findings after the changes were committed and the
    same-symbol stale-tail regression was added.

## Final Reviewer Evidence

Ohm reviewed committed diff `c4bbba1..HEAD` and confirmed it includes:

- `src/forecast_loop/dashboard.py`
- `tests/test_dashboard.py`
- `docs/architecture/PR181-dashboard-review-score-symbol-time.md`

The reviewer confirmed:

- active-symbol forecast ids drive score and review filtering;
- `latest_score` uses max `scored_at`;
- `latest_review` uses max `created_at`;
- proposals remain tied to the selected latest review;
- no-forecast storage preserves the legacy unscoped fallback;
- tests cover both cross-symbol tail contamination and same-symbol file-tail
  ordering.

The reviewer reran:

```powershell
git diff --check c4bbba1..HEAD
python -m pytest tests\test_dashboard.py::test_render_dashboard_includes_latest_artifacts tests\test_dashboard.py::test_render_dashboard_uses_only_proposal_for_latest_review tests\test_dashboard.py::test_dashboard_review_score_and_proposal_are_scoped_to_dashboard_symbol tests\test_dashboard.py::test_dashboard_review_and_score_use_created_times_not_scoped_file_tail tests\test_dashboard.py::test_dashboard_strategy_decision_uses_latest_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_strategy_decision_is_scoped_to_dashboard_symbol tests\test_dashboard.py::test_dashboard_baseline_evaluation_uses_latest_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_baseline_evaluation_is_scoped_to_dashboard_symbol -q
python -m pytest -q
```

## Final Verdict

`APPROVED`.

No blocker or important findings remain.

## Residual Risks

- Mixed-symbol reviews can still appear on any symbol they intersect; this
  follows the current design but is not strict single-symbol review purity.
- Legacy reviews with empty evidence ids are preserved only by the no-forecast
  fallback. If old storage has forecasts plus unmapped legacy reviews, those
  reviews may no longer surface in the dashboard.

