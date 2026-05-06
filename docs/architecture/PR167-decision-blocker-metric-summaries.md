# PR167: Decision-Blocker Metric Summaries

## Context

PR166 separated active strategy metrics from decision-blocker research evidence.
After that separation, the dashboard and operator console still showed
decision-blocker evidence mostly as raw artifact IDs.

That preserves traceability, but it does not expose enough concrete strategy
research content. Operators should be able to see why BUY/SELL is blocked
without opening raw JSONL artifacts.

## Decision

`StrategyDigestEvidence` now resolves exact decision-blocker evidence artifacts
from `StrategyResearchDigest.decision_research_artifact_ids`:

- `decision_event_edge`
- `decision_backtest`
- `decision_walk_forward`

The dashboard and operator console render metric summaries in the
`決策阻擋研究證據` section:

- event-edge sample size, after-cost edge, hit rate, pass flag, and flags;
- backtest strategy return, benchmark return, drawdown, win rate, and trades;
- walk-forward excess return, window count, test win rate, overfit windows, and
  flags.

Unresolved decision-blocker IDs still render as traceability fallback.

## Boundaries

- This does not change decision generation.
- This does not promote decision-blocker evidence into active strategy metrics.
- This does not alter artifact schemas; the new fields are read-side resolver
  fields only.
- This does not change research calculations.

## Verification

- Red tests:
  `python -m pytest tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q`
- Focused green:
  `python -m pytest tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q`
