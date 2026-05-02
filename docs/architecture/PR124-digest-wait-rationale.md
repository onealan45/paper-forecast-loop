# PR124: Digest Wait Rationale

## Context

PR123 made the strategy research digest point at the active retest chain when a
leaderboard entry exists but the post-entry paper-shadow observation window is
not complete. The summary correctly says the next action is waiting for the
paper-shadow window, but `next_step_rationale` could still be dominated by the
broader lineage quarantine rationale.

## Decision

When `next_research_action == "WAIT_FOR_PAPER_SHADOW_OUTCOME"`, the digest
rationale should describe the immediate blocker:

- a leaderboard entry already exists;
- no post-entry paper-shadow observation exists yet;
- the system must wait for the next complete observation window;
- future returns must not be fabricated.

## Scope

Included:

- `StrategyResearchDigest.next_step_rationale` immediate-action override;
- regression coverage in `tests/test_strategy_research_digest.py`.

Excluded:

- changing shadow-window readiness rules;
- deriving returns before candles exist;
- changing leaderboard gates or lineage verdicts.

## Verification

- `python -m pytest tests\test_strategy_research_digest.py -q`
