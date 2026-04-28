# Strategy Revision Candidates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first self-evolving strategy loop primitive: generate a concrete draft strategy revision candidate from a failed paper-shadow outcome.

**Architecture:** Keep this as a bounded research/simulation feature. Do not add a fake autonomous strategist runtime, model training, live trading, or broker execution. Reuse existing `StrategyCard` and `ResearchAgenda` artifacts: the generator creates a DRAFT child `StrategyCard` with `parent_card_id` and a linked revision `ResearchAgenda`, using paper-shadow failure attribution as the mutation basis.

**Tech Stack:** Python dataclasses, JSONL artifact repository, existing CLI patterns, pytest.

---

## File Structure

- Create `src/forecast_loop/strategy_evolution.py`: pure artifact-level revision generator.
- Modify `src/forecast_loop/cli.py`: add `propose-strategy-revision`.
- Modify `tests/test_research_autopilot.py`: add behavior and CLI tests using existing strategy/autopilot fixtures.
- Modify `README.md`: document the command and artifact behavior.
- Modify `docs/PRD.md`: record the first self-evolving strategy primitive as current capability.
- Create `docs/architecture/PR12-strategy-revision-candidates.md`: architecture note and boundaries.
- Create `docs/reviews/2026-04-29-pr12-strategy-revision-candidates-review.md`: archive independent reviewer result.

## Task 1: TDD For Revision Candidate Generation

**Files:**

- Modify: `tests/test_research_autopilot.py`

- [ ] **Step 1: Add failing direct generator test**

Add a test that seeds a strategy card, paper-shadow `RETIRE` outcome, and linked artifacts. It should call:

```python
from forecast_loop.strategy_evolution import propose_strategy_revision
```

Expected assertions:

- returned revision card has `status == "DRAFT"`;
- `parent_card_id == original.card_id`;
- `author == "codex-strategy-evolution"`;
- `decision_basis == "paper_shadow_strategy_revision_candidate"`;
- `parameters["revision_source_outcome_id"] == outcome.outcome_id`;
- `parameters["revision_failure_attributions"]` contains `negative_excess_return`;
- entry/risk rules include concrete revision text, not only copied parent rules;
- returned agenda links to the revision card and says it is for revision testing.

- [ ] **Step 2: Add failing no-revision-needed test**

Promotion-ready paper-shadow outcomes should not create a revision. Assert `ValueError` includes `does not require revision`.

- [ ] **Step 3: Add failing idempotency test**

Calling the generator twice for the same outcome should return the same revision card and agenda; storage should not duplicate them.

- [ ] **Step 4: Add failing CLI test**

Add CLI test for:

```powershell
$storageDir = "$env:TEMP\pr12-revision-cli-test"
$paperShadowOutcomeId = "paper-shadow-outcome:retire"
python .\run_forecast_loop.py propose-strategy-revision --storage-dir $storageDir --paper-shadow-outcome-id $paperShadowOutcomeId --created-at 2026-04-28T14:00:00+00:00
```

Expected JSON keys:

- `revision_strategy_card.card_id`
- `revision_research_agenda.agenda_id`
- `revision_strategy_card.parent_card_id`
- `revision_research_agenda.strategy_card_ids`

- [ ] **Step 5: Verify RED**

Run:

```powershell
python -m pytest tests\test_research_autopilot.py::test_propose_strategy_revision_creates_draft_child_card_and_agenda -q
```

Expected: fail because `forecast_loop.strategy_evolution` does not exist.

## Task 2: Implement Revision Generator

**Files:**

- Create: `src/forecast_loop/strategy_evolution.py`

- [ ] **Step 1: Add lookup helpers**

Load `PaperShadowOutcome` by ID and require its parent `StrategyCard`.

- [ ] **Step 2: Add revision classifier**

Support attribution-aware mutation text:

- `negative_excess_return`: add stricter confirmation rule and baseline-edge retest requirement.
- `adverse_excursion_breach`: add smaller simulated max position / drawdown guard.
- `turnover_breach`: add cooldown / minimum hold rule.
- unknown attribution: add explicit research rule that the next trial must isolate that attribution.

- [ ] **Step 3: Create DRAFT child StrategyCard**

Copy parent family/symbols/data requirements, set `parent_card_id`, bump version by appending `.rev1` to the parent version, set author `codex-strategy-evolution`, and add revision metadata into `parameters`.

- [ ] **Step 4: Create linked ResearchAgenda**

Agenda title should include revision, hypothesis should mention paper-shadow failure attribution, and `strategy_card_ids` should contain the revision card id.

- [ ] **Step 5: Keep idempotency**

If the same revision card or agenda already exists, return the existing artifacts.

## Task 3: CLI Integration

**Files:**

- Modify: `src/forecast_loop/cli.py`

- [ ] **Step 1: Add parser**

Add command:

```powershell
$storageDir = ".\paper_storage\manual-research"
$paperShadowOutcomeId = "paper-shadow-outcome:example"
$createdAt = "2026-04-28T14:00:00+00:00"
python .\run_forecast_loop.py propose-strategy-revision --storage-dir $storageDir --paper-shadow-outcome-id $paperShadowOutcomeId --created-at $createdAt
```

Do not leave raw placeholder commands in docs or tests.

- [ ] **Step 2: Add handler**

Use `JsonFileRepository`, parse `created_at`, call `propose_strategy_revision`, and print JSON with both artifacts.

- [ ] **Step 3: Run targeted tests**

```powershell
python -m pytest tests\test_research_autopilot.py -q
```

## Task 4: Docs

**Files:**

- Modify: `README.md`
- Modify: `docs/PRD.md`
- Create: `docs/architecture/PR12-strategy-revision-candidates.md`

- [ ] **Step 1: Architecture doc**

Explain this is the first self-evolving strategy primitive, not a full autonomous strategist.

- [ ] **Step 2: README command docs**

Add command example and explain generated artifacts.

- [ ] **Step 3: PRD status**

Move “no self-evolving strategy loop” language forward: now there is a first revision-candidate primitive, while full autonomous strategy generation/training remains deferred.

## Task 5: Review, Gates, PR

**Files:**

- Create: `docs/reviews/2026-04-29-pr12-strategy-revision-candidates-review.md`

- [ ] **Step 1: Run gates**

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

- [ ] **Step 2: Request independent reviewer subagent**

One reviewer subagent only; review-only; strongest model/highest reasoning.

- [ ] **Step 3: Archive review**

Archive findings, fixes, and final `APPROVED` under `docs/reviews/`.

- [ ] **Step 4: Commit / push / PR / CI / merge**

Stage only PR12 files. Do not stage `.codex/`, `paper_storage/`, `reports/`, `output/`, `.env`, or secrets.
