# PR11 Codex Governance Docs And Prompts

## Status

Implemented as a docs-and-prompts milestone after PR10 Strategy-Visible UX.

PR11 does not add a controller daemon, scheduler, broker adapter, data provider,
or execution service. It records how ChatGPT Pro Controller decisions, Codex
worker routing, reviewer subagent gates, and Windows autopilot runs should be
represented inside the repository.

## Purpose

The project now has a research-first Alpha Factory direction, strategy-visible
UX, research agendas, autopilot loop records, locked evaluation gates, and
paper-shadow learning. The missing governance layer is not another runtime
service. The missing layer is a repeatable operating contract:

- how a controller decision is recorded;
- how worker roles are selected;
- how review stays independent;
- how machine gates are run;
- how Windows/GitHub execution is performed without committing runtime files;
- how reusable prompts are written so future autonomous runs do not depend on
  memory of one chat thread.

## Controller Boundary

ChatGPT Pro Controller is a human-supervised workflow role, not a product
service in this repository. The repo must represent controller output through
artifacts, docs, prompts, acceptance gates, and review archives.

Allowed PR11 artifacts:

- controller governance docs;
- controller decision template;
- worker handoff template;
- final reviewer prompt;
- Windows autopilot runbook;
- review archive entries under `docs/reviews/`.

Blocked PR11 artifacts:

- fake online controller runtime;
- background service that claims to be ChatGPT Pro;
- broker or exchange execution;
- real API key handling;
- runtime storage such as `.codex/`, `paper_storage/`, `reports/`, `output/`,
  or `.env`.

## Controller Decision Artifact

Every controller decision that changes project direction should be recordable
with these fields:

```yaml
controller_decision_id: controller-decision:2026-04-29-example
created_at: 2026-04-29T00:00:00+08:00
decision_type: roadmap | architecture | repair | merge | research_direction
scope: affected milestone, PR, or artifact family
decision: concrete decision written in Traditional Chinese
rationale: why this decision improves research, prediction, simulation, or governance
allowed_worker_roles:
  - controller
  - feature
  - verifier
  - reviewer
  - docs
blocked_actions:
  - real order submission
  - real capital movement
  - committed secrets
affected_files:
  - docs/architecture/example.md
acceptance_summary:
  - tests pass
  - independent reviewer subagent returns APPROVED
machine_gates:
  - python -m pytest -q
  - python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
  - python .\run_forecast_loop.py --help
  - git diff --check
```

The template lives at
[`docs/prompts/controller-decision-template.md`](../prompts/controller-decision-template.md).

## Worker Routing Policy

Worker routing follows `AGENTS.md` and `docs/roles/`. Use the smallest role set
that cleanly separates risk.

Default PR11 routing:

- `controller`: owns scope, branch, gates, integration, and role plan.
- `docs`: writes docs that match the implementation.
- `verifier`: runs tests and checks assertions, preferably through machine
  gates rather than broad rewrites.
- `reviewer`: independent reviewer subagent only; no edits.

For implementation-heavy future PRs, use the role combinations in `AGENTS.md`.
Do not spawn workers just to create the appearance of process. Spawn when the
work can be separated by ownership and risk.

## Review Policy

Self-review is not a merge gate.

Before merge, a reviewer subagent must receive:

- branch name and scope;
- changed file summary;
- tests and machine gates already run;
- explicit instruction to review only and not edit files;
- instructions to return P0/P1/P2 findings or `APPROVED`.

The final review result must be archived under `docs/reviews/` before merge.

## Machine Gates

Every PR after PR11 must run at least:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Milestone-specific smoke tests are required when a PR touches CLI, storage,
dashboard, ingestion, backtest, research gates, broker/sandbox simulation, or
operator console behavior.

## Runtime And Secret Exclusion

Do not commit:

- `.codex/`
- `paper_storage/`
- `reports/`
- `output/`
- `.env`
- secrets
- downloaded private notes unless explicitly converted into repo docs with
  sensitive content removed

Use precise staging paths instead of `git add .` when runtime files are present.

## Windows And Browser Assumptions

The default local shell is PowerShell. Commands in docs should be PowerShell-safe
and should not use raw placeholder arguments in executable command examples.

The user's browser is Edge. Browser testing or UX inspection docs should say
Edge when a specific browser is needed.

## Acceptance

PR11 is complete when:

- this architecture doc exists;
- controller governance, Windows runbook, and prompt templates exist;
- tests prove the docs contain required gates and role catalog links resolve;
- README and PRD describe PR11 as implemented;
- independent reviewer subagent returns `APPROVED`;
- review is archived under `docs/reviews/`;
- no runtime, secret, or storage artifact is committed.
