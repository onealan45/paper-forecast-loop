# PR85: Paper-shadow Attribution Detail Copy Review

## Reviewer

- Harvey (`019ddad3-2758-75c1-bb0d-7046ffe645cc`)

## Scope

Review PR85 changes that make detailed paper-shadow attribution panels reuse
readable Traditional Chinese labels while preserving raw attribution codes.

## Change Summary

- Dashboard detailed `Paper-shadow 歸因` panel now renders readable failure
  attribution copy.
- Operator console detailed `Paper-shadow 歸因` panel now renders the same
  readable failure attribution copy.
- Regression tests assert readable attribution labels inside the detailed
  paper-shadow section, not only in the headline conclusion.
- README, PRD, and architecture notes document the behavior.

## Verification

- `python -m pytest tests/test_dashboard.py::test_dashboard_surfaces_strategy_research_context_before_raw_metadata tests/test_operator_console.py::test_research_page_surfaces_strategy_hypothesis_gates_shadow_and_autopilot -q`
- `python -m pytest -q`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
- `python .\run_forecast_loop.py --help`
- `git diff --check`
- `git ls-files .codex paper_storage reports output .env`

## Final Review

Harvey reviewed the diff and replied: `APPROVED`.
