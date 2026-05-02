# PR133: Reuse Retest Split Windows

## Context

Replacement and revision retests should be comparable against prior candidates
when they use the same research dataset and symbol. The previous planner blocked
new replacement retests at `split_window_inputs_required` even when the storage
already contained a locked split manifest for the same symbol and dataset. That
forced manual date copying and made the self-evolving research loop brittle.

## Decision

When a revision or replacement retest has a pending trial but no locked split
for the current strategy card, the planner may reuse an existing `LOCKED` split
manifest only if it matches:

- the same symbol;
- the same dataset id;
- a different strategy card id.

The reused split is not treated as current-card evidence. It is used only as the
source of train, validation, holdout, and embargo window inputs for a new
`lock-evaluation-protocol` execution. The executor still creates a new locked
split manifest for the current strategy card before backtest and walk-forward
tasks can run.

Backtest and walk-forward selectors also require the evidence to carry the same
revision-retest `id_context`. For completed `PASSED` trials, the accepted context
may come from the source `PENDING` trial only when it belongs to the same
strategy card, symbol, dataset, source outcome, protocol, and trial index.

## Scope

Included:

- Planner support for a ready `lock_evaluation_protocol` task from reusable
  split windows.
- Executor support for creating a current-card split from same-symbol,
  same-dataset reusable windows.
- Regression coverage for command args, new split creation, and unlocked
  backtest readiness after protocol locking.
- Regression coverage proving cross-card backtest and walk-forward evidence is
  rejected for both pending and passed-trial retest paths.

Excluded:

- reusing backtest, walk-forward, leaderboard, or paper-shadow evidence from a
  different strategy card;
- inventing split windows when no matching locked split exists;
- changing trial budgets, research gates, or paper-shadow timing rules.

## Rationale

This keeps the Alpha Factory rule intact: strategy search can evolve, but the
evaluation protocol remains locked and comparable. Reusing the window definition
removes manual friction without letting a new strategy inherit another
strategy's evidence.

## Verification

- `python -m pytest tests\test_research_autopilot.py::test_revision_retest_task_plan_reuses_existing_dataset_split_windows tests\test_research_autopilot.py::test_execute_revision_retest_next_task_locks_protocol_from_reusable_split -q`
- `python -m pytest tests\test_research_autopilot.py -q`
- `python -m pytest -q`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
- `python .\run_forecast_loop.py --help`
- `git diff --check`
