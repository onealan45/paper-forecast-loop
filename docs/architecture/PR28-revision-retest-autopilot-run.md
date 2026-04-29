# PR28: Revision Retest Autopilot Run

## Context

`record-research-autopilot-run` was originally designed for the main strategy
decision loop. It always treated a missing `strategy_decision_id` as a blocking
evidence problem.

That is correct for normal strategy runs, but it is too strict for completed
DRAFT revision retests. A revision retest is a research-evidence loop; it can
have a strategy card, PASSED retest trial, locked evaluation, leaderboard entry,
and paper-shadow outcome without also having a next-horizon strategy decision.

## Change

PR28 allows `record_research_autopilot_run` to omit `strategy_decision_id` only
when the linked strategy card is a DRAFT revision candidate and the linked
paper-shadow outcome belongs to that revision.

Normal strategy runs still require strategy decision evidence. Weak or
unrankable revision retest evidence still blocks the run for the actual evidence
reasons, such as non-rankable locked evaluation or blocked leaderboard entry.

## Non-Goals

- No automatic strategy promotion.
- No fake strategy decision artifacts.
- No retest executor changes.
- No broker, sandbox, live order, or real-capital path.

## Verification

Regression coverage confirms:

- normal strategy autopilot runs still block on missing strategy decision;
- revision retest autopilot runs can omit strategy decision without adding
  `strategy_decision_missing`;
- weak locked-evaluation / leaderboard evidence still blocks the revision run.
