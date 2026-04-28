# Strategy-Visible UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the local read-only operator console expose concrete strategy hypothesis, evidence gates, leaderboard state, paper-shadow attribution, and autopilot next research action.

**Architecture:** Keep this PR as a UX/read-model slice. Load existing PR6-PR9 artifacts into `OperatorConsoleSnapshot`, derive a compact strategy research view in `operator_console.py`, and render it in Traditional Chinese without creating new strategy, backtest, or execution behavior.

**Tech Stack:** Python dataclasses, JSONL artifact repository, server-rendered static HTML, pytest.

---

## File Structure

- Modify `src/forecast_loop/operator_console.py`: extend the snapshot with latest strategy card, experiment trial, locked evaluation, leaderboard entry, paper-shadow outcome, research agenda, and research autopilot run; render a strategy-visible research page and stronger overview preview.
- Modify `src/forecast_loop/dashboard.py`: surface the same strategy research context in the static `render-dashboard` output.
- Modify `tests/test_operator_console.py`: add failing tests that seed strategy/research artifacts and assert Traditional Chinese UX labels plus concrete IDs/metrics are visible.
- Modify `tests/test_dashboard.py`: add a failing test proving static dashboard exposes strategy card, gates, leaderboard, paper-shadow attribution, and next research action.
- Modify `README.md`: document the operator console strategy-visible research surface.
- Modify `docs/PRD.md`: update the current gap/status language so PR10 is described as implemented after this change.
- Add `docs/reviews/2026-04-29-pr10-strategy-visible-ux-review.md`: archive the independent reviewer result after implementation.

## Task 1: TDD For Strategy-Visible Research Page

**Files:**
- Modify: `tests/test_operator_console.py`

- [x] **Step 1: Add artifact helpers to seed PR6-PR9 research chain**

Add helpers for `StrategyCard`, `ExperimentTrial`, `LockedEvaluationResult`, `LeaderboardEntry`, `PaperShadowOutcome`, `ResearchAgenda`, and `ResearchAutopilotRun`. Use fixed IDs such as `strategy-card:visible`, `leaderboard-entry:visible`, and `research-autopilot-run:visible`.

- [x] **Step 2: Add failing research-page test**

Add a test that renders `page="research"` and asserts these user-facing strings appear:

```python
assert "目前策略假設" in html
assert "BTC strategy visibility candidate" in html
assert "Breakout continuation should beat the baseline after costs." in html
assert "進場規則" in html
assert "突破前高且成交量放大" in html
assert "Evidence Gates" in html
assert "locked-evaluation:visible" in html
assert "alpha_score" in html
assert "0.2100" in html
assert "Leaderboard" in html
assert "leaderboard-entry:visible" in html
assert "Paper-shadow 歸因" in html
assert "negative_excess_return" in html
assert "下一步研究動作" in html
assert "REVISE_STRATEGY" in html
assert "research-autopilot-run:visible" in html
```

- [x] **Step 3: Add failing overview-preview test**

Assert overview contains a compact strategy research preview before the generic artifact counts:

```python
assert "策略研究焦點" in overview
assert overview.index("策略研究焦點") < overview.index("Artifact Counts")
assert "strategy-card:visible" in overview
assert "leaderboard-entry:visible" in overview
assert "REVISE_STRATEGY" in overview
```

- [x] **Step 4: Run the targeted test to verify RED**

Run:

```powershell
python -m pytest tests\test_operator_console.py::test_research_page_surfaces_strategy_hypothesis_gates_shadow_and_autopilot -q
```

Expected: fail because `OperatorConsoleSnapshot` does not load or render these research artifacts yet.

## Task 2: Load Research Artifacts Into Snapshot

**Files:**
- Modify: `src/forecast_loop/operator_console.py`

- [x] **Step 1: Import the missing models**

Add model imports for `ExperimentTrial`, `LeaderboardEntry`, `LockedEvaluationResult`, `PaperShadowOutcome`, `ResearchAgenda`, `ResearchAutopilotRun`, and `StrategyCard`.

- [x] **Step 2: Extend `OperatorConsoleSnapshot`**

Add fields:

```python
latest_strategy_card: StrategyCard | None
latest_experiment_trial: ExperimentTrial | None
latest_locked_evaluation: LockedEvaluationResult | None
latest_leaderboard_entry: LeaderboardEntry | None
latest_paper_shadow_outcome: PaperShadowOutcome | None
latest_research_agenda: ResearchAgenda | None
latest_research_autopilot_run: ResearchAutopilotRun | None
```

- [x] **Step 3: Load symbol-scoped artifacts**

In `build_operator_console_snapshot`, load existing repository methods:

```python
strategy_cards = [card for card in _safe_load(repository.load_strategy_cards) if symbol in card.symbols]
experiment_trials = [trial for trial in _safe_load(repository.load_experiment_trials) if trial.symbol == symbol]
locked_evaluations = _safe_load(repository.load_locked_evaluation_results)
leaderboard_entries = [entry for entry in _safe_load(repository.load_leaderboard_entries) if entry.symbol == symbol]
paper_shadow_outcomes = [outcome for outcome in _safe_load(repository.load_paper_shadow_outcomes) if outcome.symbol == symbol]
research_agendas = [agenda for agenda in _safe_load(repository.load_research_agendas) if agenda.symbol == symbol]
research_autopilot_runs = [run for run in _safe_load(repository.load_research_autopilot_runs) if run.symbol == symbol]
```

Use `_latest(...)` for the new snapshot fields.

- [x] **Step 4: Count the new artifacts**

Add counts for `strategy_cards`, `experiment_trials`, `locked_evaluations`, `leaderboard_entries`, `paper_shadow_outcomes`, `research_agendas`, and `research_autopilot_runs`.

- [x] **Step 5: Run the targeted test**

Run the same targeted pytest command. Expected: still fail because rendering is not implemented.

## Task 3: Render Strategy-Visible UX

**Files:**
- Modify: `src/forecast_loop/operator_console.py`

- [x] **Step 1: Replace `_render_research` with a strategy-first layout**

Top row:
- `目前策略假設`: strategy card name, hypothesis, family/version/status, parameters.
- `下一步研究動作`: latest research autopilot run status/action/blockers.
- `Leaderboard`: rankable, alpha score, promotion stage, blocked reasons.

Second row:
- `Evidence Gates`: locked evaluation pass/rankable, alpha score, blocked reasons, gate metrics.
- `Backtest / Walk-forward`: keep existing backtest and walk-forward metrics.
- `Paper-shadow 歸因`: outcome grade, excess return after costs, failure attributions, recommended strategy action.

Third row:
- `策略規則`: signal description, entry rules, exit rules, risk rules, data requirements.
- `Research Agenda`: title, hypothesis, acceptance criteria, blocked actions.
- `Autopilot Steps`: agenda -> strategy -> evaluation -> decision -> paper-shadow timeline.

- [x] **Step 2: Add small HTML helpers**

Add helpers:

```python
def _dict_rows(values: dict[str, object]) -> str: ...
def _plain_list(items: list[str], *, empty: str = "none") -> str: ...
def _autopilot_steps(run: ResearchAutopilotRun | None) -> str: ...
def _strategy_research_preview(snapshot: OperatorConsoleSnapshot) -> str: ...
```

Each helper must escape user/artifact text and render empty states instead of failing.

- [x] **Step 3: Add overview preview**

Insert a `策略研究焦點` card in `_render_overview` before `Artifact Counts`. It should show latest strategy card, leaderboard entry, paper-shadow action, and autopilot next research action.

- [x] **Step 4: Run targeted tests**

Run:

```powershell
python -m pytest tests\test_operator_console.py -q
```

Expected: all operator console tests pass.

## Task 4: Docs And Review Archive

**Files:**
- Modify: `README.md`
- Modify: `docs/PRD.md`
- Add: `docs/reviews/2026-04-29-pr10-strategy-visible-ux-review.md`

- [x] **Step 1: Update README**

Add a short PR10 status note that both `render-dashboard` and `operator-console --page research` now surface strategy hypothesis, rules, locked gates, leaderboard state, paper-shadow attribution, and research autopilot next action.

- [x] **Step 2: Update PRD**

Move strategy-visible UX from current deferred gap into implemented current capability, while still stating that deeper strategy mutation workers remain future work.

- [x] **Step 3: Request independent subagent review**

Use one reviewer subagent only, with `gpt-5.5` and `xhigh`, to review the diff for:
- incorrect artifact linking;
- missing tests;
- misleading UX claims;
- live execution/secrets/runtime artifact leakage.

- [x] **Step 4: Archive the reviewer result**

Write the reviewer verdict and verification commands to `docs/reviews/2026-04-29-pr10-strategy-visible-ux-review.md`.

## Task 5: Full Gate, Commit, Push, PR

**Files:**
- No production scope expansion.

- [x] **Step 1: Run required gates**

Run:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

- [x] **Step 2: Verify no runtime/secrets are staged**

Run:

```powershell
git status --short
```

Ensure `.codex/`, `paper_storage/`, `reports/`, `output/`, `.env`, and secrets are not staged.

- [ ] **Step 3: Commit and publish**

Commit with:

```powershell
git add src\forecast_loop\operator_console.py tests\test_operator_console.py README.md docs\PRD.md docs\superpowers\plans\2026-04-29-strategy-visible-ux.md docs\reviews\2026-04-29-pr10-strategy-visible-ux-review.md
git commit -m "feat: surface strategy research context in console"
git push -u origin codex/strategy-visible-ux
```

- [ ] **Step 4: Open PR**

Open draft PR:

```powershell
gh pr create --draft --title "[PR10] Surface strategy-visible UX" --body-file <generated-pr-body>
```

After gates and reviewer approval, mark ready and merge if GitHub reports mergeable.
