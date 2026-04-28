# Strategy Card And Experiment Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the PR6 Alpha Factory registry foundation: versioned strategy cards, experiment trial budgets, and append-only experiment trials including failed, aborted, and invalid runs.

**Architecture:** Keep this stage artifact-first. Add focused dataclasses in `forecast_loop.models`, repository read/write methods in JSONL and SQLite, a small `experiment_registry.py` service for idempotent creation, CLI commands for manual/autonomous recording, and health checks for duplicate ids and broken links. Do not add leaderboard ranking, automatic strategy generation, or decision promotion in this PR.

**Tech Stack:** Python dataclasses, existing JSONL repository, existing SQLite generic artifact table, argparse CLI, pytest.

---

## Scope

PR6 implements:

- `strategy_cards.jsonl`: immutable/versioned strategy descriptions and hypotheses.
- `experiment_budgets.jsonl`: per-card trial budget snapshots.
- `experiment_trials.jsonl`: append-only trial records for `PASSED`, `FAILED`, `ABORTED`, and `INVALID` outcomes.
- CLI:
  - `register-strategy-card`
  - `record-experiment-trial`
- Health and SQLite parity for the new artifacts.

PR6 explicitly defers:

- locked split manifests and holdout gates;
- leaderboard ranking;
- paper-shadow outcome learning;
- automatic natural-language strategy generation;
- strategy-visible UX.

## Files

- Create `src/forecast_loop/experiment_registry.py`: service helpers for strategy card registration and experiment trial recording.
- Modify `src/forecast_loop/models.py`: add `StrategyCard`, `ExperimentBudget`, `ExperimentTrial`.
- Modify `src/forecast_loop/storage.py`: add repository protocol and JSONL persistence.
- Modify `src/forecast_loop/sqlite_repository.py`: add artifact specs, methods, migration/export parity.
- Modify `src/forecast_loop/health.py`: load artifacts, duplicate checks, and link checks.
- Modify `src/forecast_loop/cli.py`: add two CLI commands and handlers.
- Create `tests/test_experiment_registry.py`: TDD coverage for JSONL, CLI, budget enforcement, failed/aborted persistence, and health.
- Modify `tests/test_sqlite_repository.py`: parity for SQLite round trip/migration/export.
- Modify `README.md`: add artifact and command documentation.
- Create `docs/architecture/PR6-strategy-card-experiment-registry.md`: document current registry contract.
- Create `docs/reviews/2026-04-28-pr6-strategy-card-experiment-registry-review.md`: archive independent final reviewer result after review.

## TDD Tasks

### Task 1: Model And JSONL Registry

**Files:**
- Modify: `src/forecast_loop/models.py`
- Modify: `src/forecast_loop/storage.py`
- Create: `tests/test_experiment_registry.py`

- [ ] **Step 1: Write failing round-trip test**

Add a test that imports `StrategyCard`, `ExperimentBudget`, `ExperimentTrial`, and `JsonFileRepository`, saves one card plus a failed and aborted trial, and expects all to round-trip from JSONL.

- [ ] **Step 2: Verify RED**

Run:

```powershell
python -m pytest tests\test_experiment_registry.py::test_json_repository_round_trips_strategy_cards_and_experiment_trials -q
```

Expected failure: import error or missing repository methods.

- [ ] **Step 3: Implement minimal models and JSONL methods**

Add dataclasses with stable ids, `to_dict`, and `from_dict`. Add repository methods and paths for:

- `save_strategy_card` / `load_strategy_cards`
- `save_experiment_budget` / `load_experiment_budgets`
- `save_experiment_trial` / `load_experiment_trials`

- [ ] **Step 4: Verify GREEN**

Run the same targeted pytest command. Expected: pass.

### Task 2: Registry Service And Trial Budget Enforcement

**Files:**
- Create: `src/forecast_loop/experiment_registry.py`
- Modify: `tests/test_experiment_registry.py`

- [ ] **Step 1: Write failing service tests**

Add tests proving:

- registering the same strategy card twice is idempotent;
- a trial records budget metadata;
- a trial after `max_trials` is persisted as `ABORTED` with `trial_budget_exhausted`;
- `FAILED` and `INVALID` outcomes are persisted, not dropped.

- [ ] **Step 2: Verify RED**

Run:

```powershell
python -m pytest tests\test_experiment_registry.py -q
```

Expected failure: missing service functions.

- [ ] **Step 3: Implement service functions**

Implement:

- `register_strategy_card(repository, ..., created_at) -> StrategyCard`
- `record_experiment_trial(repository, ..., created_at, max_trials) -> ExperimentTrial`

Keep logic minimal and deterministic. Do not run backtests from this service.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
python -m pytest tests\test_experiment_registry.py -q
```

Expected: pass.

### Task 3: CLI Commands

**Files:**
- Modify: `src/forecast_loop/cli.py`
- Modify: `tests/test_experiment_registry.py`

- [ ] **Step 1: Write failing CLI tests**

Add tests for:

- `register-strategy-card` writes one card and prints JSON containing `card_id`;
- `record-experiment-trial --status FAILED` writes an experiment trial and keeps `failure_reason`;
- `record-experiment-trial` with exhausted budget prints an `ABORTED` trial.

- [ ] **Step 2: Verify RED**

Run:

```powershell
python -m pytest tests\test_experiment_registry.py -q
```

Expected failure: argparse unknown command.

- [ ] **Step 3: Implement argparse and handlers**

Add parser commands with explicit arguments. Use `KEY=VALUE` parsing for parameters and metrics. Return JSON with `strategy_card` or `experiment_trial`.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
python -m pytest tests\test_experiment_registry.py -q
python .\run_forecast_loop.py --help
```

Expected: tests pass and help includes new commands.

### Task 4: Health And SQLite Parity

**Files:**
- Modify: `src/forecast_loop/health.py`
- Modify: `src/forecast_loop/sqlite_repository.py`
- Modify: `tests/test_experiment_registry.py`
- Modify: `tests/test_sqlite_repository.py`

- [ ] **Step 1: Write failing integrity tests**

Add tests proving health flags:

- duplicate `card_id`;
- experiment trial referencing missing strategy card;
- experiment trial referencing missing dataset/backtest/walk-forward/event-edge artifact when the optional id is present.

Add SQLite parity checks in existing SQLite test helper.

- [ ] **Step 2: Verify RED**

Run:

```powershell
python -m pytest tests\test_experiment_registry.py tests\test_sqlite_repository.py -q
```

Expected failure: health and SQLite do not know the new artifacts.

- [ ] **Step 3: Implement health and SQLite support**

Add new artifact specs, repository methods, migration loops, export loops, duplicate checks, and link checks.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
python -m pytest tests\test_experiment_registry.py tests\test_sqlite_repository.py -q
```

Expected: pass.

### Task 5: Docs, Review, And Gates

**Files:**
- Modify: `README.md`
- Create: `docs/architecture/PR6-strategy-card-experiment-registry.md`
- Create: `docs/reviews/2026-04-28-pr6-strategy-card-experiment-registry-review.md`

- [ ] **Step 1: Update docs**

Document the new artifacts, CLI commands, and deferred boundaries.

- [ ] **Step 2: Run full local verification**

Run:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

- [ ] **Step 3: Independent review**

Dispatch a reviewer subagent using `roles/reviewer.md` expectations. Reviewer must check registry persistence, budget enforcement, health links, SQLite parity, docs, and no runtime/secrets committed.

- [ ] **Step 4: Archive review and re-run gates**

Archive reviewer result in `docs/reviews/2026-04-28-pr6-strategy-card-experiment-registry-review.md`, fix any blocking findings, then rerun the full local gate.

## Acceptance Criteria

- Strategy cards are persisted and idempotent by stable `card_id`.
- Experiment trials persist all statuses, including `FAILED`, `ABORTED`, and `INVALID`.
- Trial budget exhaustion cannot silently drop a trial; it writes an `ABORTED` artifact with a clear reason.
- Health check detects duplicate ids and broken links for the new artifacts.
- SQLite migration/export/db-health include the new artifact types.
- CLI smoke tests prove both new commands are operator-friendly.
- User-facing docs are Traditional Chinese.
- Full local gate passes.
- Independent reviewer subagent approves and review is archived.
