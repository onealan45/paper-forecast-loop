# PR46 Lineage Research Task Run Log UX Review

## Scope

Branch: `codex/lineage-research-task-run-log-ux`

PR46 surfaces the latest matching lineage research task run log in the static
dashboard and local operator console. The panel is read-only and is displayed
beside the current lineage research task plan.

## Reviewer

- Reviewer subagent: Harvey
- Role: reviewer
- Result: APPROVED after one fix pass

## Initial Finding

Harvey found one P2 issue:

- stale lineage task runs could match a newer task plan when the same lineage
  received a newer paper-shadow outcome after the run was recorded.

The issue was valid because the first matcher only checked symbol, provider,
command, decision basis, lineage agenda, and root strategy. It did not include
the current task plan's `latest_lineage_outcome` identity.

## Fix

The matcher now requires the automation run's `latest_lineage_outcome` step to
match `LineageResearchTaskPlan.latest_outcome_id` exactly. This covers both
present and absent outcome cases.

Regression coverage was added for:

- dashboard hides an older same-lineage run after a newer lineage outcome
  changes the current task plan;
- operator console hides the same stale run;
- run-log tests cover present `latest_lineage_outcome` matching;
- run-log tests cover the absent-outcome case.

## Final Reviewer Notes

Harvey approved the follow-up review:

- the prior stale-run issue is addressed;
- dashboard/operator selection now uses a matcher that includes
  `latest_lineage_outcome`;
- no blocking findings remain.

## Verification

Latest local verification:

```powershell
python -m pytest tests\test_dashboard.py::test_dashboard_lineage_research_task_run_ignores_stale_run_after_new_outcome tests\test_operator_console.py::test_operator_console_lineage_research_task_run_ignores_stale_run_after_new_outcome -q
```

Result: `2 passed`

```powershell
python -m pytest tests\test_dashboard.py tests\test_operator_console.py -k "lineage_research or strategy_lineage" -q
```

Result: `16 passed, 44 deselected`

```powershell
python -m pytest tests\test_lineage_research_plan.py -q
```

Result: `12 passed`

```powershell
python -m pytest -q
```

Result: `399 passed`

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
```

Result: passed with no output.

```powershell
python .\run_forecast_loop.py --help
```

Result: passed and includes `record-lineage-research-task-run`.

```powershell
git diff --check
```

Result: exit 0. PowerShell displayed expected CRLF warnings only.

```powershell
git ls-files .codex paper_storage reports output .env
```

Result: empty.

## Decision

APPROVED. PR46 may proceed to commit, push, PR creation, CI, and merge if final
gates remain green.
