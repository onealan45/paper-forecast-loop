# PR141 Decision Blocker Research Executor

## Problem

PR140 made the next decision-blocker research task machine-readable, but the
loop still stopped at a plan. Event-edge evaluation is the first safe evidence
builder because it does not require the system to invent backtest or
walk-forward windows.

## Decision

Add `execute-decision-blocker-research-next-task` and
`decision_research_executor.py`.

The executor:

- builds the current `DecisionBlockerResearchTaskPlan`;
- requires the next task to be `ready`;
- supports only `build_event_edge_evaluation`;
- calls the existing `build_event_edge_evaluations` builder;
- refuses zero-artifact executions;
- rebuilds the plan so the event-edge task becomes completed when a same-symbol
  event-edge evaluation exists after the blocker agenda;
- records an `AutomationRun` with the agenda, optional decision id, and created
  event-edge artifact.

## Scope

This PR deliberately does not run backtests, infer walk-forward windows, mutate
strategy cards, place orders, or call broker/exchange adapters. Windowed
validation remains blocked until a later planner/executor can supply explicit
research windows.

## Verification

Regression coverage proves:

- executing the next supported task creates an event-edge evaluation;
- the after-plan advances from event-edge to the blocked walk-forward task;
- an `AutomationRun` records the execution;
- blocked walk-forward tasks are rejected instead of executed;
- the CLI returns JSON with before/after plans and created artifact ids.
