# PR169: Dedupe Decision-Blocker Research Windows

## Context

Decision-blocker research can create a new agenda every time a new strategy
decision repeats the same blocker summary. Before this change, the task planner
only treated event-edge, backtest, and walk-forward artifacts as complete when
they were created after the latest agenda. If the latest candle/data window had
not changed, a new agenda could still schedule the same blocker research again.

That wastes cycles and grows runtime artifacts without adding new prediction
evidence.

## Decision

The decision-blocker task planner now keeps the original "artifact after agenda"
behavior, but adds input-window reuse:

- Event-edge evidence can be reused when the latest same-symbol evaluation was
  created after the current event/reaction/candle input watermark. It does not
  need to be newer than a repeated agenda when the input watermark is unchanged;
  otherwise the dedupe would not work for identical blocker agendas.
- Backtest evidence can be reused when a blocker-focused backtest run/result
  covers the same symbol, start/end window, and exact candle ids, and was created
  after the candle input watermark. Both the run and result must be fresh enough;
  a late result cannot rescue a run created before a candle re-import.
- Walk-forward evidence can be reused when a blocker-focused validation covers
  the same symbol and start/end window, and was created after the candle input
  watermark.
- Reused evidence must not be future-dated relative to the planner `now`.

The task plan reports reused evidence as `completed` with no command args, so
the executor will not create another identical research artifact.

## Boundaries

- This does not delete or rewrite existing runtime artifacts.
- This does not change decision generation or BUY/SELL gates.
- This does not relax research gates; weak evidence still blocks directional
  action.
- This does not reuse backtests or walk-forward validations that lack the
  decision-blocker id context.
- This does not reuse event-edge evidence after any newer event, market reaction,
  or candle import changes the input watermark.

## Verification

- Red/green planner suite:
  `python -m pytest tests\test_decision_research_plan.py -q`
  Covers reuse and non-reuse cases for unchanged inputs, stale event-edge inputs,
  generic backtests, stale backtest runs with late results, and wrong-window
  walk-forward validations.
- Executor suite:
  `python -m pytest tests\test_decision_research_executor.py -q`
- Digest suite:
  `python -m pytest tests\test_strategy_research_digest.py -q`
- Active storage smoke:
  `python .\run_forecast_loop.py decision-blocker-research-plan --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD --symbol BTC-USD`
