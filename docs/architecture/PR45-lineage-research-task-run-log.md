# PR45 Lineage Research Task Run Log

## Purpose

PR43 introduced the read-only `lineage-research-plan` CLI and PR44 surfaced the
same plan in the UX. PR45 records the current lineage task-plan inspection as an
`AutomationRun` so the self-evolving research loop has an auditable trace of the
next strategy work item it inspected.

## Command

```powershell
python run_forecast_loop.py record-lineage-research-task-run --storage-dir .\paper_storage\manual-coingecko --symbol BTC-USD
```

Optional timestamp:

```powershell
python run_forecast_loop.py record-lineage-research-task-run --storage-dir .\paper_storage\manual-coingecko --symbol BTC-USD --now 2026-04-30T11:00:00+00:00
```

## Behavior

The command:

- builds the same `LineageResearchTaskPlan` as `lineage-research-plan`;
- writes one `AutomationRun` row to `automation_runs.jsonl`;
- uses `provider = research`;
- uses `command = lineage-research-plan`;
- uses `decision_basis = lineage_research_task_plan_run_log`;
- stores steps for lineage agenda, root strategy, latest lineage outcome when
  present, and every task in the plan.

Run status is derived from the next task:

- `LINEAGE_RESEARCH_TASK_READY`
- `LINEAGE_RESEARCH_TASK_BLOCKED`
- `LINEAGE_RESEARCH_TASK_COMPLETE`
- `LINEAGE_RESEARCH_TASK_IN_PROGRESS`

## Non-Goals

PR45 does not:

- execute the next task;
- create or mutate strategy cards;
- create lineage research agendas;
- create paper orders, broker orders, sandbox orders, or live orders;
- add dashboard rendering for the new run log.

## Verification

Tests cover:

- recording a ready `propose_strategy_revision` lineage task plan;
- recording a blocked `collect_lineage_shadow_evidence` plan;
- proving the ready plan changes only `automation_runs.jsonl`;
- CLI JSON output and persistence.
