# AGENTS.md

This file captures the repo-level Codex collaboration rules for this project.

## Core Rules

- Use Traditional Chinese for user-facing status and final reports unless the user explicitly asks otherwise.
- Keep all forecasting, strategy decisions, portfolio state, broker interfaces, and automation behavior paper-only.
- Do not add live trading, real broker/exchange order submission, real API key handling, or automatic strategy promotion.
- Prefer `python .\run_forecast_loop.py ...` in this checkout because it bootstraps `src\` onto `sys.path`.
- Use PowerShell-safe commands. Do not leave raw placeholders such as `<storageDir>` inside executable commands.
- Archive every substantive review under `docs/reviews/`.

## Review Rule

Only use subagents for review. Do not self-review your own changes.

When a final review is needed:

- plan the reviewer role before spawning subagents
- use the smallest role set that separates risk
- prefer the strongest available model and highest reasoning effort
- keep `max_depth = 1` unless there is a strong reason to nest workers
- archive final review results under `docs/reviews/`

## Browser Rule

The user's browser is Edge. Do not assume Chrome.

## Role Catalog

Role files live under `docs/roles/`.

Core roles:

- `docs/roles/controller.md`
- `docs/roles/feature.md`
- `docs/roles/fixer.md`
- `docs/roles/verifier.md`
- `docs/roles/reviewer.md`
- `docs/roles/docs.md`
- `docs/roles/refactor.md`
- `docs/roles/reproducer.md`
- `docs/roles/root-cause.md`

Extended roles for data / research / pipeline work:

- `docs/roles/recovery.md`
- `docs/roles/contract.md`
- `docs/roles/replay.md`
- `docs/roles/data.md`
- `docs/roles/infra.md`
- `docs/roles/ui.md`

## Routing Rules

Choose the smallest role set that cleanly separates risk.

### Use `controller + fixer + verifier + docs`

When the task is:

- a small bugfix
- a PR convergence pass
- a bounded correctness patch

### Use `controller + feature + verifier + reviewer + docs`

When the task is:

- a bounded new feature
- a feature extension with clear acceptance criteria

### Use `controller + refactor + verifier + reviewer + docs`

When the task is:

- structural cleanup
- module extraction
- duplicated logic consolidation

### Use `controller + reproducer + root-cause + fixer + verifier + docs`

When the task is:

- a flaky failure
- an intermittent bug
- an incident-like issue where reproduction is not stable yet

### Use `controller + recovery + contract + replay + verifier + docs`

When the task is:

- loop correctness
- rerun safety
- artifact semantics
- provider coverage or replay behavior

### Use `controller + data + infra + verifier + docs`

When the task is:

- ETL
- pipelines
- evaluation jobs
- CI / scheduler / automation plumbing

### Use `controller + feature + ui + verifier + docs`

When the task is:

- user-facing UI
- component work
- interaction flows

## Ownership Rules

- One mutable file cluster should have one primary worker owner at a time.
- If ownership must move, controller decides and prior owner stops editing.
- Verifier should prefer tests and assertions, not large production rewrites.
- Docs should reflect code reality, not imagined behavior.
- Reviewer should critique and tighten, not silently redesign.

## Worker Lifecycle

- Keep `max_depth = 1` unless there is a very strong reason to nest workers.
- Controller stays alive across the milestone.
- Workers are disposable.

Respawn a worker if:

- its role changes
- its main file cluster changes
- the integrated branch changed substantially
- it is repeating stale assumptions
- the task moved from implementation to verification or vice versa

## Handoff Protocol

Every worker handoff should state:

- what it changed
- what it deliberately did not change
- what it assumes is true
- what still looks risky
- what tests were added or updated

## Done Rule

A role task is done only when:

- scope stayed inside the role
- changes are coherent
- tests or evidence match the claimed behavior
- handoff is explicit

