# PR135 Repair Retest Evidence Context Artifacts

## Problem

PR134 made `health-check` block PASSED revision/replacement retest trials when
their linked backtest or walk-forward evidence does not carry the matching
retest chain `id_context`. That made the defect visible, but active storage
still needed a repeatable repair path. Manually editing `experiment_trials.jsonl`
would be hard to audit and easy to repeat incorrectly.

## Decision

`repair-storage` now inspects PASSED retest trials using the same context rules
as health-check:

- the trial must use the current `revision_retest_protocol`;
- the trial must have a verifiable `revision_source_outcome_id`;
- linked backtest runs and walk-forward validations must carry an exact
  `id_context` token for the current retest chain;
- same-chain pending source-trial contexts remain valid when the source trial
  belongs to the same card, symbol, dataset, trial index, protocol, and source
  outcome.

When a PASSED retest trial fails those checks, `repair-storage` removes it from
active `experiment_trials.jsonl` and appends it once to:

```text
quarantine/retest_context_experiment_trials.jsonl
```

The repair report adds:

- `quarantined_retest_trial_count`
- `active_experiment_trial_count`
- `latest_experiment_trial_id`
- `retest_trial_quarantine_path`

The command remains idempotent: rerunning it after quarantine does not duplicate
the quarantined trial.

## Scope

This does not rewrite backtest, walk-forward, or strategy-card artifacts. It
quarantines only the invalid PASSED evidence claim so active research and
health-check state no longer treat polluted retest evidence as valid.

## Verification

Regression coverage creates one valid PASSED retest trial and one context-
polluted PASSED retest trial. `repair-storage` must keep the valid trial active,
quarantine the polluted trial, update the report fields, and remove the PR134
health mismatch findings from the repaired storage state.
