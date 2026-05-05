# PR154 - Prefer Decision Blocker Standalone Backtest Evidence

## Context

PR153 let the decision-blocker research executor complete:

```text
event-edge -> backtest -> walk-forward
```

Walk-forward validation also creates internal backtests for each validation and
test window. Because those internal backtests can be newer than the standalone
`run_backtest` task artifact, the latest strategy decision and digest could use
an internal walk-forward backtest as the primary `Backtest` evidence.

That made the research plan and the operator-facing evidence disagree:

- plan `run_backtest` task: standalone blocker backtest
- decision / digest `Backtest`: newer walk-forward internal backtest

## Decision

Add a shared research artifact selector for backtest evidence. When a
decision-blocker standalone backtest exists, decision generation,
strategy-research digest, and the decision-blocker plan prefer the
`BacktestRun` whose `decision_basis` contains:

```text
id_context=decision_blocker_research:run_backtest:backtest_result
```

If no such run exists, selection falls back to the latest same-symbol backtest
for legacy compatibility.

## Why

The standalone backtest is the direct artifact for the `run_backtest` research
task. Walk-forward internal backtests are supporting evidence for
walk-forward windows, not the primary backtest result an operator should see as
the blocker-focused backtest.

## Verification

- Added a research-gate regression test proving strategy decisions prefer the
  standalone blocker backtest over a newer walk-forward internal backtest.
- Added a strategy-digest regression test proving digest evidence IDs and
  summary copy use the standalone blocker backtest.
- Active BTC-USD storage now shows:
  - decision `backtest_result=backtest-result:10986a7e8679e68a`
  - digest evidence includes `backtest-result:10986a7e8679e68a`
  - dashboard summary reports the standalone backtest metrics
