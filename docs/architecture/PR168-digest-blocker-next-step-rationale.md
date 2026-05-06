# PR168: Digest Blocker Next-Step Rationale

## Context

After PR167, dashboard and operator console expose concrete decision-blocker
metrics. Active runtime then showed a remaining semantic mismatch: the digest
could still say the next step is only waiting for paper-shadow even when the
latest decision already links blocker evidence that keeps BUY/SELL blocked.

That makes the loop look passive while the research evidence says the strategy
needs blocker-focused interpretation or revision.

## Decision

When a `StrategyResearchDigest` has both:

- `decision_research_blockers`, and
- `decision_research_artifact_ids`,

`next_step_rationale` now prioritizes the decision-blocker research path. The
copy says the blockers are still unresolved, counts linked blocker evidence,
and directs the next step toward comparing event-edge, backtest, and
walk-forward results before revising strategy hypotheses or data/features.

Paper-shadow waiting remains the fallback when no decision-blocker evidence is
linked.

## Boundaries

- This does not change `next_research_action`.
- This does not change decision generation.
- This does not change artifact schemas.
- This does not promote blocker evidence into active strategy metrics.
- This only changes the digest narrative used by dashboard/operator console.

## Verification

- Red test:
  `python -m pytest tests\test_strategy_research_digest.py::test_strategy_research_digest_records_decision_blocker_research_artifact_ids -q`
- Focused green:
  `python -m pytest tests\test_strategy_research_digest.py::test_strategy_research_digest_records_decision_blocker_research_artifact_ids -q`
- Digest suite:
  `python -m pytest tests\test_strategy_research_digest.py -q`
