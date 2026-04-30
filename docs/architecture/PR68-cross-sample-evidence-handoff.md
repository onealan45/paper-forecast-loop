# PR68: Cross-Sample Evidence Handoff

## Context

PR67 made blocked cross-sample validation tasks list the missing evidence
inputs. The remaining handoff gap was the worker prompt: it still described the
task generically, so the next research/autopilot worker had to inspect raw
artifacts to know which agenda, lineage, strategy cards, and latest outcome were
being validated.

## Decision

When `record_cross_sample_autopilot_run` is blocked, the task prompt now names:

- the cross-sample agenda id;
- the source lineage root card;
- the agenda strategy card ids;
- the latest lineage outcome id;
- the expected fresh-sample evidence artifacts.

The prompt remains non-executing: it tells the next worker what evidence chain
must exist before recording the linked research autopilot run, but it does not
invent placeholder command arguments or fake artifact ids.

## Verification

- `python -m pytest .\tests\test_lineage_research_plan.py::test_lineage_research_task_plan_marks_cross_sample_task_complete_when_agenda_exists -q`
- `python -m pytest .\tests\test_lineage_research_plan.py -q`

