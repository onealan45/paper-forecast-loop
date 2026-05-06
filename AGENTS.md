# AGENTS.md

This file captures the repo-level Codex collaboration rules for this project.

## Core Rules

- Treat `docs/architecture/autonomous-alpha-factory-master-decision.md` as the
  current master execution decision after M7A. If another local note conflicts
  with it, follow the master decision unless the user explicitly supersedes it.
- The immediate next milestone after M7A is PR0 Reviewability And Formatting
  Gate. Do not continue adding strategy intelligence on top of pathological
  long-line source files unless PR0 is complete or a reviewer proves it is not
  needed.
- Use Traditional Chinese for user-facing status and final reports unless the user explicitly asks otherwise.
- Optimize for research ability, prediction quality, backtesting, strategy simulation, and continuous strategy learning. Do not treat operational safety or productization as the primary project goal.
- The current execution boundary is: do not submit real orders, do not move real capital, and do not commit secrets. This is the present project boundary, not a permanent product statement; future automated trading work would require an explicit new user request and a separate design stage.
- `paper-only` names in existing commands, artifacts, and docs should be treated as simulation/backtest compatibility labels, not as a restriction on research scope or data sources.
- Any useful information source may be considered for research, prediction, backtesting, and simulation, including market, macro, fundamental, sentiment, flow, alternative, local, and external sources.
- Natural-language strategy generation and natural-language control by the user are allowed. The loop may turn user strategy instructions into research hypotheses, backtests, simulations, and decision artifacts.
- Tool-rich automation is acceptable when it improves research, prediction, backtesting, or self-reflection. Sandbox or broker gates should block execution only, not strategy research, forecasting, simulation, or reporting.
- Learn from Vibe-Trading-style capabilities where useful: strategy skills, self-evolving skills, swarm-style research roles, MCP/tool surfaces, agent memory, broad data loaders, backtest engines, validation utilities, strategy export/review surfaces, and shadow-account style simulation.
- UX should expose concrete strategy content: current hypothesis, reasoning, evidence, prediction basis, backtest/simulation result, failure conditions, and next research action. Do not let health/status panels dominate strategy visibility.
- Do not implement a fake ChatGPT Pro Controller runtime service. Record
  controller-level decisions as artifacts, docs, prompts, research agendas,
  acceptance gates, and operator digests.
- Keep the Alpha Factory principle explicit: strategy search space may broaden,
  but evaluation protocol, holdout, trial budget, cost model, gates, and
  leaderboard rules must not move after results are known.
- Do not add real broker/exchange order submission, real API key handling, or automatic promotion into live-money execution in the current research/simulation scope.
- Prefer `python .\run_forecast_loop.py ...` in this checkout because it bootstraps `src\` onto `sys.path`.
- Use PowerShell-safe commands. Do not leave raw placeholders such as `<storageDir>` inside executable commands.
- Archive every substantive review under `docs/reviews/`.

## Review Rule

Only subagents may perform substantive review of repo changes, including code,
tests, docs, instructions, and automation rules. The controller may coordinate
review, summarize reviewer findings, and check that review artifacts exist, but
must not self-approve its own changes unless the user explicitly exempts a
trivial non-substantive edit.

When a final review is needed:

- plan the reviewer role before spawning subagents
- use the smallest role set that separates risk
- prefer the strongest available model and highest reasoning effort
- organize current subagents before spawning new ones to avoid hitting
  worker-count limits
- keep `max_depth = 1` unless there is a strong reason to nest workers
- treat changed files as the starting point, not the review boundary
- inspect nearby readers, builders, schemas, CLI output, storage helpers, and
  tests when they may affect the claimed behavior
- do not treat controller-reported verification as proof
- reviewers must independently inspect whether tests and evidence cover intended
  failure modes, false positives, false negatives, and compatibility paths
- check that review conclusions are supported by file references, tests, or
  command evidence
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
- Controller should integrate work and enforce scope, not hide unresolved worker
  disagreements.
- Workers should not continue editing after their ownership has moved.

## Worker Lifecycle

- Keep `max_depth = 1` unless there is a very strong reason to nest workers.
- Controller stays alive across the milestone.
- Workers are disposable.
- Prefer respawning a focused worker over stretching one worker across unrelated
  roles.
- Before spawning new workers, summarize active workers and close or retire stale
  ones when possible.

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
- what verification commands were run
- what remains blocked or intentionally out of scope

## Done Rule

A role task is done only when:

- scope stayed inside the role
- changes are coherent
- tests or evidence match the claimed behavior
- handoff is explicit
- residual risks are stated
- no final self-review was used as merge evidence

## PR Review Prompt Requirements

Every final reviewer prompt should include:

- role file path, usually `docs/roles/reviewer.md`
- strict instruction: review only, do not edit files
- repo path
- branch name
- base SHA or base branch
- PR intent
- changed files
- verification already run
- explicit review tasks
- output format requiring verdict, findings, residual risks, and tests reviewed

Reviewer output must use:

- `Verdict: APPROVED` or `Verdict: CHANGES_REQUESTED`
- severity-ranked findings
- file and line references when available
- residual risks
- tests reviewed
- no implementation patches

## Review Quality Bar

A reviewer must check:

- whether the implementation actually satisfies the stated intent
- whether behavior changed outside the intended scope
- whether old artifacts remain backward compatible
- whether false positives and false negatives are covered
- whether severity, repair, blocking, and health semantics are correct
- whether tests assert behavior rather than only snapshotting strings
- whether fixtures match realistic artifact shapes
- whether CLI behavior, storage behavior, and docs agree
- whether changed files depended on nearby unchanged code that also needed
  review

## Verification Quality Bar

A verifier must prefer:

- focused regression tests for the new behavior
- compatibility tests for old artifacts and old storage shapes
- negative tests for malformed or missing evidence
- command-level verification when CLI behavior is part of the change
- exact command output summaries in handoff

A verifier must not:

- rewrite large production modules just to make testing easier
- rely only on happy-path tests
- claim full coverage when edge cases were not exercised
- treat `pytest passed` as proof that acceptance criteria were met

## Documentation Rule

Docs changes must:

- describe actual implemented behavior
- preserve current execution boundaries
- avoid promising live trading, real orders, broker submission, or real capital
  movement
- name known limitations and residual risks
- stay aligned with architecture docs, role docs, and CLI behavior

## Storage And Artifact Rule

For artifact, replay, health, or research-quality changes:

- preserve append-only and audit-friendly behavior where applicable
- keep legacy artifacts readable unless the task explicitly migrates them
- distinguish missing evidence from weak evidence
- distinguish repair-required findings from informational findings
- avoid fabricating future market results, paper-shadow outcomes, or evaluation
  evidence
- keep ids, timestamps, symbol scope, and provenance traceable

## Final Report Rule

Final reports should include:

- concise summary
- files changed
- behavior changed
- tests run
- review status
- residual risks
- next recommended action only when useful
