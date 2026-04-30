# PR49 Replacement Retest Scaffold Review

Date: 2026-04-30

Reviewer: Harvey subagent (`019ddad3-2758-75c1-bb0d-7046ffe645cc`)

Branch: `codex/replacement-retest-scaffold`

Scope:

- Allow existing revision retest scaffold and plan commands to accept DRAFT lineage replacement strategy cards.
- Preserve the existing retest chain and compatibility parameters.
- Avoid adding execution, promotion, paper order, broker, sandbox, live trading, or real-capital behavior.

Initial review result: `CHANGES REQUESTED`

- Finding: `revision-retest-plan` accepted lineage replacement cards whose source outcome was not `QUARANTINE_STRATEGY`, while `create_revision_retest_scaffold` rejected the same card.
- Required change: add the same replacement action validation to `revision_retest_plan._source_outcome`, and add a regression where a replacement card points at a same-lineage `REVISE_STRATEGY` outcome.

Resolution:

- Added `test_replacement_strategy_plan_rejects_non_quarantine_source_outcome`.
- Verified the new test failed before the fix.
- Updated `revision_retest_plan._source_outcome` to reject lineage replacement source outcomes unless `recommended_strategy_action == "QUARANTINE_STRATEGY"`.

Final review result: `APPROVED`

Reviewer notes:

- No remaining blocking findings.
- `revision_retest_plan._source_outcome` now applies `QUARANTINE_STRATEGY` validation for lineage replacement source outcomes, matching scaffold behavior.
- The regression and positive scaffold/CLI tests passed locally.
- No added execution, promotion, paper/broker/live order path, or secret path was found.

Verification:

- `python -m pytest tests\test_lineage_research_executor.py::test_replacement_strategy_plan_rejects_non_quarantine_source_outcome tests\test_lineage_research_executor.py::test_lineage_replacement_strategy_can_start_retest_scaffold tests\test_lineage_research_executor.py::test_cli_create_revision_retest_scaffold_accepts_lineage_replacement_card -q` -> `3 passed`
- `python -m pytest -q` -> `407 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> passed with CRLF warnings only
- `git ls-files .codex paper_storage reports output .env` -> empty

Automation / safety status:

- Review archive complete.
- No runtime, storage, output, report, environment, or secret files are intended for commit.
- PR49 remains research/scaffold only; no live order path is introduced.
