# PR30: Revision Retest Autopilot Run UX

## Context

PR29 added `record-revision-retest-autopilot-run`, which records a completed
DRAFT revision retest chain as a `ResearchAutopilotRun` without requiring a
fake next-horizon strategy decision. That closed the artifact path, but the
operator still had to inspect `research_autopilot_runs.jsonl` to see that the
self-evolution loop had been recorded.

## Decision

The dashboard and operator console now carry a separate
`latest_strategy_revision_retest_autopilot_run` snapshot field. It is selected
only when the run:

- matches the latest DRAFT revision card id
- uses `decision_basis == "research_paper_autopilot_loop"`
- has no `strategy_decision_id`
- has a linked `paper_shadow_outcome_id`

The normal strategy autopilot run remains separate. Parent strategy research
loops are not mislabeled as revision retest evidence.

## UX Behavior

The read-only strategy surfaces now show:

- run id
- loop status
- next research action
- blocked reasons
- linked paper-shadow outcome
- recorded steps

This appears next to the retest task plan and retest task run log. It is
inspection-only and does not execute tasks, mutate strategy cards, promote
strategies, or submit orders.

## Verification

Regression tests cover both surfaces:

- dashboard renders the latest revision retest autopilot run
- operator console research and overview pages render the same run

The targeted test command is:

```powershell
python -m pytest tests\test_dashboard.py tests\test_operator_console.py -k "revision_retest_autopilot_run" -q
```
