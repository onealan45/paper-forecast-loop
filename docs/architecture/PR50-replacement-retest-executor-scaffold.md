# PR50 Replacement Retest Executor Scaffold

Date: 2026-04-30

## Context

PR49 allowed DRAFT `lineage_replacement_strategy_hypothesis` cards to use the
existing revision retest scaffold and plan. The remaining gap was executor
continuity: `execute-revision-retest-next-task` could run later retest tasks,
but rejected the first ready task, `create_revision_retest_scaffold`.

That forced replacement retests back into a manual CLI call even after the plan
identified a ready scaffold step.

## Decision

`execute-revision-retest-next-task` now supports the first scaffold task:

- it builds the current `revision-retest-plan`;
- when the next ready task is `create_revision_retest_scaffold`, it calls the
  existing `create_revision_retest_scaffold` domain helper;
- it uses the dataset id already selected by the plan;
- it records the normal `AutomationRun` with
  `command = execute-revision-retest-next-task`;
- it returns the created or existing retest trial id in `created_artifact_ids`.

This applies to both traditional revision cards and lineage replacement cards
because both now share the same retest contract.

## Non-Goals

- No backtest execution is added in this PR.
- No walk-forward execution is added in this PR.
- No strategy promotion is added.
- No paper order, broker, sandbox, live order, or real-capital path is added.
- No replacement-only retest pipeline is introduced.

## Operational Effect

The replacement path can now move from:

1. quarantined lineage;
2. DRAFT replacement strategy hypothesis;
3. ready retest plan;
4. pending retest scaffold;

through one executor command, as long as a research dataset artifact exists.
The later retest tasks remain governed by the existing chain and gates.

## Verification

- Added coverage that a lineage replacement card with an available research
  dataset can be scaffolded by `execute_revision_retest_next_task`.
- Added CLI coverage for `execute-revision-retest-next-task` on the same
  replacement-card scaffold step.
- Existing PR49 validations still cover source outcome lineage and
  `QUARANTINE_STRATEGY` requirements.
