# PR49 Replacement Retest Scaffold

## Purpose

PR47 creates DRAFT lineage replacement strategy cards, and PR48 makes them
visible. PR49 lets those replacement cards enter the existing locked retest
scaffold instead of leaving them as static hypotheses.

The goal is research validation continuity: replacement strategies can move
into the same backtest, walk-forward, leaderboard, and paper-shadow task chain
used by revision candidates.

## Behavior

`create-revision-retest-scaffold` and `revision-retest-plan` now accept DRAFT
strategy cards with:

- `decision_basis = lineage_replacement_strategy_hypothesis`;
- `parameters.replacement_source_outcome_id`;
- `parameters.replacement_source_lineage_root_card_id`;
- `parent_card_id = None`.

For replacement cards, the source paper-shadow outcome must:

- exist;
- match the requested symbol;
- belong to the replacement source lineage;
- have `recommended_strategy_action = QUARANTINE_STRATEGY`.

The generated pending `ExperimentTrial` preserves existing retest compatibility
keys, including `revision_source_outcome_id`, and adds:

- `revision_retest_kind = lineage_replacement`;
- `replacement_source_lineage_root_card_id`.

## Compatibility

The command name remains `create-revision-retest-scaffold` for now because the
downstream task plan and executor are already wired to the revision retest
schema. PR49 broadens the accepted strategy card type without introducing a
parallel retest pipeline.

Existing revision cards still work unchanged.

## Non-Goals

PR49 does not:

- rename the revision retest command;
- execute backtests or walk-forward validation;
- evaluate leaderboard gates;
- record paper-shadow outcomes;
- promote strategies;
- create paper, sandbox, broker, or live orders.

## Verification

Tests cover:

- replacement strategy cards starting a retest scaffold;
- CLI scaffold creation for replacement cards;
- `revision-retest-plan` resolving the replacement card and next
  `lock_evaluation_protocol` task;
- existing revision and lineage regressions.
