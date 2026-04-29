# PR44 Lineage Research Task Plan UX

## Purpose

PR43 made lineage agenda task planning available through the
`lineage-research-plan` CLI. PR44 makes the same next research task visible in
the read-only strategy UX so operators and autonomous workers can see the
concrete next strategy work item without running a separate command.

## UX Surfaces

Dashboard and operator console research pages now include:

- task id and status
- required artifact
- blocked reason
- missing inputs
- command args when the next task is directly runnable
- worker prompt
- rationale

The panel is intentionally read-only. It displays commands and prompts but does
not execute them.

## Snapshot Behavior

Both snapshot builders now resolve:

```text
latest_lineage_research_task_plan
```

The plan is built only when a scoped lineage research agenda exists. If the
agenda or lineage context cannot be resolved, the field is `None` and no panel
is rendered.

## Non-Goals

PR44 does not:

- create a lineage research agenda
- execute a task plan
- write an automation run
- mutate strategy cards
- submit paper, sandbox, or live orders

## Verification

Tests cover dashboard and operator console rendering of a quarantined lineage
task plan, including `draft_replacement_strategy_hypothesis` and the
replacement-strategy worker prompt.
