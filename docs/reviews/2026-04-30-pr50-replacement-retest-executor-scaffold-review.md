# PR50 Replacement Retest Executor Scaffold Review

Date: 2026-04-30

Reviewer: Harvey subagent (`019ddad3-2758-75c1-bb0d-7046ffe645cc`)

Branch: `codex/replacement-retest-executor-scaffold`

Scope:

- Let `execute-revision-retest-next-task` execute the first ready retest task,
  `create_revision_retest_scaffold`.
- Use the existing scaffold domain helper and the dataset id selected by
  `revision-retest-plan`.
- Support lineage replacement strategy cards through the PR49 plan/scaffold
  contract.
- Do not add backtest execution, walk-forward execution, strategy promotion,
  paper orders, broker adapters, sandbox execution, live trading, or real-capital
  behavior.

Review result: `APPROVED`

Reviewer notes:

- No blocking findings were found.
- The new executor branch only runs when the next task is
  `create_revision_retest_scaffold` and the plan has a dataset id.
- The executor calls the existing scaffold helper, returns the pending trial id,
  and records the existing `AutomationRun` shape.
- No backtest, walk-forward, promotion, paper/broker/live order path was added.
- Runtime artifact checks were empty.

Verification:

- `python -m pytest tests\test_lineage_research_executor.py::test_execute_revision_retest_next_task_scaffolds_lineage_replacement_card tests\test_lineage_research_executor.py::test_cli_execute_revision_retest_next_task_scaffolds_lineage_replacement_card -q` -> `2 passed`
- `python -m pytest tests\test_research_autopilot.py -k "execute_revision_retest_next_task or revision_retest" -q` -> `42 passed, 17 deselected`
- `python -m pytest -q` -> `409 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> passed with CRLF warnings only
- `git ls-files .codex paper_storage reports output .env` -> empty

Safety status:

- PR50 is scaffold-only executor continuity for the research loop.
- No runtime, storage, output, report, environment, or secret files are intended
  for commit.
