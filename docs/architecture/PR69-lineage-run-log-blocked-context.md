# PR69: Lineage Run Log Blocked Context

## Context

`record-lineage-research-task-run` already persisted the current lineage task
plan and stored the next task worker prompt and rationale in the automation run
steps. After PR67 and PR68, blocked cross-sample tasks became much more
actionable because they carry explicit missing evidence inputs and a concrete
handoff prompt.

The remaining gap was that automation run logs did not persist the blocked
reason or missing input list. A later research worker that only consumed the run
log had to rebuild the task plan to know which evidence was missing.

## Decision

When a lineage research task run has a next task, the run log now keeps the
existing prompt and rationale steps and additionally writes:

- `next_task_blocked_reason` when the next task has a blocked reason;
- `next_task_missing_inputs` when the next task has missing inputs.

The values are stored as step artifact ids to preserve the existing
`AutomationRun.steps` shape and avoid a broader schema migration.

## Verification

- `python -m pytest .\tests\test_lineage_research_plan.py::test_record_lineage_research_task_run_logs_blocked_next_task_context -q`
- `python -m pytest .\tests\test_lineage_research_plan.py::test_record_lineage_research_task_run_logs_replacement_next_task_context -q`

