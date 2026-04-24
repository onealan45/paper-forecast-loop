# M1 Strategy Research Robot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a paper-only strategy decision layer that answers the next-horizon buy/sell/hold/risk question and creates Codex repair requests when the loop is unhealthy.

**Architecture:** Keep JSONL compatibility for this PR and add the new M1 artifacts behind repository methods. Add a decision engine fed by forecasts, scores, reviews, baselines, portfolio snapshots, and health checks; add CLI and dashboard surfaces without introducing live execution. Document SQLite as the next canonical-store migration rather than mixing it into this feature patch.

**Tech Stack:** Python 3.13, stdlib dataclasses/json/pathlib/datetime, existing JSONL repository, pytest.

---

## File Structure

- Create: `src/forecast_loop/baselines.py` for naive persistence baseline evaluation.
- Create: `src/forecast_loop/decision.py` for strategy decision generation.
- Create: `src/forecast_loop/health.py` for storage audit and repair request generation.
- Create: `src/forecast_loop/broker.py` for broker interface and paper-only adapter.
- Modify: `src/forecast_loop/models.py` to add M1 artifact dataclasses.
- Modify: `src/forecast_loop/storage.py` to save/load M1 JSONL artifacts.
- Modify: `src/forecast_loop/cli.py` to add `decide`, `health-check`, and `run-once --also-decide`.
- Modify: `src/forecast_loop/dashboard.py` to prioritize decision and health.
- Modify: `README.md` and `docs/PRD.md` for M1 product scope.
- Add tests under `tests/` for decisions, baselines, health, broker safety, CLI, and dashboard.

## Tasks

### Task 1: Document Architecture

- [x] Add `docs/architecture/M1-strategy-research-robot.md`.
- [x] Keep JSONL active in this PR and document SQLite as the next migration step.
- [x] State paper-only and live-trading blocked boundaries.

### Task 2: Add M1 Artifact Models And Repository Methods

- [x] Add `BaselineEvaluation`, `StrategyDecision`, `PaperPosition`, `PaperPortfolioSnapshot`, `HealthFinding`, `HealthCheckResult`, and `RepairRequest` dataclasses.
- [x] Add deterministic identity helpers for baselines, decisions, snapshots, and repair requests.
- [x] Add JSON serialization/deserialization for each model.
- [x] Add repository save/load methods and JSONL paths for all new artifact families.
- [x] Add tests proving round-trip persistence and duplicate idempotency.

### Task 3: Add Baseline Evaluation

- [x] Implement naive persistence baseline using previous actual regime as the next expected regime.
- [x] Compute sample size, directional accuracy, baseline accuracy, model edge, recent score, and evidence grade.
- [x] Persist a `BaselineEvaluation`.
- [x] Add tests for insufficient samples, no baseline edge, and positive baseline edge.

### Task 4: Add Paper-Only Broker Boundary

- [x] Add `BrokerAdapter` protocol and `PaperBrokerAdapter`.
- [x] Provide account snapshot and blocked paper order submission semantics.
- [x] Add tests proving no live broker adapter is available and live mode fails closed.

### Task 5: Add Health And Repair Requests

- [x] Implement `health-check` for missing storage, bad JSON rows, duplicate forecast ids, score/review/proposal/decision broken links, latest forecast staleness, last-run meta mismatch, and dashboard freshness.
- [x] Generate `repair_requests.jsonl` and `.codex/repair_requests/pending/<repair_request_id>.md` for blocking findings.
- [x] Add tests for missing storage, bad JSON, duplicate ids, missing forecast links, meta mismatch, and repair prompt output.

### Task 6: Add Strategy Decision Engine

- [x] Generate `STOP_NEW_ENTRIES` when health is blocking, latest forecast is missing, or latest forecast is stale.
- [x] Generate `HOLD` when evidence is insufficient.
- [x] Block BUY/SELL when model does not beat baseline.
- [x] Generate `REDUCE_RISK` when recent score is poor.
- [x] Generate paper-only BUY/SELL only when evidence grade is A/B and model edge is positive.
- [x] Link forecast, score, review, and baseline ids into the decision.
- [x] Add tests for all decision gates.

### Task 7: Add CLI Surface

- [x] Add `python run_forecast_loop.py decide --storage-dir <path> --symbol BTC-USD --horizon-hours 24`.
- [x] Add `python run_forecast_loop.py health-check --storage-dir <path>`.
- [x] Add optional `run-once --also-decide`.
- [x] Preserve argparse-style errors for malformed datetimes and operator input mistakes.
- [x] Add CLI tests.

### Task 8: Update Dashboard

- [x] Add latest strategy decision and health status to `DashboardSnapshot`.
- [x] Render tomorrow's decision first, then risk posture, prediction quality, latest forecast, and repair status.
- [x] Add Traditional Chinese labels for actions, evidence grades, repair required, provider failure, and storage degraded.
- [x] Keep raw metadata collapsed and the dashboard read-only.
- [x] Add dashboard tests.

### Task 9: Docs, Verification, Review, And Automation

- [x] Update README and PRD to describe M1 as a strategy research robot.
- [x] Run `python -m pytest -q`.
- [x] Run `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`.
- [x] Run `decide`, `health-check`, and `render-dashboard` against active paper storage.
- [x] Use a subagent for final review; do not self-review.
- [x] Archive review under `docs/reviews/`.
- [x] Resume `hourly-paper-forecast` only if final review approves and active artifacts are healthy.
