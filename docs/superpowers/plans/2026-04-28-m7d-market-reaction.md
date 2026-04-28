# M7D Market Reaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the M7D already-priced / market reaction gate for canonical event snapshots.

**Architecture:** Add a focused `market_reaction.py` module that reads M7C canonical event snapshots, matching reliability checks, and stored hourly market candles. It emits `MarketReactionCheck` artifacts that block unreliable or already-priced events before M7E/M7F can use them.

**Tech Stack:** Python dataclasses, existing JSONL repository, existing `MarketReactionCheck` model, deterministic stored candles, pytest, `run_forecast_loop.py` CLI.

---

### Task 1: Failing Tests For Market Reaction

**Files:**
- Create: `tests/test_market_reaction.py`

- [ ] **Step 1: Write failing tests**

Cover:

```python
def test_build_market_reactions_passes_when_pre_event_drift_is_small(tmp_path):
    # Reliable event + stable pre-event prices creates one passed MarketReactionCheck.
```

```python
def test_build_market_reactions_blocks_already_priced_event(tmp_path):
    # Large pre-event 4h drift sets already_priced=True, passed=False, blocked_reason="already_priced".
```

```python
def test_build_market_reactions_blocks_unreliable_event_before_price_gate(tmp_path):
    # Event without a passed EventReliabilityCheck creates a blocked market reaction check.
```

```python
def test_build_market_reactions_cli_is_idempotent_and_requires_created_at(tmp_path, capsys):
    # CLI requires --created-at and fixed command reruns do not duplicate checks.
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
python -m pytest tests\test_market_reaction.py -q
```

Expected: fail because `forecast_loop.market_reaction` and CLI `build-market-reactions` do not exist.

### Task 2: Market Reaction Engine

**Files:**
- Create: `src/forecast_loop/market_reaction.py`

- [ ] **Step 1: Implement `build_market_reactions`**

Implement:

```python
def build_market_reactions(
    *,
    storage_dir: Path | str,
    created_at: datetime,
    symbol: str | None = None,
    already_priced_return_threshold: float = 0.03,
    volume_shock_z_threshold: float = 3.0,
) -> MarketReactionBuildResult:
```

Rules:
- Reject naive `created_at`.
- Only use canonical events whose `available_at <= created_at` and whose event snapshot `created_at <= created_at`.
- Only use candles whose `timestamp <= created_at`.
- Use event `available_at` as `event_timestamp_used`.
- Use passed reliability checks as a prerequisite.
- Compute pre-event 1h/4h/24h returns where enough candle coverage exists.
- Compute post-event 1h return only when point-in-time data exists.
- Block when reliability did not pass.
- Block when pre-event 4h absolute return exceeds threshold.
- Block when volume shock z-score exceeds threshold.
- Replace same `check_id` rows for idempotent fixed reruns.

### Task 3: CLI And Docs

**Files:**
- Modify: `src/forecast_loop/cli.py`
- Modify: `README.md`
- Create: `docs/architecture/M7D-market-reaction.md`
- Create: `docs/reviews/2026-04-28-m7d-market-reaction-review.md` after reviewer approval

- [ ] **Step 1: Add CLI**

Add:

```powershell
python .\run_forecast_loop.py build-market-reactions --storage-dir .\paper_storage\m7-fixture --symbol BTC-USD --created-at 2026-04-28T10:05:00+00:00
```

`--created-at` must be required.

- [ ] **Step 2: Update docs**

Document:
- M7D implemented scope.
- M7D deferred scope: historical edge and decision integration.
- Point-in-time candle rule.
- Already-priced blocking semantics.

- [ ] **Step 3: Verify**

Run:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Also run an M7D smoke using temporary storage with stored candles, source import,
event build, and market reaction build.
