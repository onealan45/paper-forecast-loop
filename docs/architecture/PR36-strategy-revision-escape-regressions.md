# PR36: Strategy Revision Escape Regressions

## Context

PR35 made strategy revision change summaries readable in the dashboard and
operator console. The final reviewer accepted the change and noted that the
escape behavior was code-reviewed but not protected by malicious HTML fixtures.

This matters because the user intentionally controls strategy ideas with
natural language, and future agents may generate broad strategy hypotheses.
Those fields must remain display-safe in read-only UX.

## Decision

Add dashboard and operator-console regression tests using malicious HTML in:

- revision strategy name;
- revision hypothesis;
- revision source outcome id;
- intended failure attribution / fix label.

The tests prove raw `<script>` strings do not appear in rendered HTML and that
the escaped text is visible instead.

No production code change was needed because the existing dashboard and
operator-console rendering paths already escape the displayed fields.

## Scope

This PR only adds regression tests and documentation. It does not change
strategy generation, strategy mutation, retest execution, broker behavior, or
order paths.

## Verification

Targeted command:

```powershell
python -m pytest tests\test_dashboard.py::test_dashboard_strategy_lineage_escapes_revision_change_summary tests\test_operator_console.py::test_operator_console_strategy_lineage_escapes_revision_change_summary -q
```

Full gate remains:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
git ls-files .codex paper_storage reports output .env
```
