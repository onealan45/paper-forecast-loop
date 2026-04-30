# PR74: Lineage Run Log Required Artifact

## Context

Lineage research task run logs already captured the next task prompt, rationale,
blocked reason, and missing inputs. A downstream research worker could
understand why the loop was blocked, but the expected output artifact type still
had to be recovered from the full task plan.

## Decision

Whenever `record-lineage-research-task-run` has a next task, the automation run
steps now include:

- `next_task_required_artifact`

The step status matches the next task status, and its artifact id stores the
task's `required_artifact` value, such as `research_agenda` or
`research_autopilot_run`.

This keeps the existing `AutomationRun.steps` shape and does not change task
plan artifacts.

## Verification

- `python -m pytest .\tests\test_lineage_research_plan.py::test_record_lineage_research_task_run_logs_replacement_next_task_context .\tests\test_lineage_research_plan.py::test_record_lineage_research_task_run_logs_blocked_next_task_context -q`
- `python -m pytest .\tests\test_lineage_research_plan.py -q`

