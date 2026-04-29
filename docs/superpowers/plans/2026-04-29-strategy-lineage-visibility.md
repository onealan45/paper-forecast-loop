# Strategy Lineage Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show strategy lineage, revision count, paper-shadow action counts, and failure-attribution concentration in read-only strategy UX surfaces.

**Architecture:** Add a pure summary helper that derives lineage from existing `StrategyCard` and `PaperShadowOutcome` artifacts. Dashboard and operator console snapshots carry the summary and render it near the existing strategy research panels. No executor, promotion, broker, scheduler, or trading path changes.

**Tech Stack:** Python dataclasses, JSONL repository loaders, pytest, static HTML renderers.

---

### Task 1: Add Failing Lineage Summary Tests

**Files:**
- Create: `tests/test_strategy_lineage.py`

- [ ] **Step 1: Write summary tests**

```python
from datetime import UTC, datetime, timedelta

from forecast_loop.models import PaperShadowOutcome, StrategyCard
from forecast_loop.strategy_lineage import build_strategy_lineage_summary


def _card(card_id: str, *, parent_card_id: str | None = None, status: str = "ACTIVE") -> StrategyCard:
    return StrategyCard(
        card_id=card_id,
        created_at=datetime(2026, 4, 29, 9, 0, tzinfo=UTC),
        strategy_name=card_id,
        strategy_family="breakout_reversal",
        version="v1",
        status=status,
        symbols=["BTC-USD"],
        hypothesis="test",
        signal_description="test",
        entry_rules=[],
        exit_rules=[],
        risk_rules=[],
        parameters={},
        data_requirements=[],
        feature_snapshot_ids=[],
        backtest_result_ids=[],
        walk_forward_validation_ids=[],
        event_edge_evaluation_ids=[],
        parent_card_id=parent_card_id,
        author="test",
        decision_basis="test",
    )


def _outcome(outcome_id: str, *, card_id: str, created_at: datetime, action: str, excess: float | None, attributions: list[str]) -> PaperShadowOutcome:
    return PaperShadowOutcome(
        outcome_id=outcome_id,
        created_at=created_at,
        leaderboard_entry_id=f"leaderboard-entry:{outcome_id}",
        evaluation_id=f"locked-evaluation:{outcome_id}",
        strategy_card_id=card_id,
        trial_id=f"experiment-trial:{outcome_id}",
        symbol="BTC-USD",
        window_start=created_at - timedelta(hours=24),
        window_end=created_at,
        observed_return=None,
        benchmark_return=None,
        excess_return_after_costs=excess,
        max_adverse_excursion=None,
        turnover=None,
        outcome_grade="FAIL",
        failure_attributions=attributions,
        recommended_promotion_stage="PAPER_SHADOW_FAILED",
        recommended_strategy_action=action,
        blocked_reasons=[],
        notes=[],
        decision_basis="test",
    )


def test_strategy_lineage_summary_counts_revisions_actions_and_failures():
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    parent = _card("strategy-card:parent")
    revision = _card("strategy-card:revision", parent_card_id=parent.card_id, status="DRAFT")
    sibling = _card("strategy-card:sibling", parent_card_id="strategy-card:other", status="DRAFT")
    summary = build_strategy_lineage_summary(
        root_card=parent,
        strategy_cards=[parent, revision, sibling],
        paper_shadow_outcomes=[
            _outcome("parent-fail", card_id=parent.card_id, created_at=now, action="REVISE_STRATEGY", excess=-0.03, attributions=["negative_excess_return"]),
            _outcome("revision-fail", card_id=revision.card_id, created_at=now + timedelta(hours=1), action="QUARANTINE_STRATEGY", excess=-0.08, attributions=["negative_excess_return", "drawdown_breach"]),
        ],
    )

    assert summary.root_card_id == parent.card_id
    assert summary.revision_count == 1
    assert summary.outcome_count == 2
    assert summary.action_counts == {"QUARANTINE_STRATEGY": 1, "REVISE_STRATEGY": 1}
    assert summary.failure_attribution_counts["negative_excess_return"] == 2
    assert summary.best_excess_return_after_costs == -0.03
    assert summary.worst_excess_return_after_costs == -0.08
    assert summary.latest_outcome_id == "revision-fail"
```

- [ ] **Step 2: Run red test**

Run: `python -m pytest tests\test_strategy_lineage.py -q`

Expected: fail with missing `forecast_loop.strategy_lineage`.

### Task 2: Implement Summary Helper

**Files:**
- Create: `src/forecast_loop/strategy_lineage.py`

- [ ] **Step 1: Add dataclass and builder**

Implement `StrategyLineageSummary` and `build_strategy_lineage_summary(root_card, strategy_cards, paper_shadow_outcomes)`.

- [ ] **Step 2: Run summary tests**

Run: `python -m pytest tests\test_strategy_lineage.py -q`

Expected: pass.

### Task 3: Add Dashboard And Operator Console Failing Tests

**Files:**
- Modify: `tests/test_dashboard.py`
- Modify: `tests/test_operator_console.py`

- [ ] **Step 1: Extend existing strategy research fixtures**

Add child revision and extra paper-shadow outcomes to existing strategy research fixture tests.

- [ ] **Step 2: Assert UX strings**

Assert both surfaces include:

- `策略 lineage`
- `REVISE_STRATEGY`
- `QUARANTINE_STRATEGY`
- `negative_excess_return`
- best/worst excess-return values

- [ ] **Step 3: Run red tests**

Run: `python -m pytest tests\test_dashboard.py tests\test_operator_console.py -k "strategy_lineage" -q`

Expected: fail because renderers do not yet show lineage.

### Task 4: Wire Snapshot And Renderers

**Files:**
- Modify: `src/forecast_loop/dashboard.py`
- Modify: `src/forecast_loop/operator_console.py`

- [ ] **Step 1: Add snapshot field**

Add `latest_strategy_lineage_summary: StrategyLineageSummary | None` to both snapshot dataclasses.

- [ ] **Step 2: Build summary**

Call `build_strategy_lineage_summary` from the latest parent strategy card and available strategy cards / paper-shadow outcomes.

- [ ] **Step 3: Render summary**

Render a compact read-only panel in dashboard and operator console showing revision count, action counts, attribution counts, best/worst return, and latest outcome id.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests\test_strategy_lineage.py tests\test_dashboard.py tests\test_operator_console.py -k "strategy_lineage" -q`

Expected: pass.

### Task 5: Docs, Review, Gates, PR

**Files:**
- Create: `docs/architecture/PR31-strategy-lineage-visibility.md`
- Create: `docs/reviews/2026-04-29-pr31-strategy-lineage-visibility-review.md`
- Modify: `README.md`
- Modify: `docs/PRD.md`
- Modify: `docs/architecture/alpha-factory-research-background.md`

- [ ] **Step 1: Document the feature**

Record that PR31 adds read-only strategy lifecycle and demotion/quarantine visibility from existing artifacts.

- [ ] **Step 2: Run full gates**

Run:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

- [ ] **Step 3: Final reviewer**

Use one reviewer subagent. Reviewer must not edit files. Archive verdict under `docs/reviews/`.

- [ ] **Step 4: Commit, push, PR, CI, merge**

Only merge if local gates, subagent review, GitHub CI, and merge state pass.
