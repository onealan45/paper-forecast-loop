# Strategy Revision Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make PR12 DRAFT strategy revision candidates visible in the static dashboard and local operator console.

**Architecture:** Keep the existing latest strategy research chain, but add a separate latest revision-candidate view so a newly created DRAFT child strategy card is not hidden by the latest autopilot run. Reuse existing `StrategyCard`, `ResearchAgenda`, and `PaperShadowOutcome` artifacts; no schema migration, scheduler, model trainer, or execution path is added.

**Tech Stack:** Python dataclasses, JSONL repository, server-rendered/static HTML, pytest.

---

## File Structure

- Modify `src/forecast_loop/strategy_research.py`: add a `StrategyRevisionCandidate` dataclass and resolver logic.
- Modify `src/forecast_loop/dashboard.py`: include revision candidate fields in `DashboardSnapshot` and render them in `render_strategy_research_panel`.
- Modify `src/forecast_loop/operator_console.py`: include revision candidate fields in `OperatorConsoleSnapshot`, research page, and overview preview.
- Modify `tests/test_dashboard.py`: add failing coverage that dashboard shows the DRAFT revision candidate even when latest autopilot run points to the parent strategy.
- Modify `tests/test_operator_console.py`: add failing coverage that operator console research and overview pages show the DRAFT revision candidate.
- Modify `README.md` and `docs/PRD.md`: document that PR13 makes PR12 revisions visible.
- Create `docs/architecture/PR13-strategy-revision-visibility.md`.
- Create `docs/reviews/2026-04-29-pr13-strategy-revision-visibility-review.md` after independent review.

## Task 1: TDD For Revision Candidate UX

**Files:**

- Modify: `tests/test_dashboard.py`
- Modify: `tests/test_operator_console.py`

- [ ] **Step 1: Add dashboard failing test**

Create a failed paper-shadow outcome, existing autopilot run, DRAFT revision `StrategyCard`, and linked revision `ResearchAgenda`.

Expected dashboard HTML contains:

- `策略修正候選`
- revision card id `strategy-card:dashboard-revision`
- parent card id `strategy-card:dashboard-visible`
- source outcome id `paper-shadow-outcome:dashboard-visible`
- status `DRAFT`
- mutation phrase `Require positive after-cost edge`
- revision agenda id `research-agenda:dashboard-revision`

Run:

```powershell
python -m pytest tests\test_dashboard.py::test_dashboard_shows_strategy_revision_candidate_even_when_autopilot_chain_points_to_parent -q
```

Expected before implementation: fail because the dashboard does not render `策略修正候選`.

- [ ] **Step 2: Add operator console failing test**

Use the same shape for console fixtures.

Expected operator console research page and overview contain:

- `策略修正候選`
- revision card id `strategy-card:visible-revision`
- source outcome id `paper-shadow-outcome:visible`
- revision agenda id `research-agenda:visible-revision`

Run:

```powershell
python -m pytest tests\test_operator_console.py::test_operator_console_shows_strategy_revision_candidate -q
```

Expected before implementation: fail because the console does not render `策略修正候選`.

## Task 2: Add Revision Candidate Resolver

**Files:**

- Modify: `src/forecast_loop/strategy_research.py`

- [ ] **Step 1: Add dataclass**

Add:

```python
@dataclass(slots=True)
class StrategyRevisionCandidate:
    strategy_card: StrategyCard
    research_agenda: ResearchAgenda | None
    source_outcome: PaperShadowOutcome | None
```

- [ ] **Step 2: Extend chain**

Add `revision_candidate: StrategyRevisionCandidate | None` to `StrategyResearchChain`.

- [ ] **Step 3: Resolve latest revision candidate**

Pick the latest card matching all conditions:

- `status == "DRAFT"`
- `decision_basis == "paper_shadow_strategy_revision_candidate"`
- `parameters["revision_source_outcome_id"]` exists
- requested symbol is in `symbols`

Then link:

- source outcome by `revision_source_outcome_id`
- latest research agenda where `card.card_id` is in `strategy_card_ids`

## Task 3: Render Dashboard And Console

**Files:**

- Modify: `src/forecast_loop/dashboard.py`
- Modify: `src/forecast_loop/operator_console.py`

- [ ] **Step 1: Add snapshot fields**

Add latest revision card, agenda, and source outcome fields to both snapshots.

- [ ] **Step 2: Dashboard rendering**

Add a visible block in `render_strategy_research_panel` with Traditional Chinese labels:

- `策略修正候選`
- `來源失敗`
- `父策略`
- `修正重點`
- `重新測試 agenda`

- [ ] **Step 3: Operator console rendering**

Add the same revision candidate block to the research page and a concise line in the overview preview.

## Task 4: Docs

**Files:**

- Modify: `README.md`
- Modify: `docs/PRD.md`
- Create: `docs/architecture/PR13-strategy-revision-visibility.md`

- [ ] **Step 1: Document PR13**

State that PR13 makes PR12 DRAFT revision candidates visible but still does not run retests automatically.

## Task 5: Gates And Review

**Files:**

- Create: `docs/reviews/2026-04-29-pr13-strategy-revision-visibility-review.md`

- [ ] **Step 1: Run gates**

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

- [ ] **Step 2: Independent review**

Use one reviewer subagent only. The reviewer must not edit files and must return P0/P1/P2 findings or `APPROVED`.

- [ ] **Step 3: Publish**

Archive review, commit, push, create PR, wait for CI, merge only after checks pass, then rerun post-merge gates on `main`.
