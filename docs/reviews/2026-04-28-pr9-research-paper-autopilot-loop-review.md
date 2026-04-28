# PR9 Research / Paper Autopilot Loop Review

## Reviewer

- Reviewer: Darwin subagent
- Role: `docs/roles/reviewer.md`
- Scope: PR9 research agenda and autopilot run artifacts, service logic, CLI,
  JSONL/SQLite parity, health-check links, docs, and tests.
- Date: 2026-04-28

## Initial Findings

### P1: Validate the linked evidence chain, not only existence

The first implementation loaded agenda, strategy card, experiment trial, locked
evaluation, leaderboard entry, and paper-shadow outcome by id, but did not prove
they belonged to the same evidence chain. A mixed-chain run could still return
`READY_FOR_OPERATOR_REVIEW`.

### P1: Missing paper decision can still promote

The first implementation allowed a missing `strategy_decision_id` to skip the
paper-decision step while still producing `READY_FOR_OPERATOR_REVIEW`.

### P2: PR9 plan CLI example is stale and not executable

The plan used raw placeholders and stale flags such as `--trial-id` and
`--decision-id` instead of the implemented `--experiment-trial-id`,
`--locked-evaluation-id`, and `--strategy-decision-id`.

## First Fix Pass

- Added `test_research_autopilot_blocks_mismatched_evidence_chain`.
- Added `test_research_autopilot_requires_paper_decision_for_ready_state`.
- Added `test_health_check_flags_research_autopilot_mismatched_chain`.
- Added chain mismatch checks in `autopilot.py` and `health.py`.
- Updated the PR9 plan CLI examples to concrete PowerShell-safe commands.

## Follow-Up Finding

### P1: Linked paper decision state is still ignored

The reviewer found that a linked `StrategyDecision` with the wrong symbol,
`STOP_NEW_ENTRIES`, `tradeable=false`, and a blocked reason could still produce
`READY_FOR_OPERATOR_REVIEW`.

## Final Fix

- Added `test_research_autopilot_blocks_bad_paper_decision_state`.
- Added `test_health_check_flags_research_autopilot_bad_decision_state`.
- `autopilot.py` now blocks:
  - strategy decision symbol mismatch;
  - non-tradeable decision;
  - fail-closed `STOP_NEW_ENTRIES` or `REDUCE_RISK`;
  - non-empty decision blocked reason.
- `health.py` now emits equivalent `research_autopilot_run_strategy_decision_*`
  findings.

## Re-Review Result

The reviewer confirmed all prior findings are closed and found no blocking
findings.

Final recommendation: **APPROVED**.

## Verification

- Targeted mismatch / missing-decision tests -> passed
- Targeted bad-decision tests -> passed
- `python -m pytest tests\test_research_autopilot.py tests\test_paper_shadow.py tests\test_sqlite_repository.py tests\test_locked_evaluation.py -q` -> `35 passed`
- `python -m pytest -q` -> `290 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed and includes PR9 commands
- `git diff --check` -> passed; LF/CRLF warnings only

## Scope Notes

- PR9 adds audit-loop records, not a scheduler.
- PR9 does not automatically generate strategies.
- PR9 does not mutate strategy cards.
- PR9 does not add live trading, real broker execution, secrets, or runtime
  artifacts.
