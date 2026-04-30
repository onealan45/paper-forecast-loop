# PR57 Lineage Task Run Context

Date: 2026-04-30

## Context

PR56 made the live `lineage-research-plan` payload replacement-aware, but the
persisted `AutomationRun` only recorded the next task id/status/artifact id.
After reload, an operator or automation reader could see that a lineage task was
ready, but not the exact research instruction or rationale that should guide the
next worker.

For a research-first loop, the task-run artifact should preserve the concrete
strategy research instruction, especially when a replacement retest is the
reason to validate a new hypothesis across samples.

## Decision

`record-lineage-research-task-run` now appends two standard steps whenever a
next task exists:

- `next_task_worker_prompt`
- `next_task_rationale`

Both use the existing persisted `AutomationRun.steps` shape:

- `name`
- `status`
- `artifact_id`

The prompt/rationale text is stored in `artifact_id` because the current
`AutomationRun.from_dict` schema only preserves these three fields. This avoids
introducing a broader step schema migration while making the instruction visible
in existing dashboard and operator-console step renderers.

## Non-Goals

- No automatic execution of the next task is added.
- No strategy promotion rule is changed.
- No order, broker, sandbox, live execution, or real-capital path is added.
- No `AutomationRun.steps` schema migration is introduced in this PR.

## Verification

- Added regression coverage that a replacement-aware
  `verify_cross_sample_persistence` task writes prompt/rationale steps.
- Verified the prompt/rationale survive JSONL reload through
  `AutomationRun.from_dict`.
