# PR51 Replacement Retest Scaffold UX Review

Date: 2026-04-30

Reviewer: Harvey subagent (`019ddad3-2758-75c1-bb0d-7046ffe645cc`)

Branch: `codex/replacement-retest-scaffold-ux`

Scope:

- Show lineage replacement retest scaffold state in dashboard and operator
  console.
- Add replacement-specific snapshot fields for retest task plan and latest
  executor run.
- Keep the existing traditional revision-candidate UX wiring unchanged.
- Do not add execution, backtest, walk-forward, promotion, paper order, broker,
  sandbox, live trading, or real-capital behavior.

Review result: `APPROVED`

Reviewer notes:

- Replacement retest plan/run fields are independent snapshot fields.
- Existing revision-candidate panel still uses the original
  `latest_strategy_revision_retest_*` wiring and is not overwritten by the
  replacement path.
- `_latest_revision_retest_executor_run` matches by symbol, provider, command,
  decision basis, `revision_card` step, and `source_outcome` step, which is
  specific enough for the current executor run identity.
- The replacement panel only shows scaffold/trial/dataset/next-task/latest
  executor-run status and explicitly states that this does not mean the strategy
  passed, was promoted, or placed an order.
- No dashboard/operator console execution, broker/order/live, or secret path was
  added.

Verification:

- `python -m pytest tests\test_dashboard.py::test_dashboard_shows_lineage_replacement_retest_scaffold tests\test_operator_console.py::test_operator_console_shows_lineage_replacement_retest_scaffold -q` -> `2 passed`
- `python -m pytest tests\test_dashboard.py tests\test_operator_console.py -k "lineage_replacement or replacement_retest" -q` -> `4 passed`
- `python -m pytest tests\test_lineage_research_executor.py -q` -> `8 passed`
- `python -m pytest -q` -> `411 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> passed with CRLF warnings only
- `git ls-files .codex paper_storage reports output .env` -> empty

Safety status:

- PR51 is read-only UX visibility for replacement retest scaffold state.
- No runtime, storage, output, report, environment, or secret files are intended
  for commit.
