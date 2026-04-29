# PR29: Revision Retest Autopilot Run CLI

## Context

PR28 allowed completed DRAFT revision retest chains to be recorded as
`ResearchAutopilotRun` without creating a fake next-horizon strategy decision.
However, the operator still had to manually copy agenda, trial, locked
evaluation, leaderboard, and paper-shadow outcome IDs.

That made the closed research loop too awkward to use from the CLI.

## Change

PR29 adds `record_revision_retest_autopilot_run` and the CLI command:

```powershell
python run_forecast_loop.py record-revision-retest-autopilot-run --storage-dir <path> --revision-card-id <id> --symbol BTC-USD --now <timestamp>
```

The helper builds the current revision retest task plan, requires that the plan
is complete, resolves the linked revision agenda, and records a
`ResearchAutopilotRun` without a strategy decision ID.

## Failure Behavior

The command refuses to record when the revision retest chain is incomplete. It
reports missing plan evidence such as:

- next task still pending or blocked
- missing PASSED retest trial
- missing locked evaluation
- missing leaderboard entry
- missing paper-shadow outcome

## Non-Goals

- No retest executor behavior changed.
- No automatic strategy promotion.
- No fake strategy decision artifact.
- No broker, sandbox, live order, or real-capital path.

## Verification

Regression tests cover:

- helper records the latest completed revision retest chain;
- CLI prints both the revision retest task plan and created autopilot run;
- the run has `strategy_decision_id=None`;
- existing PR28 missing-decision behavior remains covered.
