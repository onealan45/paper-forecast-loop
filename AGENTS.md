# AGENTS.md

This file captures the repo-level Codex collaboration rules for this project.

## Core Rules

- Use Traditional Chinese for user-facing status and final reports unless the user explicitly asks otherwise.
- Optimize for research ability, prediction quality, backtesting, strategy simulation, and continuous strategy learning. Do not treat operational safety or productization as the primary project goal.
- The hard execution boundary is: do not submit real orders, do not move real capital, and do not commit secrets. Live-money execution remains prohibited.
- `paper-only` names in existing commands, artifacts, and docs should be treated as simulation/backtest compatibility labels, not as a restriction on research scope or data sources.
- Any useful information source may be considered for research, prediction, backtesting, and simulation, including market, macro, fundamental, sentiment, flow, alternative, local, and external sources.
- Natural-language strategy generation and natural-language control by the user are allowed. The loop may turn user strategy instructions into research hypotheses, backtests, simulations, and decision artifacts.
- Tool-rich automation is acceptable when it improves research, prediction, backtesting, or self-reflection. Sandbox or broker gates should block execution only, not strategy research, forecasting, simulation, or reporting.
- Learn from Vibe-Trading-style capabilities where useful: strategy skills, self-evolving skills, swarm-style research roles, MCP/tool surfaces, agent memory, broad data loaders, backtest engines, validation utilities, strategy export/review surfaces, and shadow-account style simulation.
- UX should expose concrete strategy content: current hypothesis, reasoning, evidence, prediction basis, backtest/simulation result, failure conditions, and next research action. Do not let health/status panels dominate strategy visibility.
- Do not add real broker/exchange order submission, real API key handling, or automatic promotion into live-money execution.
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
