# M7F Decision Integration

## Summary

M7F connects the M7B-M7E Alpha Evidence Engine into the existing strategy
decision path. It does this conservatively:

- no new BUY/SELL shortcut;
- no schema change to `strategy_decisions.jsonl`;
- no direct LLM/news/event signal promotion;
- no live execution path.

The only behavioral change is that directional strategy decisions now require
the latest event-family historical edge evaluation for the symbol to pass the
research gate.

## Implemented Scope

M7F updates:

- `forecast_loop.decision.generate_strategy_decision`
- `forecast_loop.research_gates.evaluate_research_gates`
- `tests/test_research_gates.py`

The decision engine now loads the latest `EventEdgeEvaluation` for the decision
symbol and passes it into the research gate.

## Gate Semantics

BUY/SELL still require all previous gates:

- forecast evidence;
- model edge over baseline;
- evidence grade `A` or `B`;
- backtest quality;
- walk-forward quality;
- risk freshness;
- health not blocking.

M7F adds the event-edge requirement:

- missing latest event edge -> `research_event_edge_missing`;
- latest event edge `passed=false` -> `research_event_edge_not_passed`;
- missing or non-positive `average_excess_return_after_costs` ->
  `research_event_edge_not_positive`.

Any of these blocks directional BUY/SELL and produces HOLD unless a stronger
risk gate already forces REDUCE_RISK or STOP_NEW_ENTRIES.

## Decision Basis

M7F keeps the `StrategyDecision` artifact schema unchanged. Event evidence is
surfaced in `decision_basis`:

- `event_edge=<evaluation_id|missing>`
- `event_edge_sample_n=<n>`
- `event_edge_average_excess_after_costs=<value>`
- `event_edge_passed=<true|false|none>`
- `event_edge_flags=<flags>`

This makes the decision auditable without widening the strategy decision schema
before the downstream UX and report layers are updated.

## Deferred Scope

M7F intentionally does not implement:

- strategy-card generation;
- experiment registry;
- leaderboard promotion;
- event-derived feature snapshots in decision artifacts;
- dashboard strategy redesign;
- live fetch, broker, testnet, live order, or secret paths.

Those remain later Alpha Factory PRs under the master sequence.

## Acceptance

M7F is complete when:

- missing event edge blocks BUY/SELL;
- failed event edge blocks BUY/SELL;
- passed event edge allows the pre-existing quality path to proceed;
- decision basis exposes the edge evaluation evidence;
- existing baseline/backtest/walk-forward/risk/health gates remain active;
- tests, compile checks, CLI help, diff check, and independent reviewer approval
  pass.
