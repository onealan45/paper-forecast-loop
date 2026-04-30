# PR56 Lineage Replacement Next Step Review

Date: 2026-04-30

Reviewer: Harvey (`019ddad3-2758-75c1-bb0d-7046ffe645cc`)

## Scope

Reviewed branch `codex/lineage-replacement-next-step`.

PR56 carries replacement context into the next lineage research task when a
replacement retest is the latest improving lineage evidence.

## Reviewed Changes

- `lineage-research-plan` includes replacement card id, latest replacement
  outcome id, latest excess return, and source outcome id in the
  `verify_cross_sample_persistence` worker prompt.
- The task rationale states that cross-sample validation should test the
  replacement hypothesis directly.
- README, PRD, and architecture notes describe the replacement-aware follow-up
  behavior.

## Reviewer Findings And Fixes

Harvey reported two P2 findings during review:

- Stale replacement context could leak into a newer root/revision-driven
  improvement because `_latest_replacement_context` fell back to any replacement
  node with a latest outcome.
- Replacement context could still overclaim causality when the latest lineage
  outcome belonged to a replacement node but its latest change label was not an
  improvement.

Both were fixed:

- `_latest_replacement_context` now requires exact
  `node.latest_outcome_id == summary.latest_outcome_id`.
- `_latest_replacement_context` also requires
  `summary.latest_change_label == "改善"`.
- Added regressions for stale replacement evidence and unknown latest
  replacement evidence.
- Updated PR56 architecture notes to document the exact-match and improvement
  requirements.

## Verification Evidence

- `python -m pytest tests\test_lineage_research_plan.py::test_lineage_research_task_plan_includes_replacement_context_for_improving_replacement -q` -> 1 passed
- `python -m pytest tests\test_lineage_research_plan.py::test_lineage_research_task_plan_omits_stale_replacement_context_when_latest_outcome_is_root -q` -> 1 passed
- `python -m pytest tests\test_lineage_research_plan.py::test_lineage_research_task_plan_omits_replacement_context_when_latest_replacement_is_unknown -q` -> 1 passed
- `python -m pytest tests\test_lineage_research_plan.py -q` -> 15 passed
- `python -m pytest tests\test_strategy_lineage.py -q` -> 10 passed
- `python -m pytest -q` -> 418 passed
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> exit 0
- `python .\run_forecast_loop.py --help` -> exit 0
- `git diff --check` -> exit 0
- `git ls-files .codex paper_storage reports output .env` -> empty

## Final Reviewer Result

APPROVED

No remaining blocking findings were reported.

## Safety / Runtime Artifact Check

This review did not approve any real-order, real-capital, broker-live, secret,
or runtime artifact path. Runtime and local-only folders remain excluded from
Git scope.
