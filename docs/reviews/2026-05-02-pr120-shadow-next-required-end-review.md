# PR120 Shadow Next Required End Review

## Scope

- Branch: `codex/pr120-shadow-next-required-end`
- Files reviewed:
  - `src/forecast_loop/revision_retest_plan.py`
  - `tests/test_research_autopilot.py`
- Intent: improve revision retest shadow-readiness copy by showing the expected next required candle timestamp when only the first aligned candle has been observed.

## Reviewer

- Subagent: `Gibbs`
- Role: `docs/roles/reviewer.md`
- Result: `APPROVED`

## Findings

- No blocking findings.
- Reviewer confirmed `candidate_window_ready` is still gated by an observed second candle.
- Reviewer confirmed inferred `next_required_window_end` does not generate command arguments by itself.
- Reviewer confirmed the existing command suggestion path remains intact once the second candle exists.

## Verification

- RED check:
  - `python -m pytest tests\test_research_autopilot.py::test_revision_retest_shadow_task_exposes_aligned_window_readiness -q`
  - Failed before implementation because the rationale still displayed `next_required_window_end=missing`.
- Targeted checks:
  - `python -m pytest tests\test_research_autopilot.py::test_revision_retest_shadow_task_exposes_aligned_window_readiness tests\test_research_autopilot.py::test_revision_retest_shadow_task_exposes_ready_aligned_window_candidate tests\test_dashboard.py::test_dashboard_revision_retest_task_plan_shows_shadow_readiness_copy tests\test_dashboard.py::test_dashboard_lineage_replacement_retest_panel_shows_shadow_readiness_copy -q`
  - Passed: `4 passed`.
- Full gate:
  - `python -m pytest -q`
  - Passed: `494 passed`.
  - `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Passed.
  - `python .\run_forecast_loop.py --help`
  - Passed.
  - `git diff --check`
  - Passed with CRLF warnings only.
- Runtime check:
  - Active revision retest plan for `strategy-card:5151c231b76295fa` now shows `next_required_window_end=2026-05-01T21:00:00+00:00` while keeping `candidate_window_ready=false` with latest stored candle `2026-05-01T20:00:00+00:00`.

## Decision

Approved for merge.
