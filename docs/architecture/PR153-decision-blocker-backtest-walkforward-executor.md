# PR153 - Decision Blocker Backtest And Walk-Forward Executor

## Context

`decision-blocker-research-plan` could emit ready `run_backtest` and
`run_walk_forward_validation` tasks, but
`execute-decision-blocker-research-next-task` only supported
`build_event_edge_evaluation`. Active BTC-USD storage reached the ready
`run_backtest` task and then failed with:

```text
unsupported_decision_blocker_research_task_execution:run_backtest
```

That stopped the decision-blocker research loop after event-edge evidence, even
though backtest and walk-forward commands were already planned.

## Decision

Extend the decision-blocker executor to support:

- `run_backtest`
- `run_walk_forward_validation`

Both tasks reuse the plan-generated command arguments for `start`, `end`,
`as-of`, and walk-forward window sizes. This keeps the executor aligned with the
as-of replay semantics already emitted by the planner.

## Traceability

Walk-forward validation creates internal backtest results. The decision-blocker
plan now prefers the backtest whose `BacktestRun.decision_basis` contains the
explicit `decision_blocker_research:run_backtest:backtest_result` context when
marking the `run_backtest` task complete. That prevents walk-forward internal
backtests from overwriting the task artifact shown in the plan.

## Verification

- Added executor tests for backtest execution.
- Added executor tests for walk-forward execution.
- Added a regression test proving the backtest task artifact remains stable
  after walk-forward creates internal backtests.
- Active BTC-USD storage now completes the full decision-blocker plan:
  event-edge -> backtest -> walk-forward.
