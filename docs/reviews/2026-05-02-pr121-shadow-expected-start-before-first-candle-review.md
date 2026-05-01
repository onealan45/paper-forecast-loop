# PR121 Shadow Expected Start Before First Candle Review

## Scope

- Branch: `codex/pr121-shadow-expected-start-before-first-candle`
- Files reviewed:
  - `src/forecast_loop/revision_retest_plan.py`
  - `tests/test_research_autopilot.py`
- Intent: improve revision retest shadow-readiness copy when a leaderboard entry exists but no post-entry candle has been observed yet.

## Reviewer

- Subagent: `Planck`
- Role: `docs/roles/reviewer.md`
- Result: `APPROVED`

## Findings

- No blocking findings.
- Reviewer confirmed `candidate_window_ready` remains gated by `next_required_window_observed`.
- Reviewer confirmed inferred expected start/end does not create `command_args`.
- Reviewer confirmed interval inference uses positive timestamp deltas and does not introduce an infinite loop.
- Reviewer confirmed existing post-entry candle ready path and command suggestion behavior are still covered by tests.
- Reviewer confirmed there is no artifact schema change.

## Verification

- RED check:
  - `python -m pytest tests\test_research_autopilot.py::test_revision_retest_shadow_task_exposes_expected_window_before_first_post_entry_candle -q`
  - Failed before implementation because the readiness rationale still displayed missing aligned start/end.
- Targeted checks:
  - `python -m pytest tests\test_research_autopilot.py::test_revision_retest_shadow_task_exposes_expected_window_before_first_post_entry_candle tests\test_research_autopilot.py::test_revision_retest_shadow_task_exposes_aligned_window_readiness tests\test_research_autopilot.py::test_revision_retest_shadow_task_exposes_ready_aligned_window_candidate -q`
  - Passed: `3 passed`.
- Full gate before review:
  - `python -m pytest -q`
  - Passed: `495 passed`.
  - `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Passed.
  - `python .\run_forecast_loop.py --help`
  - Passed.
  - `git diff --check`
  - Passed with CRLF warnings only.
- Runtime check:
  - Active third-generation retest plan for `strategy-card:c2340c8b1a3b21d1` now shows expected `first_aligned_window_start=2026-05-01T22:00:00+00:00`, `next_required_window_end=2026-05-01T23:00:00+00:00`, and `candidate_window_ready=false`.

## Decision

Approved for merge after rerunning final verification with this review archive included.
