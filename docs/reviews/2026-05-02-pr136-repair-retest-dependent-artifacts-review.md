# PR136 Repair Retest Dependent Artifacts Review

## Scope

Review target: local branch `codex/pr136-repair-retest-dependent-artifacts`.

This review covers cascade quarantine for active artifacts that still reference
quarantined retest trials or already-quarantined retest dependent artifacts.

## Reviewer

- Reviewer subagent: Anscombe
- Review type: final code review with one follow-up after a blocking finding
- Final result: APPROVED

## Initial Finding

The first review was BLOCKED.

Finding:

- P1: cascade ignored already-quarantined dependent ids. A partial previous
  repair could leave active leaderboard, paper-shadow, or research-autopilot
  rows pointing at already-quarantined locked evaluation, leaderboard, or
  paper-shadow artifacts.

## Fix

Implementation added regression coverage for partial cascade repair and updated
`repair-storage` to merge existing dependent quarantine ids into downstream
bad-id sets:

- locked evaluation quarantine ids feed leaderboard, paper-shadow, and
  research-autopilot cascade;
- leaderboard quarantine ids feed paper-shadow and research-autopilot cascade;
- paper-shadow quarantine ids feed research-autopilot cascade.

## Final Reviewer Verification

Anscombe reran:

```powershell
python -m pytest tests\test_maintenance.py -q
python -m pytest tests\test_research_autopilot.py::test_health_check_flags_research_autopilot_link_errors -q
python -m pytest tests\test_maintenance.py tests\test_research_autopilot.py -q
git diff --check
```

Results:

- `tests\test_maintenance.py`: 8 passed
- focused research-autopilot link test: 1 passed
- maintenance + research autopilot related tests: 101 passed
- diff check: passed with CRLF warnings only

Reviewer also reran a temp-storage focused repro and confirmed the previous P1
no longer reproduces.

## Implementer Verification

Implementer ran:

```powershell
python -m pytest tests\test_maintenance.py tests\test_research_autopilot.py -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Results:

- maintenance + research autopilot related tests: 101 passed
- full test suite: 518 passed
- compileall: passed
- CLI help: passed
- diff check: passed with CRLF warnings only

## Remaining Risks

- The repair path still rewrites JSONL files rather than using a transactional
  store. This is consistent with current repair-storage behavior and not a new
  blocker for PR136.
- This review was a local focused reviewer-subagent review, not CodeRabbit.

## Decision

APPROVED for merge after normal machine gates pass.
