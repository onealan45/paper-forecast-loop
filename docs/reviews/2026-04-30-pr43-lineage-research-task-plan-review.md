# PR43 Lineage Research Task Plan Review

## Scope

Branch: `codex/lineage-research-task-plan`

PR43 adds a read-only `lineage-research-plan` CLI and task planner that turns a
persisted `strategy_lineage_research_agenda` into the next concrete strategy
research task.

## Reviewer

- Reviewer subagent: Harvey
- Role: reviewer
- Result: APPROVED after requested fixes

## Initial Findings

The reviewer found two P2 issues:

- `build_lineage_research_task_plan` selected lineage agendas by decision basis
  and card intersection but did not first filter by requested symbol. A newer
  agenda for another symbol on a shared multi-symbol strategy card could be
  selected.
- The first test pass covered revision and quarantine routing, but not the
  documented improving or insufficient-evidence branches.

## Fixes

- `research_agendas` are now filtered by requested `symbol` before agenda
  selection and before passing agendas into the lineage resolver.
- Added a shared BTC/ETH strategy-card regression proving a newer ETH agenda is
  not selected for a BTC plan.
- Added routing tests for:
  - improving lineage -> `verify_cross_sample_persistence`;
  - insufficient evidence -> `collect_lineage_shadow_evidence`.

## Final Reviewer Notes

Harvey returned `APPROVED` with no blocking or important findings.

Residual reviewer note: Harvey reran the targeted PR43 tests and checked that
forbidden runtime/artifact paths were not tracked. Harvey did not rerun the full
suite and relied on the controller-provided full-suite result.

## Verification

Latest local verification:

```powershell
python -m pytest tests\test_lineage_research_plan.py -q
```

Result: `9 passed`

```powershell
python -m pytest tests\test_strategy_lineage.py tests\test_operator_console.py -k "lineage or revision" -q
```

Result: `24 passed, 14 deselected`

```powershell
python -m pytest tests\test_research_autopilot.py -k "revision or autopilot" -q
```

Result: `59 passed`

```powershell
python -m pytest -q
```

Result: `394 passed`

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
```

Result: passed with no output.

```powershell
python .\run_forecast_loop.py --help
```

Result: passed.

```powershell
git diff --check
```

Result: exit 0. PowerShell displayed expected CRLF warnings only.

```powershell
git ls-files .codex paper_storage reports output .env
```

Result: empty.

## Decision

APPROVED. PR43 may proceed to commit, push, and PR creation if final gates stay
green.
