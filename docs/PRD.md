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

- PR0 Reviewability And Formatting Gate comes before more strategy code.
- M7A is only the evidence artifact foundation.
- M7B-M7F must implement the Alpha Evidence Engine: source registry, source
  document import, event reliability, market reaction / already-priced checks,
  historical edge, and decision integration.
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
- the current read-only UX includes static HTML plus a local operator console;
  it does not yet make concrete strategy logic prominent enough
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
- research datasets are generated artifacts only; no strong strategy generation,
  model training, self-evolving skill loop, or optimizer is included yet
- backtests are local simulations over stored candles; no broker or live execution path is involved
- walk-forward validation now influences simulated BUY/SELL gates through
  M4F research-quality checks
- research reports summarize available artifacts only; strategy behavior changes
  come from M4F research-quality gates

The repository is suitable for continued hourly research only when
tests pass, active storage repair status is fresh, dashboard freshness is
visible, strategy decision/health status are visible, and
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
