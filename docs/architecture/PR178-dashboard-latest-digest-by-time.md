# PR178: Dashboard Latest Digest By Created Time

## Context

PR175 and PR176 made `health-check` validate the latest
`StrategyResearchDigest` per symbol by `created_at`. The operator console also
selects latest digest by `created_at`.

The static dashboard still selected the last JSONL row. If an older digest was
appended later, dashboard/operator-console/health-check could disagree about
which strategy digest is current.

## Decision

Dashboard snapshot construction now selects the latest strategy research
digest by `created_at`, not by file tail.

## Boundaries

- This only changes dashboard digest selection.
- It does not change digest generation, health-check validation, or operator
  console behavior.
- Other dashboard latest fields are left unchanged in this PR.

## Verification

```powershell
python -m pytest tests\test_dashboard.py::test_dashboard_strategy_research_digest_uses_latest_created_at_not_file_tail -q
python -m pytest tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```
