# PR25 Revision Retest Leaderboard Gate Executor

## Purpose

PR25 extends `execute-revision-retest-next-task` so the revision retest chain can
advance from a PASSED retest experiment trial to locked evaluation and
leaderboard-entry evidence.

The new supported task is:

- `evaluate_leaderboard_gate`

The executor remains a narrow domain-code whitelist. It does not dispatch shell
commands, does not run arbitrary command arguments from the plan, and does not
execute later retest tasks.

## Execution Flow

When the current revision retest plan reports
`next_task_id == "evaluate_leaderboard_gate"`:

1. The executor requires a PASSED retest trial id, split manifest id, cost model
   id, baseline id, backtest result id, and walk-forward validation id.
2. It calls the existing `evaluate_leaderboard_gate` domain function with those
   plan-linked IDs.
3. The domain function writes one `LockedEvaluationResult` and one
   `LeaderboardEntry`.
4. Weak or incomplete evidence is represented as blocked leaderboard evidence
   rather than a crash.
5. The executor records an execution `AutomationRun`.
6. It returns before/after revision retest plans and both created artifact ids.

The expected after-plan transition is:

```text
evaluate_leaderboard_gate -> record_paper_shadow_outcome
```

## Still Blocked

PR25 deliberately does not execute:

- `record_paper_shadow_outcome`
- arbitrary command args
- shell or subprocess commands

Paper-shadow outcome recording needs a real observed shadow window and its own
narrow executor support before it can run from the retest executor.

## Research Meaning

This turns a PASSED retest trial into auditable leaderboard evidence. It can
produce a blocked leaderboard entry when evidence is weak; that is still useful
research signal because it records exactly why a revision is not rankable.

It does not promote, paper-shadow, or trade the revised strategy.

## Verification

Covered behavior:

- executor writes one locked evaluation result and one leaderboard entry for
  `evaluate_leaderboard_gate`;
- both artifacts link the revision card and PASSED retest trial evidence;
- weak baseline edge is fail-closed as blocked evidence instead of TypeError;
- executor records an execution `AutomationRun`;
- CLI returns JSON with before/after plans and both created artifact ids;
- after-plan advances to `record_paper_shadow_outcome`;
- paper-shadow outcome execution remains blocked.

Primary focused command:

```powershell
python -m pytest .\tests\test_research_autopilot.py -k "leaderboard_gate_next_task or unsupported_ready_task" -q
```
