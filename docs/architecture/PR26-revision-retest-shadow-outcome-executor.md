# PR26 Revision Retest Shadow Outcome Executor

## Purpose

PR26 extends `execute-revision-retest-next-task` so the revision retest chain can
close a `record_paper_shadow_outcome` task when, and only when, the caller
provides explicit shadow-window observation inputs.

The supported task is:

- `record_paper_shadow_outcome`

The task planner still reports this task as blocked by default because the
system must not fabricate future returns.

## Execution Boundary

The executor may override the blocked task only when all required inputs are
present:

- `shadow_window_start`
- `shadow_window_end`
- `shadow_observed_return`
- `shadow_benchmark_return`

Optional inputs:

- `shadow_max_adverse_excursion`
- `shadow_turnover`
- `shadow_note`

The override is allowed only for `blocked_reason ==
"shadow_window_observation_required"`. Other blocked states remain rejected.

## Execution Flow

When the current revision retest plan reports
`next_task_id == "record_paper_shadow_outcome"`:

1. Without explicit observation inputs, the executor keeps returning
   `revision_retest_next_task_not_ready`.
2. With required observation inputs, it calls the existing
   `record_paper_shadow_outcome` domain function using the plan-linked
   leaderboard entry id.
3. The domain function writes one `PaperShadowOutcome`.
4. The executor records an execution `AutomationRun`.
5. It returns before/after revision retest plans and the created outcome id.

The expected after-plan transition is:

```text
record_paper_shadow_outcome -> complete
```

## Still Blocked

PR26 deliberately does not:

- fabricate shadow-window returns;
- pull provider data automatically for the observation window;
- execute arbitrary command args;
- shell out or run subprocess commands;
- trade or submit orders.

## Research Meaning

This lets an externally observed shadow window close the revision retest loop
and feed the existing paper-shadow learning path. It is still a research artifact
flow; it does not promote or execute a strategy by itself.

## Verification

Covered behavior:

- missing observation inputs keep the shadow task blocked;
- explicit observation inputs write exactly one paper shadow outcome;
- the outcome links the current revision leaderboard entry;
- after-plan has no remaining next task;
- CLI returns JSON with the created outcome id.

Primary focused command:

```powershell
python -m pytest .\tests\test_research_autopilot.py -k "shadow_outcome_next_task or shadow_outcome_requires_observation_inputs" -q
```
