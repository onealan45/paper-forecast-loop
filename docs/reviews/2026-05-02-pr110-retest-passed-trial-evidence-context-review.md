# PR110 Retest Passed Trial Evidence Context Review

## Scope

- Branch: `codex/pr110-retest-passed-trial-evidence-context`
- Reviewer: subagent `Godel`
- Review mode: blocking-only final review

## Result

APPROVED.

No blocking findings remained after replacing shell-unsafe evidence-context
delimiters with a PowerShell-safe string format.

## Findings

No blocking findings.

## Prior Blocking Findings Resolved

- `;` was unsafe in copyable PowerShell command args.
- `|` was also unsafe because PowerShell treats it as a pipeline operator.
- The final format is:

```text
backtest_<backtest_result_id>__walk_forward_<walk_forward_validation_id>
```

The regression test now rejects PowerShell metacharacters in the planner context
argument.

## Residual Risk

This PR fixes the PASSED trial collision for revision/replacement retest chains
by using evidence-specific parameters. Future schema-level linkage between
experiment trials and evidence artifacts would still be stronger than encoding
evidence identity in parameters.

## Verification Evidence

- `python -m pytest .\tests\test_research_autopilot.py::test_execute_revision_retest_passed_trial_writes_evidence_specific_trial_when_stale_trial_id_exists -q` -> `1 passed`
- `python -m pytest .\tests\test_research_autopilot.py .\tests\test_experiment_registry.py -q` -> `84 passed`
- `python -m pytest -q` -> `480 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> passed
- Active `revision-retest-plan` shows fresh PASSED trial
  `experiment-trial:97e6fc0e81eef8bb` and `next_task_id =
  evaluate_leaderboard_gate`.

## Docs And Tests

Reviewer confirmed tests and docs match implementation:

- planner and executor use the same evidence-context helper
- stale PASSED trial collision is covered
- PowerShell metacharacter exclusion is covered
- docs describe the shell-safe delimiter decision

