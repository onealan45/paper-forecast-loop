# PR136 Repair Retest Dependent Artifacts

## Problem

PR135 can quarantine a context-polluted PASSED retest trial from active
`experiment_trials.jsonl`. In active storage this exposed a second-layer
integrity problem: downstream artifacts may still reference the quarantined
trial, causing health-check findings such as:

- `locked_evaluation_missing_trial`
- `leaderboard_entry_missing_trial`
- `paper_shadow_outcome_missing_experiment_trial`
- `research_autopilot_run_missing_experiment_trial`

That is still the same polluted evidence claim. Leaving those rows active makes
the repair incomplete.

## Decision

`repair-storage` now treats retest-context quarantine as a small evidence-chain
quarantine. It identifies bad retest trial ids from both:

- newly detected context-polluted PASSED retest trials; and
- existing `quarantine/retest_context_experiment_trials.jsonl` rows.

It then cascades quarantine to active dependent artifacts that reference those
trial ids or the already-quarantined dependent ids:

- `locked_evaluation_results.jsonl`
- `leaderboard_entries.jsonl`
- `paper_shadow_outcomes.jsonl`
- `research_autopilot_runs.jsonl`

Each artifact type is appended once to a dedicated quarantine file:

```text
quarantine/retest_context_locked_evaluation_results.jsonl
quarantine/retest_context_leaderboard_entries.jsonl
quarantine/retest_context_paper_shadow_outcomes.jsonl
quarantine/retest_context_research_autopilot_runs.jsonl
```

The repair report adds:

- `quarantined_retest_dependent_artifact_count`
- `retest_dependent_quarantine_paths`

## Scope

This does not quarantine the underlying backtest or walk-forward rows. Those
artifacts may still be useful as raw research runs; only the active claim that
they belong to a PASSED retest evidence chain is removed.

## Verification

Regression coverage now proves:

- a newly quarantined bad retest trial also removes its dependent locked
  evaluation, leaderboard, paper-shadow, and research-autopilot rows;
- a later repair can use an existing retest-trial quarantine file to remove
  dangling downstream rows even when the bad trial is no longer active.
