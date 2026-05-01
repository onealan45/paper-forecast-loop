# PRD: AI Strategy Research And Prediction Lab

**Version:** 0.1
**Date:** 2026-04-22
**Status:** Draft
**Source:** Consolidated from prior product Q&A in this thread

## 1. Product Summary

This project is an **AI-first strategy research and prediction lab**.

It is not a productization project and, in the current scope, it is not a live
order-execution system.
Its purpose is to:

- generate recurring market forecasts from public data
- wait for the prediction window to complete
- validate forecast quality
- compare forecast quality against baselines
- review results
- produce a strategy decision for the next horizon for research, backtesting,
  and simulation
- discover, test, and refine strategies through natural-language control
- raise Codex-ready repair requests when health checks find blocking failures
- present concrete strategies, backtests, predictions, and research rationale in
  the UI

The core product idea is:

> The user is using natural language to direct an AI research loop that studies markets, creates strategies, backtests them, predicts outcomes, and reflects on what works.

The current execution boundary is narrow:

> Do not place real orders and do not move real capital.

This is the present research/simulation boundary, not a permanent product
statement. Future automated trading would require an explicit new user request
and a separate design stage.

Other tools, data sources, strategy generation methods, and automated research
loops are acceptable when they improve research, backtesting, prediction,
simulation, or strategy reflection.

## 1.0 User Direction Update

The user's current preference is:

- research ability and prediction ability are more important than conservative
  safety framing;
- the system may use any useful information source, not only public data, as
  long as the source is recorded well enough for research use;
- natural-language strategy generation is acceptable because the user controls
  the system through natural language;
- self-evolving skills are desirable because the user wants continuous study,
  learning, reflection, and strategy improvement;
- large tool access inside the automated loop is acceptable when it is bounded
  by the no-real-order rule;
- UX must expose concrete strategies, hypotheses, backtests, prediction logic,
  and strategy changes instead of only artifact health and system status;
- sandbox or broker safety gates must not block research simulation. They only
  exist to prevent accidental real execution.

## 1.1 Research Background: Alpha Factory Direction

The current master decision after M7A is recorded in
[`docs/architecture/autonomous-alpha-factory-master-decision.md`](architecture/autonomous-alpha-factory-master-decision.md).
The PRD follows that decision:

- PR0 Reviewability And Formatting Gate comes before more strategy code and is
  complete.
- M7A is only the evidence artifact foundation.
- M7B-M7F implement the Alpha Evidence Engine: source registry, source document
  import, event reliability, market reaction / already-priced checks,
  historical edge, and decision integration.
- PR6 starts the Strategy Card and Experiment Registry layer: strategy cards,
  trial budget snapshots, and append-only experiment trials including failed,
  aborted, and invalid results.
- PR7 starts Locked Evaluation and Leaderboard Gates: split manifests, cost
  model snapshots, locked evaluation results, and leaderboard entries where
  `alpha_score` is impossible until hard gates pass.
- PR8 starts Paper-Shadow Outcome Learning: leaderboard entries can now receive
  simulated shadow-window outcomes with excess return, failure attribution, and
  promotion / retire / quarantine recommendations.
- PR9 starts Research/Paper Autopilot Loop records: agendas and linked loop
  runs make the agenda -> strategy -> evaluation -> decision -> outcome -> next
  action chain inspectable.
- PR10 surfaces that research loop in the read-only UX: dashboard and operator
  console pages now show the current strategy hypothesis, strategy rules, locked
  evidence gates, leaderboard state, paper-shadow attribution, and next
  autopilot research action before raw metadata.
- PR11 adds Codex Governance Docs And Prompts: controller decision template,
  worker handoff template, final reviewer prompt, Windows autopilot runbook, and
  docs tests for required gates and role catalog alignment.
- PR12 adds Strategy Revision Candidates: failed paper-shadow outcomes can
  produce DRAFT child strategy cards and linked retest agendas from explicit
  failure attributions.
- PR13 adds Strategy Revision Visibility: the dashboard and operator console
  show the latest DRAFT revision candidate, parent strategy, source
  paper-shadow failure, mutation rules, and retest agenda.
- PR14 adds Strategy Revision Retest Scaffold: a DRAFT revision candidate can
  produce an idempotent `PENDING` experiment trial and optional locked
  split/cost protocol without fabricating evaluation or promotion evidence.
- PR15 adds Revision Retest Visibility: the dashboard and operator console show
  the pending retest trial, dataset, locked split manifest, and remaining
  required evidence artifacts for the latest DRAFT revision.
- PR16 adds Revision Retest Task Plan: the system can inspect the current DRAFT
  revision retest chain and emit ordered next research tasks, missing inputs,
  and runnable command arguments without writing artifacts.
- PR17 adds Revision Retest Task Plan UX: the dashboard and operator console
  show the next retest task, status, blocked reason, missing inputs, and command
  args without executing them.
- PR18 adds Revision Retest Task Run Log: the system can record the inspected
  retest task plan as an `AutomationRun` so ready/blocked task state is
  auditable without executing the task.
- PR19 adds Revision Retest Run Log UX: the dashboard and operator console show
  the latest retest task run log next to the task plan, including run id,
  status, command, completed time, and task steps.
- PR20 adds Revision Retest Next Task Executor: the first executable retest
  step can run a ready `lock_evaluation_protocol` task, write a cost model, and
  record an execution `AutomationRun` without shell/subprocess dispatch.
- PR21 extends Revision Retest Next Task Executor to
  `generate_baseline_evaluation`, writing baseline evidence and execution audit
  while still blocking backtest and later tasks.
- PR22 extends Revision Retest Next Task Executor to `run_backtest`, writing
  holdout backtest run/result evidence from the locked split window while still
  blocking walk-forward and later tasks.
- PR23 extends Revision Retest Next Task Executor to `run_walk_forward`, writing
  rolling validation evidence from the locked full split window while still
  blocking passed-trial recording and later tasks.
- PR24 extends Revision Retest Next Task Executor to
  `record_passed_retest_trial`, linking baseline, holdout backtest, and
  walk-forward evidence into a PASSED retest trial while still blocking
  leaderboard evaluation and later tasks.
- PR25 extends Revision Retest Next Task Executor to
  `evaluate_leaderboard_gate`, writing locked evaluation and leaderboard-entry
  evidence from the PASSED retest trial while still blocking paper-shadow
  outcome recording and later tasks.
- PR26 extends Revision Retest Next Task Executor to
  `record_paper_shadow_outcome` only when explicit shadow-window observation
  inputs are supplied, preserving the no-fabricated-returns boundary while
  allowing a retest chain to close.
- PR27 adds Revision Retest Completed Chain Visibility: the strategy research
  resolver and read-only UX now treat a completed revision retest chain as
  `PASSED` evidence with no remaining `Next Required` artifacts.
- PR28 adds Revision Retest Autopilot Run support: completed DRAFT revision
  retests can be recorded as research autopilot runs without fabricating a
  strategy decision artifact.
- PR29 adds Revision Retest Autopilot Run CLI: completed revision retest chains
  can now be recorded as research autopilot runs from one command that resolves
  plan evidence automatically.
- PR30 adds Revision Retest Autopilot Run UX: dashboard and operator console
  now show the latest revision-scoped research autopilot run next to the retest
  task plan and task-run log.
- PR31 adds Strategy Lineage Visibility: dashboard and operator console now
  summarize parent strategy lineage, DRAFT revisions, paper-shadow action
  counts, repeated failure attributions, best/worst after-cost excess return,
  and latest shadow outcome.
- PR32 adds Recursive Strategy Lineage: strategy lineage now follows
  multi-generation revision trees back to the original root strategy and
  includes nested revision outcomes in the UX summary.
- PR33 adds Strategy Lineage Tree Visibility: dashboard and operator console
  now expose each revision's parent and depth so nested or branching revision
  paths remain inspectable.
- PR34 adds Strategy Lineage Edge Regressions: branching trees, missing parents,
  and parent cycles are now committed regression cases instead of reviewer-only
  smoke checks.
- PR35 adds Strategy Revision Change Summary: lineage nodes now expose the
  revision's name, status, hypothesis, source outcome, and intended failure
  attributions so strategy self-evolution is readable without raw JSON.
- PR36 adds Strategy Revision Escaping Regressions: strategy names,
  hypotheses, source outcomes, and intended fixes are regression-tested against
  malicious HTML in dashboard and operator console outputs.
- PR37 adds Strategy Lineage Performance Trajectory: each lineage paper-shadow
  outcome now exposes after-cost excess return, delta versus the previous
  outcome, improvement/worsening label, action, and failure attribution in the
  dashboard and operator console.
- PR38 adds Strategy Lineage Performance Verdict: dashboard and operator
  console now show a concise verdict, improvement/worsening/unknown counts,
  latest delta, latest strategy action, and latest failure focus before the raw
  trajectory rows.
- PR39 adds Strategy Lineage Next Research Focus: dashboard and operator
  console now translate the lineage verdict into a concrete next study
  direction for the self-evolving strategy loop.
- PR40 adds Strategy Lineage CLI: the same lineage summary is available as
  read-only JSON for automation and research consumers, including performance
  verdict and next research focus.
- PR41 adds Strategy Lineage Research Agenda creation: the latest lineage next
  research focus can now be persisted as an idempotent research agenda artifact
  for the next self-evolution loop.
- PR42 adds Strategy Lineage Agenda UX: dashboard and operator console now show
  lineage-derived research agendas as explicit strategy research context.
- ChatGPT Pro Controller should be represented by artifacts, docs, prompts,
  agendas, acceptance gates, and digests, not a fake runtime service.
- Strategy generation can be broad, but evaluation protocol and leaderboard
  gates must stay locked after results are known.

The post-M1-M6 research background is recorded in
[`docs/architecture/alpha-factory-research-background.md`](architecture/alpha-factory-research-background.md).

The long-term direction is a research-capable, prediction-focused,
multi-strategy Alpha Factory. The system should generate and evaluate many
candidate alphas, learn from prior experiments, and improve strategy quality
over time.

The core research principle is:

> 放開策略搜尋空間，鎖死評估流程。

This keeps strategy exploration broad while preventing the evaluation loop from
turning into adaptive data mining. The evaluation path should still record fixed
data snapshots, split manifests, trial budgets, leakage checks, baseline
comparisons, validation statistics, holdout evidence, simulation results, and
repair artifacts.

Product implications:

- Candidate strategy generation can be broad, natural-language-driven, and
  self-improving.
- The first implemented self-evolving primitive is revision-candidate creation:
  failed paper-shadow outcomes can become DRAFT child strategy cards that must
  be retested before promotion.
- The first implemented retest bridge now spans scaffold through explicit
  shadow-outcome closure: revision candidates can open a pending experiment
  trial, produce baseline/backtest/walk-forward/locked-evaluation/leaderboard
  evidence through whitelisted executor steps, and then close with explicit
  observed shadow-window inputs.
- Revision candidates must be visible in the UX so the user can inspect what
  the AI is trying to fix next, not only whether the loop is healthy.
- Revision retest scaffolds must also be visible so the user can inspect
  whether a self-evolving idea has a concrete pending trial or is still missing
  dataset, split, backtest, walk-forward, and leaderboard evidence.
- Revision retest planning must make the next research action explicit. If the
  next step needs human or agent-supplied split windows or future shadow returns,
  the system should report that as blocked rather than inventing evidence.
- Revision retest planning must also be visible in the UX so strategy
  self-evolution is inspectable from the operator surfaces, not only from CLI
  JSON.
- Revision retest planning should be auditable: inspecting a plan can write a
  run log, but the log must not create strategy evidence or execute the
  displayed command args.
- Completed revision retest chains must remain visible as completed evidence,
  not disappear back into raw JSONL after the pending scaffold is superseded by
  a PASSED trial.
- Completed revision retest chains may be logged as research autopilot evidence
  without requiring a next-horizon strategy decision, while normal strategy
  runs still require decision evidence.
- Completed revision retest chains should be easy to record from the CLI; the
  operator should not need to manually copy every evidence ID after the plan is
  complete.
- Completed revision retest autopilot runs should be visible in strategy UX
  surfaces, including loop status, next research action, blocked reasons,
  paper-shadow outcome, and recorded steps.
- Strategy UX should show whether a strategy family's failures are concentrated
  around repeated failure attributions or demotion/quarantine actions, not just
  the latest isolated artifact.
- Strategy lineage should remain tied to the original root strategy even when
  the latest visible strategy card is a second- or later-generation revision.
- Strategy lineage should show revision tree structure, not only a flat list,
  when the AI creates nested or sibling revisions.
- Corrupt lineage metadata should fail conservatively: missing parents should
  keep the current card as root, and cycles should terminate without switching
  the UX anchor to an arbitrary cycle member.
- Revision lineage should explain what changed: each visible revision should
  show the hypothesis and failure mode it was intended to repair.
- Natural-language strategy content should remain display-safe in read-only UX,
  because user- or agent-authored hypotheses may contain arbitrary text.
- Strategy lineage should show whether each revision improved or worsened
  paper-shadow evidence, not only that a revision exists.
- Strategy lineage should summarize the trajectory in human terms before raw
  rows so the user can see whether self-evolution is currently improving,
  worsening, stalled, or missing evidence.
- Strategy lineage should translate the performance verdict into a next
  research focus so the user can see what the AI should inspect next.
- The evaluation path must be deterministic, versioned, and auditable.
- Failed experiments must be retained as evidence, not discarded.
- Promotion inside the research loop must depend on research evidence, not on
  one attractive backtest or one recent forecast.
- Provider limitations, data gaps, and validation weaknesses must be visible to
  the operator before any BUY/SELL decision is trusted.
- The next major stage should prioritize Vibe-Trading-style research breadth,
  strategy skills, backtesting, MCP/tool surfaces, and prediction quality while
  preserving the no-real-order rule.

## 2. Problem Statement

Most trading dashboards are either:

- execution terminals that are too dense and manual, or
- AI/chat interfaces that hide performance, state, and risk

The intended research lab must solve both problems:

- show concrete strategy performance first
- make the AI's current research hypothesis obvious
- let the user inspect why the AI predicts something
- let the user see what strategy is being tested, changed, promoted, or rejected
- keep real order execution unavailable

## 3. Product Goals

### Primary Goals

- Make current strategy performance and prediction quality the first thing the
  user understands.
- Make `what strategy the AI is studying or testing right now` obvious at a
  glance.
- Let the user inspect `why the AI made each decision`.
- Run a repeatable `ingest -> forecast -> validate -> score -> compare baseline -> decide -> health audit -> repair if needed` loop.
- Keep the system `no-real-order`, research-focused, and simulation-first.
- Learn from Vibe-Trading-style capabilities: skills, swarm workflows, MCP
  tools, broad data loaders, backtest engines, agent memory, and strategy
  export/review surfaces.
- Preserve a locked research evaluation path so broader strategy search does not
  become uncontrolled data mining.
- Make weak evidence visible by blocking BUY/SELL rather than producing fake
  conviction.
- Keep provider quality, leakage checks, baseline edge, drawdown, costs,
  validation results, and paper-shadow status inspectable from artifacts and UI.
- Increase the share of work spent on analysis, prediction, strategy discovery,
  backtesting, simulation, and strategy self-reflection.

### Secondary Goals

- Provide a practical research UX that exposes concrete strategies and evidence.
- Support automated strategy research with fallback to repair/building mode when
  the system breaks.
- Keep the system explainable and reviewable, but do not optimize for
  productization.
- Support future Alpha Factory stages through data contracts, experiment
  registry, locked splits, validation reports, leaderboard governance, and
  quarantine artifacts.

## 4. Non-Goals

The following are explicitly out of scope for V1:

- real-money trading
- unattended live execution
- real broker or exchange order submission
- real API key handling
- automatic strategy promotion to live capital
- cherry-picking only successful experiments while hiding failed trials
- multi-team collaboration workflows
- multi-account portfolio management
- full mobile parity with desktop depth

## 5. User Profile

### Confirmed Product Shape

- AI-first control surface
- single account
- single strategy
- multi-asset market coverage
- desktop-first for deep work, mobile for summary and alerts

### Likely Primary User

An individual operator or owner-analyst supervising one AI-managed strategy.

Note: the exact persona was not explicitly finalized in the Q&A, but this is the most consistent interpretation of the confirmed constraints above.

## 6. Product Principles

- **Performance first:** The first screen must answer whether the system is making or losing money.
- **Strategy clarity:** The user must immediately know what strategy,
  hypothesis, and prediction the AI is currently testing.
- **Prediction over hygiene:** Artifact health matters, but the visible center
  of the system should be strategy quality and prediction quality.
- **No real orders:** Research, simulation, and tool use may be broad, but the
  system must not submit real orders or move real capital.
- **Concrete strategy visibility:** The UI must show strategy logic, parameters,
  backtest results, prediction rationale, revisions, and next experiments.
- **Learning loop:** The system should remember research lessons and evolve
  reusable strategy skills when evidence supports a change.

## 7. UX Requirements

## 7.1 Information Architecture

Primary navigation should remain minimal:

- `Overview`
- `Decisions`
- `Control`

Supporting concepts such as positions, risk, and alerts may appear as sections inside these pages instead of top-level tabs in V1.

## 7.2 Overview Page

The first screen should prioritize the following order:

1. Today’s performance
2. AI decisions made today
3. Risk or mistakes
4. Current positions and exposure

### Required Overview Sections

#### A. Performance Strip

Show a mixed KPI set but only emphasize 3 to 4 numbers.

Expected examples:

- net PnL
- equity / NAV
- drawdown
- realized vs unrealized PnL

#### B. AI Current Intent Panel

This is the core trust surface.

It should use an **intent panel** structure, with:

- main sentence: goal first
- secondary sentence: current action second

Example pattern:

- Goal: preserve recent gains
- Action: reduce high-beta exposure and avoid new entries

#### C. Key Decisions Snapshot

Show a compact view of the most important recent AI decisions before the user goes into the full timeline.

## 7.3 Decisions Page

The main explanation surface is a **decision timeline**, not a strategy list or asset table.

### Timeline Rules

- primary structure: time-based
- default behavior: key events expanded, routine events collapsed
- event detail level: full

Each event should be able to expose:

- what happened
- why it happened
- risk basis
- execution result
- supporting signals or model evidence

## 7.4 Right-Side AI Workspace

The right-side AI pane should be a **mixed workspace**, not a pure chatbot.

It should combine:

- AI summary
- selected event audit/explanation
- suggested controls
- natural-language command input

This is the closest part of the UI to the Codex for Windows inspiration.

## 7.5 Visual Direction

The visual system should be:

- premium
- technology-forward
- dark-first
- calm and professional

It should borrow from Codex for Windows specifically in:

- context tracking
- calm premium desktop feel

It should avoid:

- generic dashboard card mosaics
- overly bright neon trading-terminal aesthetics
- chat-first layouts that bury critical numbers

## 7.6 Device Strategy

- desktop and mobile both matter
- desktop is the primary deep-review environment
- mobile keeps summary, AI state, key timeline moments, alerts, and emergency controls

## 8. Control and Execution Boundary Requirements

The user should retain high-level intervention, but manual execution is not the
focus. Controls should help research and simulation, not turn the system into a
live trading terminal.

### Allowed High-Level Controls

- pause / resume
- stop new entries
- tighten risk boundaries
- adjust high-level risk posture
- emergency stop

### Confirmation Rules

- low-risk actions may execute directly
- high-risk control changes must require confirmation

## 9. Notifications

Notification behavior should be:

- active by default
- customizable by the user

Current M5G implementation:

- creates local `notification_artifacts.jsonl` records during paper-only cycles
- shows newest local notifications in the read-only operator console overview
- covers new decisions, BUY/SELL blocked, `STOP_NEW_ENTRIES`, health blocking,
  repair request creation, and drawdown breach events
- stores only local artifact metadata and source links
- sends no external messages and stores no notification secrets

Future V1 should support:

- in-app notifications
- immediate push-like or Telegram-like notifications

## 10. Forecasting, Strategy Research, And Simulation Loop

## 10.1 Core Loop

The research engine should evolve toward this loop:

1. The system ingests useful market, macro, sentiment, fundamental, flow, or
   alternative data sources
2. AI generates a forecast
3. AI generates or revises a strategy hypothesis
4. The system runs backtests and simulations
5. The system waits for forecast horizons to complete when needed
6. The system validates prediction quality against realized data
7. The system compares strategy and forecast quality against baselines
8. The system records lessons and may propose skill updates
9. The system generates a simulated strategy decision
10. The system audits health and creates a Codex repair request if blocking failures exist
11. The next research cycle begins

## 10.2 V1 Boundary

V1 remains:

- no real capital
- no live execution
- no real order submission
- no required live broker or exchange adapter
- no secret-dependent research path

V1 can produce simulated strategy decisions such as:

- `BUY`
- `SELL`
- `HOLD`
- `REDUCE_RISK`
- `STOP_NEW_ENTRIES`

Directional actions must be blocked when evidence is weak, stale, unhealthy, or
not better than baseline.

Strategy research UX must expose the concrete current conclusion in human terms:
paper-shadow grade, after-cost edge, failure attribution, and next research
action should be readable first, with raw machine codes retained beside the
human labels for audit and rerun traceability.
The next research action in that conclusion should also be readable before the
machine action code, because it is the operator's immediate follow-up cue.
Outcome grades and core metric labels should follow the same rule: human label
first, raw grade code retained when the raw code is operationally meaningful.
Detailed paper-shadow attribution panels should reuse the same readable labels
as the headline conclusion so the UX does not switch back to raw-only codes.
Lineage views should follow the same rule for revision fixes, replacement
failures, performance verdicts, and trajectories.
Lineage action labels should also be readable first, with raw action codes kept
beside them for auditability.
Lineage next-research-focus copy should translate embedded failure attribution
tokens in the UI while preserving the raw artifact value for downstream
automation and CLI consumers.
Autopilot next-action panels should follow the same display rule: readable
action label first, raw action code retained beside it.
Lineage action-count aggregates should use the same display rule in dashboard
and operator-console UX: readable action label first, raw action code retained
beside it, while stored lineage artifacts keep machine keys unchanged.
Lineage failure-attribution aggregate counts should also render readable
failure labels first with raw failure codes retained beside them, while stored
lineage artifacts keep machine keys unchanged.
Paper-shadow detail and overview preview rows should render outcome grade and
recommended action with readable labels first and raw codes retained beside
them.

## 10.3 Data Scope

The project accepts any useful information source for research when it improves
prediction, backtesting, simulation, or strategy discovery. Public data is the
current implementation baseline, not the long-term product constraint.

Current practical V1 path:

- public crypto market data first
- BTC-USD as the initial automation symbol
- M3A registers `BTC-USD`, `ETH-USD`, `SPY`, `QQQ`, `TLT`, `GLD`, and `0050.TW`
- M3C adds deterministic stored hourly candle snapshots for replay
- M3D adds a US ETF/stock CSV fixture path for `SPY`, `QQQ`, `TLT`, and `GLD`
- M3E adds fixture-based macro event storage and calendar inspection
- M3F adds independent per-symbol strategy decisions for registered assets
- M4A adds leakage-checked research dataset artifacts built from scored forecasts
- M4B records expanded baseline suite results for research audit
- M4C adds a paper-only backtest engine over stored candles
- M4D adds rolling walk-forward validation artifacts with train/validation/test boundaries
- M4E adds generated Markdown research reports from existing research artifacts
- M4F adds research-quality gates before BUY/SELL decisions
- M5A adds a local-only read-only operator console skeleton
- M5B expands the operator console decision timeline with decision reasons,
  evidence links, invalidation conditions, and blocked reasons
- M5C expands the operator console portfolio/risk page with NAV, PnL,
  exposure, drawdown, positions, and risk gates
- M5D expands the operator console health/repair page with health status,
  blocking findings, repair request prompt paths, affected artifacts,
  recommended tests, and acceptance criteria
- M5E adds audited paper-only control events and a read-only control page for
  pause/resume, stop-new-entries, reduce-risk, emergency-stop, and max-position
  controls
- M5F adds automation run logs that link each paper cycle to step status,
  health-check id, strategy decision id, and repair request id
- M5G adds local notification artifacts for new decisions, blocked BUY/SELL
  gates, stop-new-entries, health blocking, repair requests, and drawdown
  breaches
- M6A defines Broker Adapter Contract V2 with internal paper, external paper,
  and sandbox mode names while keeping only internal paper implemented and all
  adapter submit/cancel paths blocked
- M6B adds safe example config files, secret-management documentation, `.env`
  ignore rules, and health-check detection for obvious secret leakage
- M6C adds a first mockable `BinanceTestnetBrokerAdapter` for sandbox/testnet
  experimentation with missing-key fail-safe behavior and no live endpoint
- M6D adds local broker order lifecycle artifacts that map paper orders to
  sandbox/external-paper statuses without calling a broker
- M6E adds local broker reconciliation artifacts that compare broker lifecycle,
  positions, cash, and equity against an external paper/sandbox snapshot and
  mark blocking mismatches as repair-required
- M6F adds paper/sandbox execution safety gates that require healthy storage,
  operator control allowance, tradeable decisions, evidence/risk gates, broker
  health, max order size, duplicate-order checks, reconciliation, and market
  open checks before any future sandbox submit may proceed
- M6G adds read-only dashboard broker/sandbox state: broker mode, broker
  health gate, account and positions snapshot, open orders, fills,
  reconciliation status, execution enabled/disabled, and mismatch warnings
- Taiwan provider and market calendar support remain deferred

## 10.4 Automation

Desired operating cadence:

- forecasting automation: hourly
- development fallback: every 10 minutes, only when forecasting breaks

Development-level failures should trigger fallback when they involve:

- broken data ingestion
- schema drift
- validation failures
- repeated runtime exceptions
- empty or invalid forecasts
- scoring or review regressions

## 11. MVP Scope

V1 MVP should include:

- one initial automation symbol, with per-symbol multi-asset decisions available when artifacts exist
- one strategy context
- at least one working data provider, with room to add non-public or paid
  research sources later
- immutable forecast artifacts
- score artifacts
- review artifacts
- proposal artifacts
- baseline evaluation artifacts
- strategy decision artifacts
- minimal paper portfolio snapshots
- local paper order ledger
- local paper fills and equity curve artifacts
- local paper risk snapshots and risk gates
- provider run audit artifacts
- stored market candle artifacts for deterministic replay
- US ETF/stock fixture import with adjusted close and market-calendar handling
- macro event artifacts for CPI, PCE, FOMC, GDP, NFP, and unemployment
- independent per-symbol decision generation through `decide-all`
- research dataset artifacts with no-lookahead leakage checks
- expanded baseline suite covering no-trade/cash, buy-and-hold, moving-average,
  momentum, and deterministic-random baselines
- simulated backtest run/result artifacts with return, benchmark, drawdown,
  Sharpe, turnover, and win-rate metrics
- walk-forward validation artifacts with rolling boundaries, aggregate metrics,
  and overfit-risk flags
- Markdown research reports covering data coverage, model vs baselines,
  backtests, walk-forward metrics, drawdown, overfit risk, and decision gates
- research-quality gates requiring enough samples, positive model edge,
  benchmark-beating backtests, acceptable drawdown, and stable walk-forward
  evidence before BUY/SELL
- local-only read-only operator console skeleton with overview, decisions,
  portfolio, research, health, and control-placeholder pages
- strategy-visible dashboard and operator console surfaces exposing the current
  strategy hypothesis, strategy rules, locked evidence gates, leaderboard
  state, paper-shadow attribution, and autopilot next research action
- read-only revision retest task planning that exposes next research tasks,
  missing inputs, linked artifacts, and runnable command arguments when safe
- dashboard and operator console visibility for the latest retest task plan
- audit-visible retest task run logs using existing automation run artifacts
- dashboard and operator console visibility for completed revision retest
  autopilot runs, including loop status, next action, blocked reasons,
  paper-shadow outcome, and steps
- dashboard and operator console visibility for strategy lineage, including
  multi-generation revision count, revision parent/depth tree rows, shadow
  action counts, failure attribution counts, best/worst excess return, and
  latest shadow outcome
- strategy lineage revision-change rows showing name, status, hypothesis,
  source outcome, and intended failure attributions
- regression coverage proving strategy revision natural-language fields are
  HTML-escaped in dashboard and operator console views
- strategy lineage performance trajectory showing after-cost excess, delta,
  improvement/worsening label, action, and failure attributions per shadow
  outcome
- strategy lineage performance verdict summarizing latest trend, counts,
  latest action, and latest failure focus before the raw trajectory rows
- strategy lineage next research focus translating the verdict into an
  inspectable next study direction
- read-only `strategy-lineage` CLI output exposing the latest lineage summary
  as JSON for non-HTML automation consumers
- `create-lineage-research-agenda` CLI output that persists the latest lineage
  focus as `strategy_lineage_research_agenda` without creating a decision or
  mutating a strategy card
- dashboard and operator console visibility for lineage-derived research
  agendas, including basis, priority, hypothesis, and acceptance criteria
- read-only `lineage-research-plan` CLI output that converts the latest lineage
  agenda into a concrete next task for a strategy research worker, including
  runnable revision commands when appropriate and explicit new-strategy
  research prompts when a lineage is quarantined
- dashboard and operator console visibility for the lineage research task plan,
  so the UX shows the next strategy work item, required artifact, command args,
  worker prompt, and rationale
- `record-lineage-research-task-run` audit logging that records the current
  lineage task plan as an `AutomationRun` without executing the task or mutating
  strategy artifacts
- dashboard and operator console visibility for the latest lineage task run
  log, including run status, run id, command, completed time, and step list
- `execute-lineage-research-next-task` support for the quarantined-lineage
  `draft_replacement_strategy_hypothesis` task, producing a DRAFT replacement
  strategy card with lineage/outcome links and an execution `AutomationRun`
- dashboard and operator console visibility for lineage replacement strategy
  hypotheses, so the UX exposes the concrete new strategy idea and its source
  failure context
- replacement strategy retest scaffold support, allowing DRAFT
  `lineage_replacement_strategy_hypothesis` cards to enter the existing locked
  retest plan without promotion or execution
- replacement strategy retest scaffold execution through
  `execute-revision-retest-next-task`, limited to creating the pending retest
  scaffold from an available research dataset and recording the research
  automation run
- dashboard and operator console visibility for replacement retest scaffold
  state, so the UX shows that a new replacement hypothesis has entered the
  retest chain and what task/run comes next
- replacement retest autopilot run recording, allowing a completed replacement
  chain to close the same research audit loop through the source lineage agenda
  without requiring a separate strategy decision artifact
- dashboard and operator console visibility for completed replacement retest
  autopilot runs, so the UX shows whether the replacement hypothesis completed
  the research audit loop and what research action comes next
- lineage verdict updates from replacement retest outcomes, so source lineages
  count root-linked replacement strategy paper-shadow outcomes in performance
  summaries
- replacement contribution visibility in lineage summaries and research UX,
  showing source outcome, latest replacement retest outcome, action, excess
  return, and replacement status
- replacement-aware lineage follow-up tasks, so improving replacement retests
  produce cross-sample validation prompts that name the exact replacement card,
  latest outcome, and excess return being tested
- lineage task-run logs that persist the next task worker prompt and rationale,
  so automation artifacts preserve the concrete research instruction after
  reload
- executable cross-sample lineage handoffs, so an improving lineage or improving
  replacement retest can create a `lineage_cross_sample_validation_agenda` that
  requires locked evaluation, walk-forward validation, and a fresh paper-shadow
  outcome before research confidence increases
- dashboard and operator console visibility for
  `lineage_cross_sample_validation_agenda`, so the next fresh-sample validation
  hypothesis, acceptance criteria, and required evidence artifacts are visible
  instead of hidden behind a task artifact id
- structured replacement-card links in `lineage_cross_sample_validation_agenda`
  artifacts, so research tooling can trace the exact improving replacement
  hypothesis as well as the source lineage root without parsing prompts
- dashboard and operator console visibility for those cross-sample agenda
  strategy-card links, so the research UX names the root and replacement
  strategy targets directly
- replacement retest autopilot agenda anchoring, so completed fresh-sample
  validation runs prefer a direct `lineage_cross_sample_validation_agenda`
  that names the replacement card instead of closing under an older lineage
  agenda
- dashboard and operator console visibility for linked cross-sample autopilot
  runs, so the agenda stays visible after task-plan completion and the UX shows
  the completed fresh-sample run, shadow outcome, and next research action
- lineage research task planning for linked cross-sample autopilot runs, so an
  agenda handoff is not treated as the end of validation until a completed
  fresh-sample research autopilot run is linked
- cross-sample UX validity filtering, so dashboard and operator console panels
  do not present blocked, missing-outcome, stale-outcome, or unrelated
  same-symbol autopilot runs as valid fresh-sample lineage evidence
- shared research-UX selectors, so dashboard and operator console apply the
  same cross-sample and retest evidence filters instead of carrying duplicated
  selector logic that can drift between surfaces
- actionable cross-sample task-plan blockers, so blocked fresh-sample validation
  tasks list the expected locked evaluation, walk-forward, paper-shadow outcome,
  and linked autopilot run inputs rather than only saying a run is missing
- concrete cross-sample worker prompts, so blocked fresh-sample validation tasks
  name the agenda id, strategy cards, latest lineage outcome, and expected
  evidence chain directly in the handoff
- blocked lineage task context in automation run logs, so research workers can
  read the blocked reason and missing evidence inputs from
  `record-lineage-research-task-run` output without reconstructing the plan
- human-readable blocked context labels in dashboard and operator console run
  logs, so lineage research blockers are visible in Traditional Chinese rather
  than raw automation step names
- readable blocked-reason copy for cross-sample run-log blockers, while keeping
  the original machine reason code visible for traceability
- readable missing-input copy for lineage run-log blockers, so required
  evidence artifacts are understandable to humans while raw machine codes stay
  visible
- shared automation step display copy for dashboard and operator console, so
  lineage blocker labels and values cannot drift between read-only UX surfaces
- explicit next required artifact entries in lineage task run logs, so
  downstream research workers can tell which artifact type to produce without
  reconstructing the task plan
- readable next required artifact copy in dashboard and operator console run
  logs, so those artifact targets are understandable in Traditional Chinese
  while raw machine codes stay visible
- readable required artifact copy in lineage task-plan panels, so the primary
  next-task view does not lag behind the audit run-log display
- readable missing-input copy in lineage task-plan panels, so blocked next
  research tasks explain evidence gaps without hiding raw machine codes
- readable required artifact and missing-input copy in revision retest
  task-plan panels, so strategy-revision research steps are as readable as
  lineage tasks
- readable revision retest scaffold next-required lists, so scaffold summaries
  and task plans describe required artifacts with the same copy
- readable revision retest run-step labels, so task run logs expose strategy
  card, source outcome, and evaluation-lock steps in human terms
- strategy research conclusion copy in dashboard and operator console, so the
  UX summarizes current strategy state, paper-shadow result, failure
  attribution, and next research action before raw evidence details
- readable lineage action-count aggregates in dashboard and operator console,
  so operators can scan quarantined/revised strategy action concentration
  without losing the raw action codes needed for auditability
- readable lineage failure-attribution aggregate counts in dashboard and
  operator console, so operators can scan repeated failure concentration before
  reading raw machine-code detail
- readable paper-shadow detail and overview status copy, so operators see
  outcome grade and recommended strategy action in human terms before raw codes
- decision timeline view exposing latest decision, reason summary, evidence
  grade, linked artifacts, invalidation conditions, and blocked reason
- portfolio/risk view exposing NAV, cash, realized/unrealized PnL,
  positions, drawdown, exposure, risk gate thresholds, and risk findings
- health/repair queue view exposing current health, blocking findings, repair
  request status, repair prompts, affected artifacts, recommended tests, and
  acceptance criteria
- audited simulated-control event artifacts with confirmation requirements for
  risky controls and paper-order blocking gates for emergency stop, pause, stop
  new entries, reduce risk, and max position
- automation run log artifacts that record cycle steps, health checks,
  decisions, repair requests, and final run status
- controller governance docs and prompt templates for controller decisions,
  worker handoffs, final reviewer subagent requests, Windows execution gates,
  and runtime/secret exclusion
- health-check output
- Codex repair request artifacts
- minimal CLI
- hourly research automation
- fallback automation for repair mode

## 12. Success Criteria

V1 should be considered product-ready for internal iteration only when:

- forecasts are generated on schedule
- concrete strategy hypotheses and backtest results are visible
- forecast windows are correctly aligned to provider data boundaries
- scoring only happens after complete data coverage
- reviews, proposals, and strategy decisions are based on trustworthy evidence
- strategy decisions show action, confidence, risk, invalidation conditions, and linked artifacts
- weak evidence does not produce fake BUY/SELL certainty
- the system can revise or propose reusable strategy skills from prior evidence
- the system can turn lineage evidence into a concrete next research task rather
  than only displaying status
- blocking storage, ingestion, or provider problems create repair requests
- the system can fail safely and fall back to development mode
- the UI can present strategy logic, prediction rationale, backtests, revisions,
  and decision history coherently

## 13. Known Gaps Before Full V1 Confidence

The current implementation has closed the earlier correctness gaps around
provider-aligned forecast anchors, complete target-window coverage before
scoring, incomplete realized windows, replay determinism, and dashboard
operator-state framing.

Remaining gaps are now research capability and operations scope, not known loop-blocking
correctness defects:

- strategy and regime classification remain too simple for the user's current
  research goals
- the current read-only UX now exposes concrete strategy context, but visual
  depth, comparison charts, and richer strategy revision history remain basic
- automation run logs are audit artifacts only; scheduler orchestration remains
  outside the repo
- automation is local and simulation-first, with manual evidence checks before
  any resume
- paper portfolio accounting and risk gates are local simulations
- SQLite repository migration/export now exists, while the hourly loop and dashboard still use JSONL artifacts by default until later M2 integration
- health-check creates repair requests and the operator console can inspect
  them, but there is no autonomous repair daemon in this repo
- there is no live execution layer, which is acceptable because the user wants
  research and simulation rather than real orders
- CoinGecko moving-window replay remains disabled; replay can now use imported stored candles
- ETF/stock support is fixture-only and US-calendar-only; broader data sources
  should be added when they improve prediction
- Taiwan ETF calendar/provider support remains deferred
- macro events are visible as imported calendar artifacts, but do not yet drive research features or strategy decisions
- per-symbol multi-asset decisions do not yet perform portfolio optimization or cross-asset allocation
- research datasets are generated artifacts only; PR12 adds a first
  paper-shadow-to-DRAFT-revision primitive, PR13 makes it visible, PR14/PR15 add
  visible retest scaffolds, PR16 adds read-only retest task planning, PR17
  exposes the task plan in UX, and PR18 records task-plan inspections as run
  logs, PR19 exposes those run logs in UX, PR20 executes only the first
  whitelisted retest protocol-locking task, PR21 adds baseline execution, PR22
  adds holdout backtest execution from locked split windows, PR23 adds
  walk-forward execution from the locked full split window, PR24 adds passed
  retest trial recording from existing evidence, and PR25 adds leaderboard-gate
  execution from plan-linked PASSED retest evidence, and PR26 adds explicit
  shadow-outcome execution when real observation inputs are supplied, and PR27
  keeps completed chains visible as completed revision evidence, and PR28
  records revision retest autopilot runs without fake decision artifacts. PR29
  adds one-command recording for completed revision retest autopilot runs, and
  PR30 makes those completed revision retest autopilot runs visible in the
  dashboard and operator console. PR31 adds strategy lineage summaries for
  parent/revision shadow evidence, PR32 makes those summaries recursive across
  multi-generation revision trees, PR33 exposes revision parent/depth rows in
  the UX, PR34 hardens branching/missing-parent/cycle edge cases, and PR35
  exposes revision hypothesis/source/fix summaries, and PR36 adds malicious HTML
  escaping regressions for those fields. PR37 exposes lineage performance
  trajectory, PR38 adds the human-readable lineage verdict, and PR39 adds the
  next research focus, and PR40 exposes the same summary through a read-only
  CLI. PR41 can persist that focus as a research agenda artifact, and PR42
  makes that lineage-derived agenda visible in the strategy UX, but
  strong strategy generation, model training, deeper self-evolving skill loops,
  and optimizers are not included yet
- backtests are local simulations over stored candles; no broker or live execution path is involved
- walk-forward validation now influences simulated BUY/SELL gates through
  M4F research-quality checks
- research reports summarize available artifacts only; strategy behavior changes
  come from M4F research-quality gates

The repository is suitable for continued hourly research only when
tests pass, active storage repair status is fresh, dashboard freshness is
visible, strategy decision/health status and strategy research context are visible, and
`last_run_meta.json.new_forecast.forecast_id` matches the newest forecast tail
for the same symbol when that metadata file belongs to the symbol being
audited.

## 14. Decision Log: Prior Q&A

This section records the earlier product questions and the answers that shaped the PRD.

### Product and UX Decisions

- First thing the main screen must do well: `Show overall PnL / profitability`
- Main usage style: `AI CONTROL`
- AI authority model: `AI is almost fully automatic; user mainly reviews reports, receives alerts, and intervenes when necessary`
- Typical visit cadence: `Fixed daily/weekly review, not constant monitoring`
- What users want to confirm on open: `All of performance, decisions, risk, and positions`
- Priority order on the first screen: `Performance > Decisions > Risk/Mistakes > Positions`
- Most common next action after summary: `Inspect why the AI made decisions`
- Explanation layer style: `Decision tracking panel`
- Primary explanation structure: `Timeline`
- Event detail depth: `Full detail`
- Visual style: `Premium technology look`
- Device strategy: `Desktop and mobile both matter; desktop for deep review`
- Scope: `Single account, single strategy`
- Manual intervention: `High-level controls only; manual trading is not the focus`
- Notifications: `Active + user-customizable`
- Market scope: `Multi-asset`
- Performance display: `Mixed KPI set with only 3 to 4 numbers emphasized`
- Interaction model: `Hybrid console + AI interaction`
- Codex inspiration: `Context tracking + calm premium desktop feel`
- Right-side AI pane: `Mixed summary + audit + control workspace`
- Trust priority: `The AI’s current activity must be clear at a glance`
- Current state panel style: `Intent/mission panel`
- Main AI state wording: `Goal first, then action`
- Navigation depth: `Overview / Decisions / Control`
- Mobile scope: `Summary, state, key timeline, and alerts; deep control stays on desktop`
- Control confirmations: `High-risk actions require confirmation`
- Timeline expansion logic: `Important events expanded, normal events collapsed`
- V1 notification channel recommendation accepted: `In-app + push/Telegram-like immediate notifications`
- Theme strategy recommendation accepted: `Dark-first`

### System and Automation Decisions

- No real-money trading in V1
- Public data first
- Paper-only forecasting and research loop
- Desired loop: `Predict -> Wait -> Validate -> Review -> Adjust -> Predict`
- Hourly prediction automation is the preferred runtime cadence
- Development automation should only exist as a fallback repair mode
