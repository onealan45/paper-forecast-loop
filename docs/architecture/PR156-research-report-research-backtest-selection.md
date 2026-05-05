# PR156 Research Report Research Backtest Selection

## Context

The strategy decision, strategy research digest, dashboard, and operator console
all prefer standalone decision-blocker backtest evidence over newer
walk-forward-internal backtests. The Markdown research report still selected the
latest same-symbol backtest by raw creation time.

That made generated research reports vulnerable to showing an internal
walk-forward helper backtest as the primary Backtest Metrics artifact while the
rest of the research loop used the standalone blocker backtest.

## Decision

`generate_research_report` now loads same-symbol `BacktestRun` records and uses
the shared `latest_backtest_for_research` selector.

Selection remains:

1. same-symbol backtests only;
2. prefer decision-blocker standalone backtests by linked run decision basis;
3. fall back to newest same-symbol backtest when no preferred blocker backtest
   exists.

## Impact

- Research reports now align with the decision, digest, dashboard, and operator
  console evidence selection.
- No report schema change.
- No storage format change.
- Walk-forward sections still report the latest walk-forward validation and can
  still summarize linked walk-forward backtest drawdown separately.

## Verification

- Added a regression test that generates a Markdown report with both a newer
  walk-forward-internal backtest and an older standalone decision-blocker
  backtest.
- The report's Backtest Metrics section must show the standalone blocker
  backtest.
