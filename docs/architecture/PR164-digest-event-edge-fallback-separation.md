# PR164: Digest Event-Edge Fallback Separation

## Context

PR163 separated `decision_research_artifact_ids` from the digest's active
strategy evidence list. One remaining edge case existed for event-edge metrics:
when the active strategy chain had no explicit event-edge ID, the digest builder
and read-side resolver could still fall back to the latest same-symbol
event-edge artifact. If the latest event-edge was created by decision-blocker
research, it could appear as active strategy validation while also appearing in
`決策阻擋研究證據`.

## Decision

Event-edge fallback now excludes IDs listed in
`StrategyResearchDigest.decision_research_artifact_ids`.

This applies in two places:

- digest generation in `strategy_research_digest.py`;
- dashboard/operator-console evidence resolution in
  `strategy_digest_evidence.py`.

Explicit active-chain evidence IDs still win. The change only affects fallback
selection when no explicit active event-edge ID is present.

## Boundaries

- This does not change event-edge evaluation math.
- This does not change backtest or walk-forward fallback selection.
- This does not change decision generation or strategy gates.
- Decision-blocker event-edge artifacts remain visible in
  `決策阻擋研究證據`; they are only excluded from active strategy metrics.

## Verification

- Red test: `python -m pytest tests\test_strategy_research_digest.py::test_strategy_research_digest_does_not_use_decision_blocker_event_edge_as_strategy_metric -q`
- Red test: `python -m pytest tests\test_strategy_digest_evidence.py::test_resolve_strategy_digest_evidence_event_edge_fallback_excludes_decision_blocker_ids -q`
- Focused green: `python -m pytest tests\test_strategy_research_digest.py tests\test_strategy_digest_evidence.py tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q`
