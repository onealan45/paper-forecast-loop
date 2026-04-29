# PR17 Revision Retest Task Plan UX

## Purpose

PR17 makes the PR16 revision retest task plan visible in the read-only
inspection surfaces. The user can now see the next concrete research task for a
DRAFT strategy revision without reading JSONL or running the planner CLI
manually.

## Surfaces

The static dashboard and local operator console now show:

- next retest research task ID;
- task status;
- required artifact;
- blocked reason;
- missing inputs;
- command arguments when the task is runnable.

This is shown inside the existing strategy revision / retest scaffold sections.

## Boundary

The UX remains read-only. It does not:

- execute `revision-retest-plan`;
- execute command args;
- run backtests or walk-forward validation;
- create PASSED trials;
- create locked evaluation results;
- create leaderboard entries;
- record paper-shadow outcomes.

The command args are displayed for inspection and future research automation,
not executed by the dashboard or operator console.

## Failure Behavior

If the planner cannot resolve a valid DRAFT revision/source chain, the UX falls
back to the existing revision candidate details and shows that no task plan is
available. Rendering should not fail just because the planning chain is
incomplete.

## Tests

PR17 adds regression tests proving that both dashboard and operator console show
the next retest task plan, including command args for a split-locked but
cost-model-missing retest scaffold.
