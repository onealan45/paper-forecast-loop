# PR125: Failure-Aware Replacement Strategy Cards

## Context

Lineage replacement strategy cards were traceable but too generic. They recorded
that a replacement was needed, yet the strategy content still looked like a
template: "test a distinct signal stack focused on failures." That was not
enough for a research-first loop where the UX should expose concrete strategy
hypotheses, rules, failure controls, and retest requirements.

## Decision

Add a deterministic failure-aware replacement design helper. It maps source
paper-shadow failure attributions into a concrete `StrategyCard` design:

- `drawdown_breach` / `adverse_excursion_breach` -> drawdown-controlled edge
  rebuild with reduced exposure and adverse-excursion limits.
- `weak_baseline_edge`, `baseline_edge_not_positive`, or weak holdout edge ->
  strengthened after-cost baseline-edge requirements.
- `turnover_breach` / `turnover_limit_exceeded` -> cooldown and lower turnover
  rules.
- `overfit_risk_flagged` / weak walk-forward evidence -> all-split
  walk-forward stability requirements.
- not-rankable / missing-alpha leaderboard evidence -> rankability completion
  requirements.

The implementation remains deterministic and testable. It does not call an LLM
runtime, fetch new data, change evaluation gates, or fabricate strategy
performance.

## Scope

Included:

- `ReplacementStrategyDesign` helper in `strategy_evolution.py`;
- concrete replacement hypothesis, signal description, entry/exit/risk rules;
- additional parameters such as `replacement_strategy_archetype`,
  `confirmation_count`, `max_position_multiplier`, and stronger
  `minimum_after_cost_edge`;
- regression assertions in `tests/test_lineage_research_executor.py`.

Excluded:

- changing existing already-created replacement cards in runtime storage;
- automatically promoting replacement cards;
- changing retest/leaderboard/paper-shadow gates;
- adding live trading or broker execution.

## Verification

- `python -m pytest tests\test_lineage_research_executor.py::test_execute_lineage_research_next_task_creates_replacement_strategy_card -q`
- `python -m pytest tests\test_lineage_research_executor.py tests\test_lineage_research_plan.py tests\test_strategy_lineage.py -q`
- `python -m pytest tests\test_dashboard.py::test_dashboard_shows_lineage_replacement_strategy_hypothesis tests\test_operator_console.py::test_operator_console_shows_lineage_replacement_strategy_hypothesis -q`
