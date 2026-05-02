# PR142 Event-Edge Prerequisite Plan Blocking

## Problem

PR141 correctly refused to record successful execution when event-edge building
created no artifacts. The active storage then exposed an earlier planning
problem: `decision-blocker-research-plan` could mark
`build_event_edge_evaluation` as `ready` even when the storage had no
same-symbol canonical events or market reaction checks.

That made the next task look executable even though the executor would
fail-closed with `decision_blocker_research_task_created_no_artifacts`.

## Decision

The planner now checks event-edge prerequisites before emitting a runnable
command.

`build_event_edge_evaluation` is `ready` only when all are present:

- same-symbol canonical events available at or before plan time;
- the latest market reaction check for at least one available event is passed;
- same-symbol market candles imported at or before plan time include exact
  event-timestamp and horizon-end candles for at least one latest-passed
  reaction.

If any prerequisite is missing, the task remains the next task but becomes
`blocked` with:

- `blocked_reason = missing_event_edge_inputs`
- `command_args = null`
- `missing_inputs` listing the absent artifact families.

## Scope

This PR does not import events, create market reactions, generate source
documents, infer walk-forward windows, or execute research. It only prevents a
false-ready plan from being emitted.

## Verification

Regression coverage proves:

- event-edge tasks stay ready when the required inputs exist;
- event-edge tasks are blocked when canonical events, market reactions, and
  candles are missing;
- event-edge tasks are blocked when an older passed reaction is superseded by a
  newer failed reaction;
- event-edge tasks are blocked when candles exist but do not cover the exact
  event timestamp and horizon boundary required by the builder;
- CLI JSON reflects the same readiness contract;
- executor and event-edge builder regressions still pass.
