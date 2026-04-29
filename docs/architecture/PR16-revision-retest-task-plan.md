# PR16 Revision Retest Task Plan

## Purpose

PR16 adds a read-only planning layer for self-evolving strategy revisions. PR14
can create a pending retest scaffold, and PR15 makes that scaffold visible.
PR16 answers the next operational research question: what exact artifact is
missing next, and which command can be run when the prerequisite evidence
exists?

## Behavior

`revision-retest-plan` reads existing artifacts and emits a deterministic JSON
task plan. It does not write artifacts, run simulations, or fabricate
evaluation results.

The task order is fixed:

1. `create_revision_retest_scaffold`
2. `lock_evaluation_protocol`
3. `generate_baseline_evaluation`
4. `run_backtest`
5. `run_walk_forward`
6. `record_passed_retest_trial`
7. `evaluate_leaderboard_gate`
8. `record_paper_shadow_outcome`

Each task is marked:

- `completed` when the required artifact already exists.
- `ready` when the command arguments can be emitted from known artifacts.
- `blocked` when the planner would need to invent windows, returns, or missing
  artifact IDs.

## CLI

```powershell
python run_forecast_loop.py revision-retest-plan --storage-dir .\paper_storage\manual-research --revision-card-id strategy-card:example-revision --symbol BTC-USD
```

The output includes `next_task_id`, linked artifact IDs, missing inputs, and
command arguments for runnable steps. Commands are emitted as argument arrays so
the operator or a future research worker can inspect them before execution.

## Boundaries

- Read-only: no JSONL rows are written by the planner.
- No retest execution: `backtest`, `walk-forward`, and leaderboard gates remain
  separate commands.
- No fake completion: missing split windows and paper-shadow returns remain
  blocked instead of being guessed.
- Research-first: the purpose is to accelerate strategy learning and make the
  self-evolution loop concrete, not to add execution controls.

## Tests

PR16 adds regression tests proving:

- the planner does not mutate JSONL files;
- missing split windows block `lock_evaluation_protocol`;
- locked splits produce concrete `backtest` and `walk-forward` command
  arguments;
- the CLI prints deterministic JSON.
