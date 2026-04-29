# PR37 Strategy Lineage Performance Trajectory Review

## Scope

- Date: 2026-04-30
- Branch: `codex/strategy-lineage-performance-trajectory`
- Scope: strategy lineage outcome trajectory, dashboard/operator console visibility, docs, and regression coverage.
- Reviewer source: subagent reviewer `Harvey` (`019ddad3-2758-75c1-bb0d-7046ffe645cc`), per `AGENTS.md` rule that review must be performed by subagent rather than self-review.

## Findings

### P2 - Fixed

- `src/forecast_loop/strategy_lineage.py`: missing `excess_return_after_costs` was originally displayed as `基準` when no previous numeric excess existed. That made missing evidence look like a valid baseline and could produce multiple baseline labels.
- Resolution: `current_excess=None` now displays `未知`; `基準` is reserved for the first known numeric excess value.
- Regression: `test_strategy_lineage_outcome_nodes_do_not_treat_missing_excess_as_baseline`.

## Reviewer Result

- Initial review: `CHANGES REQUESTED`
- Follow-up review after fix: `PASS`
- Reviewer noted no new live order, broker, runtime artifact, or secret risk.

## Verification

```powershell
python -m pytest tests\test_strategy_lineage.py tests\test_dashboard.py tests\test_operator_console.py -q
```

Result: `57 passed`

```powershell
python -m pytest -q
```

Result: `376 passed`

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
```

Result: passed

```powershell
python .\run_forecast_loop.py --help
```

Result: passed

```powershell
git diff --check
```

Result: passed

```powershell
git ls-files .codex paper_storage reports output .env
```

Result: no tracked runtime or secret paths.

## Merge / Automation Impact

- Blocking findings: none after fix.
- Merge impact: PR37 may proceed after final local gates and GitHub PR checks pass.
- Automation impact: no automation status change requested by this review.
