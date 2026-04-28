# Codex Governance Docs And Prompts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn PR11 into a repo-level governance package for ChatGPT Pro / Codex controller decisions, worker routing, review-only gates, Windows execution, and reusable prompts.

**Architecture:** This is a docs-and-tests milestone. It must not create a fake controller runtime service, broker adapter, live trading path, or background daemon. It adds architecture/runbook/prompt documents plus lightweight tests that verify the documents exist, include the required machine gates, and keep the role catalog aligned with `docs/roles/`.

**Tech Stack:** Markdown documentation, pytest docs checks, GitHub PR workflow.

---

## File Structure

- Create `docs/architecture/PR11-codex-governance-docs-prompts.md`: architecture decision for controller artifacts, prompt templates, acceptance gates, and non-runtime boundary.
- Create `docs/controller/controller-governance.md`: controller decision schema, routing protocol, role-set selection, review policy, and done rules.
- Create `docs/runbooks/windows-autopilot-controller.md`: Windows PowerShell runbook for autonomous PR execution, machine gates, GitHub flow, runtime exclusion, and Edge browser rule.
- Create `docs/prompts/controller-decision-template.md`: reusable controller decision artifact template.
- Create `docs/prompts/worker-handoff-template.md`: reusable worker handoff template matching AGENTS.md.
- Create `docs/prompts/final-reviewer-prompt.md`: reusable independent reviewer prompt.
- Modify `README.md`: record PR11 as implemented and link to the new docs.
- Modify `docs/PRD.md`: record controller governance docs/prompts as current capability.
- Modify `docs/architecture/autonomous-alpha-factory-master-decision.md`: mark PR11 completed without changing the required future strategy sequence.
- Add `tests/test_governance_docs.py`: checks for required docs, required gate commands, role catalog alignment, and absence of placeholder language.
- Add `docs/reviews/2026-04-29-pr11-codex-governance-docs-prompts-review.md`: archive the independent reviewer result after implementation.

## Task 1: TDD For Governance Docs

**Files:**

- Create: `tests/test_governance_docs.py`

- [x] **Step 1: Add failing file-existence and content tests**

Create tests that assert these files exist:

- `docs/architecture/PR11-codex-governance-docs-prompts.md`
- `docs/controller/controller-governance.md`
- `docs/runbooks/windows-autopilot-controller.md`
- `docs/prompts/controller-decision-template.md`
- `docs/prompts/worker-handoff-template.md`
- `docs/prompts/final-reviewer-prompt.md`

Also assert the docs include:

- `ChatGPT Pro Controller`
- `controller_decision_id`
- `python -m pytest -q`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
- `python .\run_forecast_loop.py --help`
- `git diff --check`
- `docs/reviews/`
- `.codex/`
- `paper_storage/`
- `.env`
- `Edge`
- `reviewer subagent`
- `APPROVED`

- [x] **Step 2: Add role catalog alignment test**

Parse `AGENTS.md` for every `docs/roles/*.md` reference and assert each file exists.

- [x] **Step 3: Add placeholder guard**

Fail if the new PR11 governance docs contain `TBD`, `TODO`, `<placeholder>`, `<storageDir>`, or `fill in`.

- [x] **Step 4: Verify RED**

Run:

```powershell
python -m pytest tests\test_governance_docs.py -q
```

Expected: fail because the docs do not exist yet.

## Task 2: Add Governance Architecture And Controller Docs

**Files:**

- Create: `docs/architecture/PR11-codex-governance-docs-prompts.md`
- Create: `docs/controller/controller-governance.md`

- [x] **Step 1: Write architecture doc**

Document:

- PR11 status and scope.
- ChatGPT Pro Controller is represented by docs/artifacts/prompts, not a fake service.
- Controller decision artifact schema.
- Allowed worker roles and role-routing policy.
- Machine gates before merge.
- Review archive requirement.
- Runtime/secrets exclusion.
- Current boundary: no real orders / no real capital / no committed secrets; future live design requires explicit separate stage.

- [x] **Step 2: Write controller governance doc**

Document:

- Controller preflight.
- Role-set selection from AGENTS.md.
- Worker prompt structure.
- Handoff protocol.
- Final reviewer prompt.
- Merge/stop rules.
- How to create operator digest after a run.

## Task 3: Add Windows Runbook And Prompt Templates

**Files:**

- Create: `docs/runbooks/windows-autopilot-controller.md`
- Create: `docs/prompts/controller-decision-template.md`
- Create: `docs/prompts/worker-handoff-template.md`
- Create: `docs/prompts/final-reviewer-prompt.md`

- [x] **Step 1: Write Windows runbook**

Include exact PowerShell commands for:

- preflight status
- branch creation
- machine gates
- staging only allowed files
- PR creation
- CI inspection
- merge
- runtime/secrets exclusion
- Edge browser rule

- [x] **Step 2: Write controller decision template**

Include concrete fields:

- `controller_decision_id`
- `created_at`
- `decision_type`
- `scope`
- `decision`
- `rationale`
- `allowed_worker_roles`
- `blocked_actions`
- `affected_files`
- `acceptance_summary`
- `machine_gates`

- [x] **Step 3: Write worker handoff template**

Match AGENTS.md handoff protocol:

- what changed
- what deliberately did not change
- assumptions
- remaining risks
- tests added or updated

- [x] **Step 4: Write final reviewer prompt**

Make it explicit that reviewer subagent reviews only, does not edit files, and returns findings or `APPROVED`.

## Task 4: Update Existing Project Docs

**Files:**

- Modify: `README.md`
- Modify: `docs/PRD.md`
- Modify: `docs/architecture/autonomous-alpha-factory-master-decision.md`

- [x] **Step 1: Update README**

Add PR11 to current status and link to the controller governance docs, runbook, and prompts.

- [x] **Step 2: Update PRD**

Record controller governance docs/prompts as implemented current capability.

- [x] **Step 3: Update master decision**

Mark PR11 completed and state the next sequence returns to strategy/research capability work rather than fake runtime service work.

## Task 5: Verification, Review, Commit, PR

**Files:**

- Add: `docs/reviews/2026-04-29-pr11-codex-governance-docs-prompts-review.md`

- [x] **Step 1: Run full gates**

Run:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

- [x] **Step 2: Request independent reviewer subagent**

Use one reviewer subagent with strongest model and highest reasoning. Reviewer must not edit files.

- [x] **Step 3: Archive review**

Write reviewer findings, fixes, and final verdict under `docs/reviews/`.

- [ ] **Step 4: Commit and publish**

Stage only PR11 files, commit, push, create PR, wait for CI, and merge only when all machine gates pass.
