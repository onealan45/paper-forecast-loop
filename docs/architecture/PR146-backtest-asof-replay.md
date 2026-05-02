# PR146 Backtest As-Of Replay

## Problem

PR145 correctly refused to emit a ready backtest command because the backtest
runtime could only replay by `start` / `end`. That was not enough for
plan-time research evidence: if later-imported or revised candles existed in the
same timestamp span, the runtime could use data that was unavailable when the
planner decided the task was ready.

## Decision

Add `--as-of` support to the `backtest` CLI and runtime.

When `as_of` is provided, `run_backtest`:

- filters out candles whose `imported_at` is after the as-of timestamp;
- deduplicates same-symbol candles by timestamp;
- keeps the latest candle imported at or before the as-of timestamp;
- rejects `end > as_of`, so manual CLI runs cannot request a future evaluation
  window for a plan-time replay;
- records the as-of timestamp in `decision_basis`;
- includes the as-of timestamp in the backtest identity context.

The decision-blocker planner can now emit a ready `backtest` command with
`--as-of <plan time>` when stored same-symbol candles cover the conservative
evidence window.

## Scope

This PR does not execute backtests automatically from
`execute-decision-blocker-research-next-task`. The executor still rejects ready
backtest tasks as unsupported and writes no false `AutomationRun`.

## Verification

Regression coverage proves:

- `backtest --as-of` ignores later-imported candle revisions in the selected
  timestamp span;
- `backtest --as-of` rejects evaluation windows ending after the as-of
  timestamp;
- the emitted run records the as-of timestamp in `decision_basis`;
- decision-blocker planning emits a ready backtest command with `--as-of` when
  candle coverage is sufficient;
- executor handling remains fail-closed for ready but unsupported backtest
  tasks.
