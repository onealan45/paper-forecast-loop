# PR123: Latest Retest Digest Visibility

## Context

The strategy research digest is the compact handoff consumed by automation and
shown in the dashboard/operator console. After a replacement retest completes a
leaderboard gate but still waits for a future paper-shadow window, the digest
must show the active retest chain instead of an older research autopilot run or
older paper-shadow outcome.

## Decision

- Prefer a `ResearchAutopilotRun` only when it is at least as fresh as the
  newest research anchor.
- When timestamps tie, choose the most downstream research artifact:
  `paper_shadow_outcome > leaderboard_entry > locked_evaluation > trial >
  agenda > strategy_card`.
- Preserve primary artifact ids in digest evidence, rather than letting foreign
  keys such as `trial_id` hide `leaderboard-entry`, `locked-evaluation`,
  `paper-shadow-outcome`, or `research-autopilot-run` ids.
- When a leaderboard entry exists but no paper-shadow outcome exists yet, mark
  the next research action as `WAIT_FOR_PAPER_SHADOW_OUTCOME`.

## Why This Matters

This keeps the UX and automation handoff focused on the strategy currently under
evaluation. The operator should see that the new replacement card passed into a
leaderboard entry and is waiting for the next observation window, not only that
an older lineage outcome was blocked.

## Scope

Included:

- strategy research chain freshness ordering;
- same-timestamp downstream artifact priority;
- digest evidence id primary-key ordering;
- Traditional Chinese action copy for waiting on a paper-shadow window.

Excluded:

- changing paper-shadow window enforcement;
- fabricating future returns;
- changing leaderboard or locked evaluation gates;
- broker/exchange execution.

## Verification

- `python -m pytest tests\test_strategy_research_digest.py tests\test_strategy_research_display.py -q`
