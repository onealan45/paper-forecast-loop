# PR111 Shadow Outcome Post-Entry Window Review

## Scope

- Branch: `codex/pr111-shadow-outcome-post-entry-window`
- Reviewer: subagent `Cicero`
- Review mode: blocking-only final review

## Result

APPROVED.

No blocking findings.

## Findings

No blocking findings.

## Residual Risk

The guard ensures the shadow window starts no earlier than the leaderboard
entry `created_at`. It does not independently prove the underlying data source
was imported after the entry. This is acceptable for PR111 because the stated
intent is to prevent pre-entry windows from being recorded as fresh shadow
observations.

## Verification Evidence

- New tests failed before implementation.
- `python -m pytest .\tests\test_research_autopilot.py .\tests\test_paper_shadow.py -q` -> `90 passed`
- `python -m pytest -q` -> `482 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> passed
- Active health-check -> healthy
- Active pre-entry derived-shadow smoke exits with code `2`,
  `revision_retest_shadow_window_starts_before_leaderboard_entry`, and keeps
  `paper_shadow_outcomes.jsonl` line count unchanged at `2`.

## Docs And Tests

Reviewer confirmed tests and docs match implementation:

- generic paper-shadow outcome recording rejects pre-entry windows
- revision retest executor rejects pre-entry windows before deriving candle
  returns
- valid derived-shadow tests now use post-leaderboard candles
- README, PRD, and architecture note describe the implemented behavior

