# PR47 Lineage Replacement Strategy Executor Review

## Scope

Branch: `codex/lineage-replacement-strategy-executor`

PR47 adds `execute-lineage-research-next-task` for the quarantined-lineage
replacement path. It executes only `draft_replacement_strategy_hypothesis`,
creates a DRAFT replacement strategy card, and records the execution as an
`AutomationRun`.

## Reviewer

- Reviewer subagent: Harvey
- Role: reviewer
- Result: APPROVED

## Reviewer Notes

Harvey found no blocking findings.

The reviewer confirmed:

- the executor is limited to the quarantined-lineage replacement task;
- it writes only the DRAFT replacement strategy card plus an `AutomationRun`;
- it does not introduce live, broker, order, or secret paths;
- the replacement card is linked to the lineage root and latest paper-shadow
  outcome;
- the task plan treats an existing replacement as task completion.

## Verification

Latest local verification:

```powershell
python -m pytest tests\test_lineage_research_executor.py tests\test_lineage_research_plan.py -q
```

Result: `15 passed`

```powershell
python -m pytest tests\test_dashboard.py tests\test_operator_console.py -k "lineage_research or strategy_lineage" -q
```

Result: `16 passed, 44 deselected`

```powershell
python -m pytest tests\test_research_autopilot.py -k "revision_retest_next_task or propose_strategy_revision" -q
```

Result: `8 passed, 51 deselected`

```powershell
python -m pytest -q
```

Result: `402 passed`

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
```

Result: passed with no output.

```powershell
python .\run_forecast_loop.py --help
```

Result: passed and includes `execute-lineage-research-next-task`.

```powershell
git diff --check
```

Result: exit 0. PowerShell displayed expected CRLF warnings only.

```powershell
git ls-files .codex paper_storage reports output .env
```

Result: empty.

## Decision

APPROVED. PR47 may proceed to commit, push, PR creation, CI, and merge if final
gates remain green.
