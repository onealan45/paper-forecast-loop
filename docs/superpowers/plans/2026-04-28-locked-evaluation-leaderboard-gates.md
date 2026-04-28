# Locked Evaluation And Leaderboard Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PR7 locked evaluation artifacts and leaderboard hard gates so strategy cards cannot become rankable until fixed split, cost, baseline, backtest, walk-forward, trial-budget, and optional event-edge gates pass.

**Architecture:** Build a registry/gate foundation, not a full statistical lab. Add four artifacts: `split_manifests`, `cost_model_snapshots`, `locked_evaluation_results`, and `leaderboard_entries`. A small `locked_evaluation.py` service creates immutable split/cost snapshots and evaluates an existing experiment trial into a rankable/non-rankable leaderboard entry. Keep all evaluation deterministic and artifact-linked; do not train models or relax decision gates.

**Tech Stack:** Python dataclasses, JSONL repository, SQLite generic artifact store, argparse CLI, pytest.

---

## Scope

PR7 implements:

- `split_manifests.jsonl`: fixed train/validation/holdout window manifests with embargo.
- `cost_model_snapshots.jsonl`: fee/slippage/turnover cost assumptions.
- `locked_evaluation_results.jsonl`: hard-gate outcome for one strategy trial.
- `leaderboard_entries.jsonl`: rankable only when hard gates pass; blocked entries keep reasons and no `alpha_score`.
- CLI:
  - `lock-evaluation-protocol`
  - `evaluate-leaderboard-gate`
- JSONL and SQLite parity.
- Health-check duplicate and link integrity.

PR7 defers:

- CPCV/PBO/DSR/bootstrap implementations beyond placeholder fields.
- Paper-shadow outcome learning.
- Strategy-visible UI.
- Automatic strategy generation.
- Real execution or live broker work.

## Files

- Create `src/forecast_loop/locked_evaluation.py`: service helpers.
- Modify `src/forecast_loop/models.py`: add `SplitManifest`, `CostModelSnapshot`, `LockedEvaluationResult`, `LeaderboardEntry`.
- Modify `src/forecast_loop/storage.py`: repository protocol and JSONL methods.
- Modify `src/forecast_loop/sqlite_repository.py`: artifact specs, methods, migration/export.
- Modify `src/forecast_loop/health.py`: load artifacts, duplicate/link checks.
- Modify `src/forecast_loop/cli.py`: CLI commands.
- Create `tests/test_locked_evaluation.py`: TDD behavior tests.
- Modify `tests/test_sqlite_repository.py`: SQLite parity.
- Modify `README.md`, `docs/PRD.md`, and `docs/architecture/alpha-factory-research-background.md`.
- Create `docs/architecture/PR7-locked-evaluation-leaderboard-gates.md`.
- Create `docs/reviews/2026-04-28-pr7-locked-evaluation-leaderboard-gates-review.md` after independent review.

## TDD Tasks

### Task 1: Models And JSONL

- [ ] Add failing round-trip test for split manifest, cost model, locked evaluation result, and leaderboard entry.
- [ ] Run targeted test and confirm it fails due to missing models/methods.
- [ ] Add dataclasses and JSONL repository methods.
- [ ] Re-run targeted test and confirm pass.

### Task 2: Locked Evaluation Service

- [ ] Add failing tests proving an experiment trial cannot become rankable without a locked split and cost model.
- [ ] Add failing tests proving weak/failed gates produce `rankable=False` and `alpha_score=None`.
- [ ] Add failing tests proving passed gates produce a leaderboard entry with a deterministic `alpha_score`.
- [ ] Implement `lock_evaluation_protocol()` and `evaluate_leaderboard_gate()`.
- [ ] Re-run targeted tests.

### Task 3: CLI

- [ ] Add failing CLI tests for `lock-evaluation-protocol` and `evaluate-leaderboard-gate`.
- [ ] Implement argparse commands and handlers.
- [ ] Ensure malformed values return argparse-style errors, not raw traceback.
- [ ] Re-run targeted tests and `python .\run_forecast_loop.py --help`.

### Task 4: Health And SQLite

- [ ] Add failing tests for duplicate ids and broken links.
- [ ] Add SQLite parity tests for migration/export/db-health.
- [ ] Implement health and SQLite support.
- [ ] Re-run `tests/test_locked_evaluation.py tests/test_sqlite_repository.py`.

### Task 5: Docs, Review, Gates

- [ ] Update docs in Traditional Chinese for user-facing text.
- [ ] Run full local gate:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

- [ ] Dispatch independent reviewer subagent.
- [ ] Fix blockers with tests.
- [ ] Archive review.
- [ ] Re-run full local gate.

## Acceptance Criteria

- A strategy trial cannot receive `alpha_score` unless hard gates pass.
- Failed/aborted/invalid trials are visible as non-rankable leaderboard entries, not hidden.
- Leaderboard entries link to strategy card, trial, split manifest, cost model, and locked evaluation result.
- Health-check catches duplicate ids and broken links.
- SQLite migration/export/db-health include all new artifacts.
- CLI smoke tests pass.
- Independent reviewer approves.
