# PR147 Walk-Forward As-Of Replay

## Problem

PR146 added `backtest --as-of`, but decision-blocker planning also emits a
`walk-forward` command. The walk-forward runtime selected candles by
`start` / `end` and then ran internal backtests over those windows. Without an
as-of cutoff, later-imported or revised candles in the same timestamp span could
change a previously planned walk-forward validation.

## Decision

Add `--as-of` support to the `walk-forward` CLI and runtime.

When `as_of` is provided, `run_walk_forward_validation`:

- filters out candles whose `imported_at` is after the as-of timestamp;
- deduplicates same-symbol candles by timestamp;
- keeps the latest candle imported at or before the as-of timestamp;
- rejects `end > as_of`, so manual CLI runs cannot request a future evaluation
  window for a plan-time replay;
- passes the same `as_of` into each internal validation/test backtest;
- records the as-of timestamp in the walk-forward `decision_basis`.

The decision-blocker planner now emits `walk-forward --as-of <plan time>` when
stored same-symbol candles cover the conservative rolling validation window.

## Scope

This PR does not execute walk-forward automatically from
`execute-decision-blocker-research-next-task`. The executor still rejects ready
walk-forward tasks as unsupported and writes no false `AutomationRun`.

## Verification

Regression coverage proves:

- `walk-forward --as-of` ignores later-imported candle revisions in the selected
  timestamp span;
- `walk-forward --as-of` chooses the latest same-timestamp candle imported at or
  before the as-of timestamp;
- `walk-forward --as-of` rejects evaluation windows ending after the as-of
  timestamp;
- internal backtest runs inherit the same as-of cutoff;
- decision-blocker planning emits a ready walk-forward command with `--as-of`;
- executor handling remains fail-closed for ready but unsupported walk-forward
  tasks.
