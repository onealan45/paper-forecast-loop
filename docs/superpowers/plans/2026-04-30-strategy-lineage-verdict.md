# Strategy Lineage Verdict Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a concise, human-readable verdict to strategy lineage so the UX explains whether revisions are improving, worsening, stalled, or missing evidence.

**Architecture:** Extend `StrategyLineageSummary` with derived verdict fields computed from existing `outcome_nodes`. Keep this read-only and deterministic: no strategy mutation, no promotion, no trading, no runtime artifact writes. Render the verdict in dashboard and operator console above the raw trajectory rows.

**Tech Stack:** Python dataclasses, existing JSONL-backed domain models, static dashboard HTML, local operator console HTML, pytest.

---

### Task 1: Domain Verdict

**Files:**
- Modify: `src/forecast_loop/strategy_lineage.py`
- Test: `tests/test_strategy_lineage.py`

- [ ] **Step 1: Write the failing test**

Add assertions that a lineage with one baseline outcome, one improved revision, and one worsened revision exposes:

```python
summary.performance_verdict == "惡化"
summary.improved_outcome_count == 1
summary.worsened_outcome_count == 1
summary.unknown_outcome_count == 0
summary.latest_change_label == "惡化"
summary.latest_delta_vs_previous_excess == -0.04
summary.primary_failure_attribution == "drawdown_breach"
summary.latest_recommended_strategy_action == "QUARANTINE_STRATEGY"
```

Add a missing-evidence case that exposes:

```python
summary.performance_verdict == "證據不足"
summary.unknown_outcome_count == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests\test_strategy_lineage.py -q
```

Expected: fail because `StrategyLineageSummary` does not expose verdict fields.

- [ ] **Step 3: Implement minimal verdict fields**

Add fields to `StrategyLineageSummary`:

```python
performance_verdict: str
improved_outcome_count: int
worsened_outcome_count: int
unknown_outcome_count: int
latest_change_label: str
latest_delta_vs_previous_excess: float | None
primary_failure_attribution: str | None
latest_recommended_strategy_action: str | None
```

Compute them from `outcome_nodes` and attribution counts:

```python
improved = sum(1 for node in outcome_nodes if node.change_label == "改善")
worsened = sum(1 for node in outcome_nodes if node.change_label == "惡化")
unknown = sum(1 for node in outcome_nodes if node.change_label == "未知")
latest = outcome_nodes[-1] if outcome_nodes else None
```

Verdict rule:

```python
if not outcome_nodes or unknown == len(outcome_nodes):
    "證據不足"
elif latest and latest.change_label == "改善":
    "改善"
elif latest and latest.change_label == "惡化":
    "惡化"
elif latest and latest.change_label == "持平":
    "持平"
elif worsened > improved:
    "偏弱"
elif improved > worsened:
    "偏強"
else:
    "觀察中"
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest tests\test_strategy_lineage.py -q
```

Expected: pass.

### Task 2: UX Verdict

**Files:**
- Modify: `src/forecast_loop/dashboard.py`
- Modify: `src/forecast_loop/operator_console.py`
- Test: `tests/test_dashboard.py`
- Test: `tests/test_operator_console.py`

- [ ] **Step 1: Write failing UX assertions**

Add assertions to existing strategy lineage tests:

```python
assert "表現結論" in html
assert "惡化" in html
assert "改善 0 / 惡化 2 / 未知 0" in html
assert "主要失敗 drawdown_breach" in html
assert "最新動作 QUARANTINE_STRATEGY" in html
```

- [ ] **Step 2: Run UX tests to verify they fail**

Run:

```powershell
python -m pytest tests\test_dashboard.py tests\test_operator_console.py -k "strategy_lineage" -q
```

Expected: fail because the UX does not render the verdict block.

- [ ] **Step 3: Render the verdict**

Dashboard should add a `表現結論` row before `表現軌跡`. Operator console should add the same conclusion above the trajectory list. Escape all strings through existing helpers.

- [ ] **Step 4: Run UX tests**

Run:

```powershell
python -m pytest tests\test_dashboard.py tests\test_operator_console.py -k "strategy_lineage" -q
```

Expected: pass.

### Task 3: Docs, Review, Gates

**Files:**
- Modify: `README.md`
- Modify: `docs/PRD.md`
- Modify: `docs/architecture/alpha-factory-research-background.md`
- Create: `docs/architecture/PR38-strategy-lineage-verdict.md`
- Create: `docs/reviews/2026-04-30-pr38-strategy-lineage-verdict-review.md`

- [ ] **Step 1: Update docs**

Document that PR38 adds a readable lineage performance verdict from existing paper-shadow outcomes.

- [ ] **Step 2: Run final local gates**

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
git ls-files .codex paper_storage reports output .env
```

Expected: tests pass, compileall passes, CLI help exits 0, diff check exits 0, forbidden tracked paths output is empty.

- [ ] **Step 3: Subagent review**

Use a reviewer subagent only. Controller must not self-review. Archive PASS or findings under `docs/reviews/`.

- [ ] **Step 4: Commit, push, PR, merge if gates pass**

Branch: `codex/strategy-lineage-verdict`

Commit message:

```text
Add strategy lineage performance verdict
```

PR title:

```text
[PR38] Add strategy lineage performance verdict
```
