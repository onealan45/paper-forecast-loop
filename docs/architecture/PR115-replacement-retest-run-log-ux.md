# PR115 Replacement Retest Run Log UX

## Problem

The active replacement retest can be inspected with
`record-revision-retest-task-run` while it is waiting for a complete
post-leaderboard shadow observation window. That writes an audit-visible
`AutomationRun` with status such as `RETEST_TASK_BLOCKED`.

Before PR115, replacement retest panels displayed only the latest
`execute-revision-retest-next-task` run. A newer read-only inspection run could
exist in storage but remain invisible in the replacement strategy UX, leaving the
operator with an older executor run and no clear evidence that the current
blocked state had been checked.

## Decision

Dashboard and operator console replacement retest panels now select the latest
retest activity across:

- executor runs from `execute-revision-retest-next-task`
- read-only task-plan inspection runs from `record-revision-retest-task-run`

The selected run is rendered as `Latest Retest Activity`, not `Latest Executor
Run`, because it may represent either execution or inspection.

## Boundary

This is UX selection only. It does not change how automation runs are written,
how retest plans are built, how executor gates work, or how paper-shadow
outcomes are recorded.

## Active Storage Example

The active BTC-USD replacement retest has a newer inspection run:

- `automation-run:2f9e51a4f448666e`
- status: `RETEST_TASK_BLOCKED`

That run should now be visible in the replacement retest panel instead of being
hidden behind the older executor run `automation-run:1803caba704319b4`.

## Acceptance

- Replacement retest panels prefer the newest matching activity run by
  `completed_at`.
- Existing executor-only replacement panels still show executor runs.
- The UI label reflects activity rather than execution-only semantics.
- No runtime artifacts are committed.
