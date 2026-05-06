# PR165: Disable Digest Event-Edge Fallback

## Context

PR164 excluded the current `decision_research_artifact_ids` from event-edge
fallback, but active storage showed a broader issue: a digest with no explicit
active strategy event-edge could still borrow an older same-symbol event-edge
from previous decision-blocker research.

That makes `策略證據指標` look like it has active strategy event-edge
validation even when the active strategy chain never linked one.

## Decision

Digest event-edge evidence is now explicit-only:

- explicit digest `evidence_artifact_ids` still resolve;
- active chain `event_edge_evaluation_id` / `event_edge_evaluation_ids` still
  resolve;
- same-symbol fallback for event-edge is disabled.

Backtest and walk-forward fallback remain unchanged because those selectors are
already scoped by the active chain first and are used by current strategy
visibility flows.

## Boundaries

- This does not change event-edge calculation.
- This does not change decision generation.
- This does not hide decision-blocker event-edge artifacts; they remain visible
  under `決策阻擋研究證據`.
- This only prevents unlinked event-edge artifacts from being displayed as
  active strategy metrics.

## Verification

- Red test: `python -m pytest tests\test_strategy_research_digest.py::test_strategy_research_digest_does_not_fallback_to_unlinked_event_edge -q`
- Red test: `python -m pytest tests\test_strategy_digest_evidence.py::test_resolve_strategy_digest_evidence_falls_back_to_latest_same_symbol_as_of -q`
- Focused green: `python -m pytest tests\test_strategy_research_digest.py tests\test_strategy_digest_evidence.py tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q`
