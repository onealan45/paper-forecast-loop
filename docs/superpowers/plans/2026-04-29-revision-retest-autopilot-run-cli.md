# PR29: Revision Retest Autopilot Run CLI

## Goal

Add a direct helper and CLI command that records the latest completed revision
retest chain as a `ResearchAutopilotRun` without requiring the operator to copy
agenda, trial, evaluation, leaderboard, and shadow outcome IDs by hand.

## Scope

- Add a domain helper that:
  - builds the current revision retest task plan;
  - requires a completed plan with passed trial, locked evaluation, leaderboard,
    and paper-shadow outcome;
  - resolves the linked revision agenda;
  - calls `record_research_autopilot_run` without a fake strategy decision.
- Add CLI:
  - `record-revision-retest-autopilot-run`
  - args: `--storage-dir`, `--revision-card-id`, `--symbol`, `--now`
- Do not change retest executor behavior.
- Do not auto-promote strategies.
- Do not add broker/sandbox/live execution behavior.

## TDD Plan

1. Add failing domain test for `record_revision_retest_autopilot_run`.
2. Add failing CLI test for `record-revision-retest-autopilot-run`.
3. Implement helper and wire CLI.
4. Verify existing generic `record-research-autopilot-run` behavior remains.

## Verification

- `python -m pytest tests\test_research_autopilot.py -k "revision_retest_autopilot_run or cli_record_revision_retest_autopilot" -q`
- `python -m pytest -q`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
- `python .\run_forecast_loop.py --help`
- `git diff --check`

## Acceptance Criteria

- The operator can record the completed revision retest loop with one command.
- The command refuses incomplete chains through existing plan evidence.
- No fake strategy decision is created.
- Final review is performed by a reviewer subagent and archived under
  `docs/reviews/`.
