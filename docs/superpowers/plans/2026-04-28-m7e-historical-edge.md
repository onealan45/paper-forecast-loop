# M7E Historical Edge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the M7E historical edge evaluator for event families.

**Architecture:** Add `event_edge.py` to read canonical event snapshots, passed market reaction checks, and stored candles. It writes `EventEdgeEvaluation` artifacts that summarize forward return, benchmark return, after-cost excess return, hit rate, adverse excursion, and pass/block flags for each event family/type/symbol/horizon.

**Tech Stack:** Python dataclasses, existing JSONL repository, existing `EventEdgeEvaluation` model, pytest, `run_forecast_loop.py` CLI.

---

### Task 1: Failing Tests

**Files:**
- Create: `tests/test_event_edge.py`

Cover:

```python
def test_build_event_edge_passes_when_after_cost_edge_is_positive(tmp_path):
    # Three passed market reaction events with positive forward returns create one passed edge evaluation.
```

```python
def test_build_event_edge_blocks_when_sample_size_is_too_low(tmp_path):
    # Less than min_sample_size creates blocked evaluation with insufficient_sample_size.
```

```python
def test_build_event_edge_ignores_failed_market_reaction_checks(tmp_path):
    # Failed market reaction checks do not enter sample_n.
```

```python
def test_build_event_edge_cli_is_idempotent_and_requires_created_at(tmp_path, capsys):
    # CLI requires --created-at and fixed reruns do not duplicate evaluations.
```

Expected RED:

```powershell
python -m pytest tests\test_event_edge.py -q
```

fails because `forecast_loop.event_edge` and CLI `build-event-edge` do not exist.

### Task 2: Engine

**Files:**
- Create: `src/forecast_loop/event_edge.py`

Implement:

```python
def build_event_edge_evaluations(
    *,
    storage_dir: Path | str,
    created_at: datetime,
    symbol: str | None = None,
    horizon_hours: int = 24,
    min_sample_size: int = 3,
    estimated_cost_bps: float = 10.0,
) -> EventEdgeBuildResult:
```

Rules:
- Reject naive `created_at`.
- Only include events/checks/candles available by `created_at`.
- Only include `MarketReactionCheck.passed=True`.
- Use event timestamp from `MarketReactionCheck.event_timestamp_used`.
- Require exact candle at event timestamp and event timestamp + horizon.
- Compute forward return, benchmark return placeholder `0.0`, excess return after cost.
- Group by `(event_family, event_type, symbol, horizon_hours)`.
- Pass only if `sample_n >= min_sample_size`, average excess return after costs > 0, and hit rate >= 0.5.
- Idempotent replacement for fixed evaluation id.

### Task 3: CLI And Docs

**Files:**
- Modify: `src/forecast_loop/cli.py`
- Modify: `README.md`
- Create: `docs/architecture/M7E-historical-edge.md`
- Create: `docs/reviews/2026-04-28-m7e-historical-edge-review.md` after reviewer approval

Add CLI:

```powershell
python .\run_forecast_loop.py build-event-edge --storage-dir .\paper_storage\m7-fixture --symbol BTC-USD --created-at 2026-04-28T12:00:00+00:00 --horizon-hours 24
```

`--created-at` must be required.

Verify:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```
