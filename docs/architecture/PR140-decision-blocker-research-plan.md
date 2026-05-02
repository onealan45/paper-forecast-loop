# PR140 Decision Blocker Research Plan

## Problem

PR139 persists `decision_blocker_research_agenda` artifacts from the latest
strategy decision blockers. Those agendas identify the missing evidence, but
the next worker still had to inspect the agenda manually to decide which command
to run.

The Alpha Factory loop needs a machine-readable handoff from blocker agenda to
next research task.

## Decision

Add a read-only `decision-blocker-research-plan` command and
`decision_research_plan.py`.

The planner:

- selects the latest same-symbol `decision_blocker_research_agenda`;
- extracts blocker labels from the latest same-symbol decision when available,
  otherwise from the agenda hypothesis;
- emits a completed agenda-resolution task;
- prioritizes `event_edge_evaluation` before windowed validation because it can
  produce a safe command without choosing train/test windows;
- emits a ready `build-event-edge` command when event-edge evidence is expected;
- emits blocked backtest and walk-forward tasks when safe `start` / `end`
  windows are missing.

## Scope

This PR is read-only planning. It does not execute research, mutate strategies,
loosen BUY/SELL gates, create orders, or submit broker requests.

Execution of supported decision-blocker tasks is intentionally deferred until
the planning contract is stable.

## Verification

Regression coverage proves:

- the planner chooses the latest same-symbol decision-blocker agenda;
- event-edge blockers produce a ready `build-event-edge` command;
- walk-forward blockers without windows stay blocked with explicit missing
  inputs;
- the CLI returns JSON with the plan;
- missing agendas produce an operator-friendly CLI error.
