# PR19 Revision Retest Run Log UX

PR19 exposes PR18 `record-revision-retest-task-run` output in the read-only
research UX.

## What It Shows

The dashboard and operator console now show the latest revision retest task run
log beside the existing retest task plan:

- automation run id;
- retest task status such as `RETEST_TASK_READY` or `RETEST_TASK_BLOCKED`;
- source command, currently `revision-retest-plan`;
- completion timestamp;
- task-step audit rows from `automation_runs.jsonl`.

## Selection Rule

The UX intentionally selects only automation runs matching all of these fields:

- `symbol` matches the active UX symbol;
- `provider == "research"`;
- `command == "revision-retest-plan"`;
- `decision_basis == "revision_retest_task_plan_run_log"`.

If multiple matching rows exist, the newest `completed_at` row is shown.

## Non-Execution Boundary

This is display-only. Rendering the dashboard or operator console does not run
backtests, walk-forward validations, leaderboard gates, or trial recording
commands. The UI shows command/run evidence only so the operator can see whether
the current retest task plan has been audited recently.

## Why This Matters

PR16 made the retest task plan explicit, PR17 made the plan visible, and PR18
made plan inspection audit-visible. PR19 closes the UX loop by showing that
audit evidence in the same research surface where strategy revisions are
inspected.
