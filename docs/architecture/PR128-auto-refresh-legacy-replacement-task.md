# PR128: Auto Refresh Legacy Replacement Task

## Context

PR127 added an append-only command to refresh legacy DRAFT lineage replacement
cards into failure-aware successor cards. That fixed the active storage when run
manually, but the autonomous lineage task plan still treated any existing
replacement card as a completed `draft_replacement_strategy_hypothesis` task.
Future old-template replacement cards could therefore remain generic unless an
operator knew to run the refresh command.

## Decision

Lineage task planning now detects replacement cards that lack
`replacement_strategy_archetype`. When the latest replacement for a source
outcome is still legacy-format, the next task becomes
`refresh_replacement_strategy_hypothesis`.

`execute-lineage-research-next-task` can execute that task by calling the PR127
refresh helper. It writes a new successor `StrategyCard`; it does not mutate the
old card, copy stale evidence IDs, promote the strategy, or run broker/exchange
execution.

Once the refreshed successor exists, the plan resolves the source outcome to the
newest replacement card and marks `draft_replacement_strategy_hypothesis`
complete against that successor.

## Scope

Included:

- lineage task-plan routing for legacy replacement refresh;
- lineage executor support for `refresh_replacement_strategy_hypothesis`;
- regression tests for plan routing and executor-created refreshed successors;
- README / PRD updates.

Excluded:

- changing existing retest gates;
- automatically creating paper-shadow outcomes;
- overwriting legacy strategy cards;
- live trading, broker execution, or real-order support.

## Verification

- `python -m pytest tests\test_lineage_research_plan.py::test_lineage_research_task_plan_routes_legacy_replacement_to_refresh_task -q`
- `python -m pytest tests\test_lineage_research_executor.py::test_execute_lineage_research_next_task_refreshes_legacy_replacement_strategy_card -q`
- `python -m pytest tests\test_strategy_evolution.py tests\test_lineage_research_plan.py tests\test_lineage_research_executor.py tests\test_strategy_lineage.py tests\test_strategy_research_digest.py tests\test_dashboard.py::test_dashboard_shows_lineage_replacement_strategy_hypothesis tests\test_operator_console.py::test_operator_console_shows_lineage_replacement_strategy_hypothesis -q`
