# Strategy Lineage Agenda UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make lineage-derived research agendas explicitly visible in dashboard and operator console strategy surfaces.

**Architecture:** Reuse existing `latest_research_agenda` from the strategy research resolver. Add small render helpers that only display a special lineage agenda block when `agenda.decision_basis == "strategy_lineage_research_agenda"`.

**Tech Stack:** Python server/static HTML rendering, existing `ResearchAgenda` model, pytest.

---

### Task 1: RED UX Tests

**Files:**
- Modify: `tests/test_dashboard.py`
- Modify: `tests/test_operator_console.py`

- [x] **Step 1: Add dashboard test**

Seed visible strategy lineage, create a `strategy_lineage_research_agenda`, render dashboard strategy panel, and assert:

```python
assert "Lineage 研究 agenda" in html
assert "strategy_lineage_research_agenda" in html
assert "停止加碼此 lineage" in html
```

- [x] **Step 2: Add operator console test**

Seed the same data, render operator console research page, and assert the same strings.

- [x] **Step 3: Run RED tests**

```powershell
python -m pytest tests\test_dashboard.py tests\test_operator_console.py -k "lineage_research_agenda_visibility" -q
```

Expected: fail because no dedicated lineage agenda block is rendered yet.

### Task 2: Minimal Rendering

**Files:**
- Modify: `src/forecast_loop/dashboard.py`
- Modify: `src/forecast_loop/operator_console.py`

- [x] **Step 1: Add dashboard helper**

Add:

```python
def _render_lineage_research_agenda(agenda: ResearchAgenda | None) -> str:
    if agenda is None or agenda.decision_basis != "strategy_lineage_research_agenda":
        return ""
    return f"""
      <div class="evidence-block">
        <h3>Lineage 研究 agenda</h3>
        <dl>
          <dt>Agenda</dt><dd>{_dashboard_artifact_id(agenda, "agenda_id")}</dd>
          <dt>Priority</dt><dd>{escape(agenda.priority)}</dd>
          <dt>Basis</dt><dd>{escape(agenda.decision_basis)}</dd>
          <dt>Hypothesis</dt><dd>{escape(agenda.hypothesis)}</dd>
          <dt>Acceptance</dt><dd>{_dashboard_list_inline(agenda.acceptance_criteria)}</dd>
        </dl>
      </div>
    """
```

Insert this helper immediately after the strategy lineage block in
`render_strategy_research_panel`.

- [x] **Step 2: Add operator console helper**

Add:

```python
def _lineage_research_agenda_panel(agenda: ResearchAgenda | None) -> str:
    if agenda is None or agenda.decision_basis != "strategy_lineage_research_agenda":
        return ""
    return f"""
  <article class="panel wide">
    <h3>Lineage 研究 agenda</h3>
    <p>ID：{_artifact_id(agenda, "agenda_id")}</p>
    <p>Priority：{escape(agenda.priority)}</p>
    <p>Basis：{escape(agenda.decision_basis)}</p>
    <p>Hypothesis：{escape(agenda.hypothesis)}</p>
    <h4>Acceptance</h4>
    {_plain_list(agenda.acceptance_criteria)}
  </article>
"""
```

Insert this helper after `_strategy_lineage_panel(lineage)` in `_render_research`.

- [x] **Step 3: Run GREEN tests**

```powershell
python -m pytest tests\test_dashboard.py tests\test_operator_console.py -k "lineage_research_agenda_visibility" -q
```

Expected: pass.

### Task 3: Docs, Review, Gates

**Files:**
- Modify: `README.md`
- Modify: `docs/PRD.md`
- Modify: `docs/architecture/alpha-factory-research-background.md`
- Create: `docs/architecture/PR42-strategy-lineage-agenda-ux.md`
- Create: `docs/reviews/2026-04-30-pr42-strategy-lineage-agenda-ux-review.md`
- Modify: `docs/superpowers/plans/2026-04-30-strategy-lineage-agenda-ux.md`

- [x] **Step 1: Update docs**

Document that lineage-derived agendas are now first-class visible strategy research context in dashboard/operator console.

- [x] **Step 2: Run full gates**

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
git ls-files .codex paper_storage reports output .env
```

- [x] **Step 3: Reviewer subagent**

Use reviewer subagent only. Required result: PASS with no blocking finding.

- [ ] **Step 4: Archive review and publish**

Commit:

```text
Show lineage research agendas in strategy UX
```

PR title:

```text
[PR42] Show lineage research agendas in strategy UX
```
