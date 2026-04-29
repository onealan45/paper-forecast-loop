# PR28: Revision Retest Autopilot Run

## Goal

Allow a completed DRAFT revision retest chain to be recorded as a clean
`ResearchAutopilotRun` without requiring an unrelated next-horizon strategy
decision artifact.

## Scope

- Keep normal strategy autopilot runs strict: missing strategy decision remains
  blocking for non-revision strategy cards.
- Treat DRAFT strategy revision retests as research-loop evidence. A completed
  revision retest with linked paper-shadow outcome may omit
  `strategy_decision_id`.
- Do not promote the revision automatically.
- Do not change retest executor behavior.
- Do not add broker/sandbox/live execution paths.

## TDD Plan

1. Add a failing test that seeds a completed PR20-PR26 revision retest chain and
   calls `record_research_autopilot_run` without `strategy_decision_id`.
2. Assert the run is not blocked by `strategy_decision_missing`.
3. Assert normal strategy runs still block without `strategy_decision_id`.
4. Implement the smallest domain change in `autopilot.py`.
5. Add CLI regression coverage if the domain behavior change is non-trivial.

## Verification

- `python -m pytest tests\test_research_autopilot.py -k "revision_retest_autopilot or requires_paper_decision" -q`
- `python -m pytest -q`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
- `python .\run_forecast_loop.py --help`
- `git diff --check`

## Acceptance Criteria

- Completed revision retest chains can be logged as research autopilot evidence
  without fake decision artifacts.
- Normal strategy autopilot evidence remains strict.
- Final review is performed by a reviewer subagent and archived under
  `docs/reviews/`.
