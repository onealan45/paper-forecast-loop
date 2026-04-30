# PR46 Lineage Research Task Run Log UX

## Purpose

PR45 records lineage research task-plan inspections as `AutomationRun`
artifacts. PR46 makes the latest matching run log visible in the dashboard and
operator console strategy research pages.

## Selection

Both UX snapshots now expose:

```text
latest_lineage_research_task_run
```

The selected run must:

- match the current `LineageResearchTaskPlan`;
- use `provider = research`;
- use `command = lineage-research-plan`;
- use `decision_basis = lineage_research_task_plan_run_log`;
- reference the current lineage agenda and root strategy in its steps;
- match the current `latest_lineage_outcome` step exactly, including the
  absent-outcome case where both the run and task plan have no latest outcome.

If no matching run exists, the field is `None` and no panel is rendered.
This prevents a run recorded for an older same-lineage outcome from being
displayed after a newer outcome changes the current task plan.

## UI

Dashboard and operator console render:

- run status;
- run id;
- command;
- completed timestamp;
- recorded steps.

The panel is read-only. It does not execute task commands or mutate artifacts.

## Non-Goals

PR46 does not:

- create a lineage task run log;
- execute the next lineage task;
- change task-plan routing;
- mutate strategy cards or research agendas;
- create paper, sandbox, broker, or live orders.

## Verification

Tests cover dashboard and operator console visibility for a recorded
`LINEAGE_RESEARCH_TASK_READY` run log next to a quarantined lineage task plan,
plus negative regressions where an older same-lineage run is hidden after a
newer lineage outcome changes the current task plan. Unit coverage also checks
present and absent `latest_lineage_outcome` matching.
