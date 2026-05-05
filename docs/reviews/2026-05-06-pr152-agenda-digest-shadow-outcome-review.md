# PR152 Agenda Digest Shadow Outcome Review

## Scope

Reviewed branch `codex/pr152-agenda-digest-shadow-outcome` against `main`.

Primary files:

- `src/forecast_loop/strategy_research.py`
- `tests/test_strategy_research_digest.py`
- `docs/architecture/PR152-agenda-digest-shadow-outcome.md`

## Reviewer

- Subagent reviewer: `019df9fa-5cee-7be0-8554-339f5e3baf27`
- Role: final reviewer
- Parent did not self-review.

## Initial Finding

### BLOCKED - P1

`src/forecast_loop/strategy_research.py` initially selected a fallback
paper-shadow outcome for an agenda anchor using only `strategy_card_id` and
`symbol`. That could mask a newer same-card retest, evaluation, or leaderboard
that was still waiting for a new paper-shadow outcome.

Reviewer reproduction:

- old same-card outcome existed at `+10m`
- newer same-card retest / leaderboard existed at `+23m`
- newer agenda existed at `+24m`
- digest incorrectly returned the old outcome and `QUARANTINE_STRATEGY`
  instead of waiting for paper-shadow evidence

## Fix

- Added a regression test for the original active-storage case:
  newer decision-blocker agenda pointing to a strategy card that already has a
  valid paper-shadow outcome.
- Added a regression test for the reviewer case:
  newer same-card retest / leaderboard waiting for paper-shadow outcome must not
  be masked by an older same-card outcome.
- Changed the agenda-anchor path to resolve the latest same-card non-agenda
  evidence first:
  - outcome -> keep outcome in digest
  - newer trial / evaluation / leaderboard -> keep waiting for paper-shadow
  - no evidence -> card + agenda only

## Verification

- `python -m pytest -q` -> `554 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> exit 0, LF/CRLF warnings only
- Active BTC-USD storage refresh:
  - latest digest shows `paper-shadow-outcome:b8824f418cf79b18`
  - outcome grade `BLOCKED`
  - recommended action `QUARANTINE`
  - health-check `healthy`, severity `none`, repair required `false`

## Final Review

APPROVED.

Reviewer confirmed the P1 repro now stays at:

- `paper_shadow_outcome_id=None`
- `WAIT_FOR_PAPER_SHADOW_OUTCOME`

when a newer same-card retest is still waiting for shadow evidence. Tests and
documentation match the implemented exception.

## Safety Boundary

No real-order, real-capital, or secret-handling path was added.
