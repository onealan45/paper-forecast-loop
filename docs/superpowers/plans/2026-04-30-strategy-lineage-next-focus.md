# Strategy Lineage Next Focus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a human-readable next research focus to strategy lineage so the UX explains what the strategy research loop should inspect next after a lineage verdict.

**Architecture:** Derive `next_research_focus` from existing lineage verdict, latest recommended action, and primary failure attribution. Keep this deterministic and read-only: no strategy mutation, no promotion, no scheduler behavior, no broker/order path.

**Tech Stack:** Python dataclasses, static dashboard HTML, local operator console HTML, pytest.

---

### Task 1: Domain Next Focus

**Files:**
- Modify: `src/forecast_loop/strategy_lineage.py`
- Test: `tests/test_strategy_lineage.py`

- [ ] **Step 1: Write failing tests**

For a worsened/quarantined lineage with `drawdown_breach`, assert:

```python
summary.next_research_focus == "停止加碼此 lineage，優先研究 drawdown_breach 的修正或新策略。"
```

For an all-unknown lineage, assert:

```python
summary.next_research_focus == "先補齊 paper-shadow outcome 證據，再判斷修正方向。"
```

- [ ] **Step 2: Run domain tests**

```powershell
python -m pytest tests\test_strategy_lineage.py -q
```

Expected: fail because `next_research_focus` does not exist.

- [ ] **Step 3: Implement deterministic focus text**

Rules:

```python
if performance_verdict == "證據不足":
    "先補齊 paper-shadow outcome 證據，再判斷修正方向。"
elif latest_action == "QUARANTINE_STRATEGY":
    f"停止加碼此 lineage，優先研究 {failure or '主要失敗'} 的修正或新策略。"
elif latest_action == "REVISE_STRATEGY" or performance_verdict in {"惡化", "偏弱"}:
    f"優先修正 {failure or '主要失敗'}，再重跑 locked retest。"
elif performance_verdict in {"改善", "偏強"}:
    "保留此 lineage，下一步驗證改善是否能跨樣本持續。"
else:
    "維持觀察，等待更多 paper-shadow outcome。"
```

- [ ] **Step 4: Re-run domain tests**

Expected: pass.

### Task 2: UX Next Focus

**Files:**
- Modify: `src/forecast_loop/dashboard.py`
- Modify: `src/forecast_loop/operator_console.py`
- Test: `tests/test_dashboard.py`
- Test: `tests/test_operator_console.py`

- [ ] **Step 1: Add failing UX assertions**

Assert that dashboard and operator console strategy lineage surfaces include:

```python
"下一步研究焦點"
"停止加碼此 lineage，優先研究 drawdown_breach 的修正或新策略。"
```

- [ ] **Step 2: Run focused UX tests**

```powershell
python -m pytest tests\test_dashboard.py tests\test_operator_console.py -k "strategy_lineage" -q
```

Expected: fail because the UX does not render next research focus.

- [ ] **Step 3: Render next focus**

Dashboard should add a `下一步研究焦點` row after `表現結論`. Operator console should show the same line in both research and overview strategy sections.

- [ ] **Step 4: Re-run focused UX tests**

Expected: pass.

### Task 3: Docs, Review, Gates

**Files:**
- Modify: `README.md`
- Modify: `docs/PRD.md`
- Modify: `docs/architecture/alpha-factory-research-background.md`
- Create: `docs/architecture/PR39-strategy-lineage-next-focus.md`
- Create: `docs/reviews/2026-04-30-pr39-strategy-lineage-next-focus-review.md`

- [ ] **Step 1: Update docs**

Document that PR39 turns lineage verdict into a next research focus for the self-evolving strategy loop.

- [ ] **Step 2: Run gates**

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
git ls-files .codex paper_storage reports output .env
```

- [ ] **Step 3: Subagent review and archive**

Use reviewer subagent only. Archive PASS or findings under `docs/reviews/`.

- [ ] **Step 4: Commit and publish**

Commit:

```text
Add strategy lineage next research focus
```

PR:

```text
[PR39] Add strategy lineage next research focus
```
