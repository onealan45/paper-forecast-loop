# PR155 Operator Console Research Backtest Selection

## Context

`decision`, `strategy-research-digest`, and the dashboard already prefer
standalone decision-blocker backtest evidence when both standalone blocker
backtests and newer walk-forward-internal backtests exist.

The operator console still selected `latest_backtest` by raw creation time.
That could make the console's top-level Backtest card show a newer
walk-forward-internal backtest while the decision and digest were correctly
using the standalone decision-blocker backtest.

## Decision

The operator console snapshot now uses the shared
`latest_backtest_for_research` selector.

Selection order:

1. same-symbol backtests only;
2. prefer backtests whose linked `BacktestRun.decision_basis` contains the
   decision-blocker run context;
3. fall back to the newest same-symbol backtest when no preferred blocker
   backtest exists.

## Impact

- The console, dashboard, digest, and decision layer now agree on the primary
  research backtest evidence.
- Walk-forward validation still displays as walk-forward evidence; its internal
  backtests no longer steal the standalone Backtest card when blocker evidence
  exists.
- No storage format change.

## Verification

- Added a regression test where a newer walk-forward-internal backtest and an
  older standalone decision-blocker backtest coexist.
- The snapshot must expose the standalone blocker backtest as
  `latest_backtest`.
