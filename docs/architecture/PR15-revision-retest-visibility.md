# PR15 Revision Retest Visibility

## Purpose

PR14 can create a pending retest scaffold for a DRAFT strategy revision. PR15 makes that scaffold visible in the read-only dashboard and operator console.

The goal is not to run the retest. The goal is to make the current self-evolution state inspectable:

- which DRAFT revision is being retested;
- which pending experiment trial is the retest entry point;
- which dataset is assigned;
- whether the split manifest has been locked;
- which downstream evidence artifacts are still required.

## Displayed Fields

The strategy revision panel now shows:

- `Retest Trial`
- `Dataset`
- `Locked Split`
- `Next Required`

`Next Required` is derived from the revision retest state. It can include:

- `experiment_trial`
- `split_manifest`
- `cost_model_snapshot`
- `baseline_evaluation`
- `backtest_result`
- `walk_forward_validation`
- `locked_evaluation_result`
- `leaderboard_entry`
- `paper_shadow_outcome`

## Read-Only Boundary

PR15 writes no runtime artifacts and executes no retest. It only resolves and renders existing artifacts:

- `strategy_cards.jsonl`
- `research_agendas.jsonl`
- `paper_shadow_outcomes.jsonl`
- `experiment_trials.jsonl`
- `split_manifests.jsonl`

No baseline, backtest, walk-forward, locked evaluation, leaderboard, promotion, or order path is created.

## Acceptance

- Dashboard shows the pending revision retest scaffold when present.
- Operator console research and overview pages show the same retest scaffold.
- Existing revision candidate visibility remains intact.
- Tests cover dashboard and operator console visibility.
