# PR47 Lineage Replacement Strategy Executor

## Purpose

PR43 through PR46 made lineage research agendas, task plans, and task-run logs
visible. PR47 executes the first bounded lineage task:
`draft_replacement_strategy_hypothesis`.

This closes the loop for quarantined lineages by creating a concrete DRAFT
replacement strategy card instead of only showing a worker prompt.

## Behavior

`execute-lineage-research-next-task`:

- builds the current `LineageResearchTaskPlan`;
- requires the next task to be `ready`;
- currently supports only `draft_replacement_strategy_hypothesis`;
- creates an idempotent DRAFT `StrategyCard`;
- links the replacement to the quarantined lineage root and latest
  paper-shadow outcome through card parameters;
- rebuilds the task plan after execution;
- records an `AutomationRun` with the executed task and created artifact id.

If the current task is not supported, the command fails with
`unsupported_lineage_research_task_execution:<task_id>`.

## Replacement Card Contract

Replacement strategy cards use:

- `decision_basis = lineage_replacement_strategy_hypothesis`;
- `status = DRAFT`;
- `parent_card_id = None`, because this is a replacement hypothesis, not a
  child revision;
- `parameters.replacement_source_lineage_root_card_id`;
- `parameters.replacement_source_outcome_id`;
- `parameters.replacement_failure_attributions`;
- `parameters.replacement_not_child_revision = true`.

The lineage task plan treats an existing matching replacement card as task
completion, so a rerun does not create duplicate strategy cards.

## Non-Goals

PR47 does not:

- execute a strategy;
- create paper orders;
- create sandbox or broker orders;
- promote a DRAFT card;
- evaluate the replacement card;
- run backtest, walk-forward, leaderboard, or paper-shadow steps for the
  replacement.

Those remain separate research-loop stages.

## Verification

Tests cover:

- replacement strategy creation from a quarantined lineage;
- after-plan completion once the replacement exists;
- execution `AutomationRun` contents;
- unsupported non-replacement lineage tasks failing closed;
- CLI JSON output and persistence.
