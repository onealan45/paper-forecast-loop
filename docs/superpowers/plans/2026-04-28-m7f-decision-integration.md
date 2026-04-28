# M7F Decision Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate M7 event-derived evidence into the existing strategy decision research gate without bypassing baseline, backtest, walk-forward, risk, or health gates.

**Architecture:** Extend `evaluate_research_gates` to accept the latest `EventEdgeEvaluation` for the decision symbol. `generate_strategy_decision` will load that latest edge evaluation and pass it into the research gate. The decision schema stays unchanged; event evidence is surfaced in `decision_basis`.

**Tech Stack:** Existing Python decision engine, existing `EventEdgeEvaluation` model, pytest.

---

### Task 1: Failing Tests

**Files:**
- Modify: `tests/test_research_gates.py`

Add tests:

```python
def test_research_gate_blocks_buy_when_event_edge_missing(tmp_path):
    # Strong baseline/backtest/walk-forward/risk is not enough after M7F.
    # Missing event edge must block BUY with blocked_reason == "research_event_edge_missing".
```

```python
def test_research_gate_blocks_buy_when_event_edge_fails(tmp_path):
    # A failed latest EventEdgeEvaluation blocks BUY and appears in decision_basis.
```

Update the existing allow-BUY test to seed a passed event edge evaluation.

### Task 2: Research Gate Integration

**Files:**
- Modify: `src/forecast_loop/research_gates.py`
- Modify: `src/forecast_loop/decision.py`

Rules:
- `evaluate_research_gates` accepts `latest_event_edge: EventEdgeEvaluation | None`.
- Missing edge adds `research_event_edge_missing`.
- Failed edge adds `research_event_edge_not_passed`.
- Non-positive average after-cost edge adds `research_event_edge_not_positive`.
- Decision basis records event edge id, sample size, after-cost edge, pass state, and flags.
- Existing backtest / walk-forward / baseline / risk gates remain in force.

### Task 3: Docs, Review, Verification

**Files:**
- Modify: `README.md`
- Create: `docs/architecture/M7F-decision-integration.md`
- Create: `docs/reviews/2026-04-28-m7f-decision-integration-review.md` after reviewer approval

Verify:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```
