# PR145 Decision-Blocker Backtest Window

## Problem

After PR144, the decision-blocker planner can produce a safe walk-forward
command from stored market candles, but the active blocker sequence can still
stop earlier at `run_backtest` with `missing_backtest_window`.

The storage already has same-symbol candles, so the planner should distinguish
between missing market data and missing replay capability. A later review found
that emitting a plain `backtest --start --end` command would not preserve the
plan-time candle as-of set, because the backtest runtime reloads all stored
candles in the timestamp range.

## Decision

Update `decision-blocker-research-plan` so the backtest task has three explicit
states:

- completed when a same-symbol `backtest_result` exists at or after the blocker
  agenda timestamp;
- blocked with `market_candles` as the missing input when same-symbol candle
  coverage is not available;
- blocked with `backtest_asof_replay` when candles cover a window but the
  current CLI cannot faithfully replay the plan-time as-of candle set.

This is intentionally fail-closed. The planner no longer pretends that stored
candles are missing when the real blocker is replay semantics, but it also does
not emit a non-reproducible backtest command.

## Execution Boundary

`execute-decision-blocker-research-next-task` still only supports
`build_event_edge_evaluation`. If the next task is a blocked backtest, the
executor fails closed with a not-ready error and writes no `AutomationRun`.

This keeps PR145 scoped to safe planning. Automatic backtest execution can be
added later with artifact verification and review.

## Verification

Regression coverage proves:

- backtest planning stays blocked when same-symbol market candles are missing;
- backtest planning reports `backtest_asof_replay` when candles cover the
  conservative evidence window but the current CLI cannot pin that as-of set;
- backtest planning marks a same-symbol result created after the agenda as
  completed;
- the executor rejects blocked backtest tasks without writing a false
  automation-run success.
