# Paper Forecast Loop

Backtesting, prediction, and strategy-simulation research loop.

This repository is intentionally narrow. The M1 goal is not feature breadth. The
current foundation is the first **auditable strategy research robot**:

- create a forecast on a reproducible hourly boundary
- wait for the target window to complete
- only score when provider coverage is complete
- generate review and proposal artifacts with provenance
- compare prediction quality against baselines
- produce a simulated strategy decision for the next horizon
- create Codex repair requests when health checks find blocking issues
- keep reruns safe and idempotent

## Updated Priority

The project direction is research-first, not safety-first and not
productization-first.

The highest-value outcomes are:

- stronger prediction quality;
- stronger strategy research;
- broader backtesting and simulation;
- self-improving strategy skills;
- concrete strategy visibility in the UX;
- more data sources and research tools when they improve analysis.

The current execution boundary is simple: do not place real orders and do not
move real capital. This is the present research/simulation boundary, not a
permanent product promise; future automated trading would require an explicit
new user request and a separate design stage. Everything else is allowed when it
is used for research, backtesting, prediction, simulation, or strategy
reflection.

Natural-language strategy generation is acceptable. Tool-rich automated loops
are acceptable. Self-evolving skills are desirable. Sandbox or broker gates
should not block research, prediction, backtesting, or simulation work; they
only exist to prevent accidental real execution.

Some existing artifact names still use `paper` for compatibility. In the current
direction, read those as simulation/research artifacts, not as a limit on data
sources or research methods.

## Research Background

The current master execution decision after M7A is recorded in
[`docs/architecture/autonomous-alpha-factory-master-decision.md`](docs/architecture/autonomous-alpha-factory-master-decision.md).
That document is the repo's working contract for the next phase. PR0 and
M7B-M7F establish the reviewability and Alpha Evidence Engine spine. PR6 adds
the first Strategy Card and Experiment Registry layer so failed, aborted, and
invalid research trials are retained instead of hidden.

The post-M1-M6 research direction is documented in
[`docs/architecture/alpha-factory-research-background.md`](docs/architecture/alpha-factory-research-background.md).
The target is a research-capable, prediction-focused, multi-strategy Alpha
Factory. In its current scope, it is not a live auto-trading system.

The core research rule is: **放開策略搜尋空間，鎖死評估流程。** Strategy
ideas may broaden, but candidate evaluation must stay fixed, auditable, and
repeatable through canonical data snapshots, locked split manifests, trial
budgets, baseline comparison, research gates, holdout checks, paper-shadow
monitoring, and repair/health artifacts.

Operationally, the current system should be read as the foundation of that
factory:

- M1-M6 provide the paper-only decision, health, research, portfolio, UI, and
  sandbox-safety spine.
- M7A is an artifact foundation, not a completed intelligence engine.
- M7B adds the fixture-only source registry and source document import layer.
- M7C converts imported source documents into canonical events and event
  reliability checks.
- M7D adds market reaction / already-priced checks over canonical event
  snapshots and stored candles.
- M7E adds event-family historical edge evaluation over passed market reaction
  samples.
- M7F integrates event-edge evidence into the research gate, so BUY/SELL remains
  blocked unless the latest event edge evaluation also passes.
- PR6 adds versioned strategy cards, experiment budget snapshots, and an
  append-only experiment trial registry.
- PR7 adds locked split manifests, cost model snapshots, locked evaluation
  results, and leaderboard hard gates so `alpha_score` is impossible until
  mandatory evidence gates pass.
- PR8 adds paper-shadow outcome artifacts so leaderboard candidates can be
  marked promotion-ready, revised, retired, or quarantined after simulated
  shadow results.
- PR9 adds research agenda and autopilot run artifacts so the chain from
  agenda to strategy, evaluation, decision, shadow outcome, and next research
  action is visible as one loop record.
- PR10 makes strategy research visible in the read-only UX: the dashboard and
  operator console now surface the current strategy hypothesis, rules, locked
  evidence gates, leaderboard state, paper-shadow attribution, and next
  autopilot research action before raw metadata.
- PR11 adds Codex governance docs and prompts: controller decisions, worker
  handoffs, final reviewer prompts, Windows autopilot runbook, and docs tests
  for required gates and role catalog alignment.
- PR12 adds the first self-evolving strategy primitive: failed paper-shadow
  outcomes can produce DRAFT child strategy-card revision candidates plus a
  linked retest agenda.
- PR13 makes those DRAFT revision candidates visible in the dashboard and
  operator console so strategy self-correction is inspectable without reading
  JSONL.
- PR14 adds a retest scaffold for DRAFT revision candidates: it creates an
  idempotent `PENDING` experiment trial and can lock split/cost protocol
  artifacts without fabricating evaluation results.
- PR15 makes those retest scaffolds visible in the dashboard and operator
  console, including pending trial, dataset, locked split, and remaining
  required evidence artifacts.
- PR16 adds a read-only revision retest task planner: it turns the latest DRAFT
  revision and retest scaffold into ordered research tasks, missing inputs, and
  runnable command arguments when prerequisites exist.
- PR17 surfaces that retest task plan in the dashboard and operator console so
  the UX shows the next concrete research task, status, missing inputs, blocked
  reason, and command args.
- PR18 records the current retest task plan as a research `AutomationRun`, so
  the system can audit when a retest task was inspected and whether it was
  ready or blocked without executing it.
- PR19 surfaces those retest task run logs in the dashboard and operator
  console beside the task plan, so the UX shows both the next task and the
  latest audit evidence for inspecting it.
- PR20 adds the first narrow retest executor: it can execute the ready
  `lock_evaluation_protocol` task directly through domain code, write a cost
  model, record an execution `AutomationRun`, and return before/after plans.
- PR21 extends the same executor to `generate_baseline_evaluation`, allowing
  the retest chain to advance from protocol locking to baseline evidence.
- PR22 extends the same executor to `run_backtest`, allowing the retest chain
  to produce holdout backtest evidence from the locked split window while still
  rejecting walk-forward and later tasks.
- PR23 extends the same executor to `run_walk_forward`, allowing the retest
  chain to produce rolling validation evidence from the locked full split window
  while still rejecting passed-trial recording and later tasks.
- PR24 extends the same executor to `record_passed_retest_trial`, allowing the
  retest chain to link baseline, holdout backtest, and walk-forward evidence
  into a PASSED trial while still rejecting leaderboard evaluation and later
  tasks.
- PR25 extends the same executor to `evaluate_leaderboard_gate`, allowing the
  retest chain to write locked evaluation and leaderboard-entry evidence from a
  PASSED trial while still rejecting paper-shadow outcome recording and later
  tasks.
- PR26 extends the same executor to `record_paper_shadow_outcome` only when
  explicit shadow-window observation inputs are supplied, allowing the retest
  chain to close without fabricating future returns.
- PR27 makes completed revision retest chains visible to the strategy research
  resolver and read-only UX surfaces, so a PASSED retest with locked evaluation,
  leaderboard entry, and shadow outcome no longer appears as missing work.
- PR28 lets completed DRAFT revision retests be recorded as research autopilot
  runs without inventing an unrelated strategy decision artifact; weak evidence
  still blocks on the real evaluation / leaderboard reasons.
- PR29 adds a direct `record-revision-retest-autopilot-run` command that
  resolves the completed revision retest plan and records the research autopilot
  loop without manually copying every evidence ID.
- PR30 makes those completed revision retest autopilot runs visible in the
  dashboard and operator console, so a closed self-evolution loop is visible
  from the strategy UX rather than only from `research_autopilot_runs.jsonl`.
- PR31 adds strategy lineage visibility: the read-only UX now summarizes a
  parent strategy, DRAFT revisions, paper-shadow action counts, failure
  attribution concentration, best/worst after-cost excess return, and latest
  shadow outcome.
- PR32 makes that strategy lineage recursive: multi-generation revisions and
  their shadow outcomes now stay attached to the original root strategy, so the
  UX can show deeper self-evolution history instead of only direct children.
- PR33 adds revision-tree visibility: the same lineage summary now exposes each
  revision's parent and depth, so branching or nested self-evolution does not
  collapse into an ambiguous flat list.
- PR34 hardens lineage edge cases with committed regressions for branching
  revision trees, missing parents, and parent cycles.
- PR35 adds revision change summaries to lineage nodes: the UX now shows each
  revision's strategy name, status, hypothesis, source outcome, and intended
  failure attributions to repair.
- PR36 adds malicious-HTML regression coverage for revision change summaries so
  natural-language strategy fields remain escaped in dashboard and operator
  console views.
- PR37 adds strategy lineage performance trajectory: the UX now shows each
  lineage paper-shadow outcome's after-cost excess return, delta versus the
  previous outcome, improvement/worsening label, action, and failure
  attribution.
- PR38 adds a strategy lineage performance verdict: the UX now summarizes
  whether the latest revision path is improving, worsening, stalled, or missing
  evidence before showing the raw trajectory rows.
- PR39 adds a strategy lineage next research focus: the UX now turns the
  verdict into a concrete next study direction, such as repairing drawdown
  breach or starting a new strategy hypothesis.
- PR40 adds a read-only `strategy-lineage` CLI so automation and research
  loops can consume the latest lineage summary JSON, including performance
  verdict and next research focus, without scraping dashboard HTML.
- PR41 adds `create-lineage-research-agenda`, which turns the latest lineage
  next research focus into an idempotent research agenda artifact for the next
  self-evolution loop.
- PR42 makes lineage-derived research agendas first-class in the strategy UX:
  dashboard and operator console now show the agenda basis, priority,
  hypothesis, and acceptance criteria next to the lineage summary.
- PR43 adds a read-only `lineage-research-plan` CLI that turns the latest
  lineage agenda into an executable next-task plan: revise, quarantine into a
  replacement hypothesis, collect missing shadow evidence, or verify
  cross-sample persistence.
- PR44 makes that lineage next-task plan visible in dashboard and operator
  console strategy research pages, including task id, required artifact,
  command args when available, worker prompt, and rationale.
- PR45 adds `record-lineage-research-task-run`, which records the current
  lineage task plan as an `AutomationRun` audit artifact without executing the
  task or mutating strategy artifacts.
- PR46 surfaces the latest lineage task run log in dashboard and operator
  console strategy research pages, so the UX shows whether the next strategy
  work item was inspected by the research loop.
- PR47 adds `execute-lineage-research-next-task` for the quarantined-lineage
  replacement path. It turns `draft_replacement_strategy_hypothesis` into a
  new DRAFT replacement strategy card and records the execution as an
  `AutomationRun`.
- PR48 makes replacement strategy hypotheses visible in dashboard and operator
  console research pages, including source lineage, source outcome, failure
  attributions, hypothesis, signal, rules, and parameters.
- PR49 lets a lineage replacement strategy enter the existing retest scaffold:
  `create-revision-retest-scaffold` and `revision-retest-plan` now accept
  `lineage_replacement_strategy_hypothesis` DRAFT cards while preserving the
  locked backtest / walk-forward / paper-shadow research chain.
- PR50 lets `execute-revision-retest-next-task` execute the first scaffold step
  for those replacement cards when a research dataset is already available,
  keeping the same retest chain instead of adding a parallel replacement-only
  runner.
- PR51 makes that replacement retest scaffold visible in dashboard and operator
  console, including pending trial id, dataset id, scaffold status, retest kind,
  next task, and latest executor run.
- PR52 lets completed replacement retest chains record a
  `record-revision-retest-autopilot-run` artifact by using the source lineage
  research agenda, so replacement strategies can complete the same research
  audit loop without requiring a separate paper decision artifact.
- PR53 surfaces that completed replacement retest autopilot run in dashboard and
  operator console, showing loop status, run id, next research action,
  paper-shadow outcome, blockers, and steps beside the replacement strategy.
- PR54 folds root-linked replacement strategy paper-shadow outcomes into the
  source strategy lineage summary, so replacement retest results can update the
  lineage verdict instead of staying invisible to lineage performance counts.
- PR55 exposes replacement contribution nodes in the lineage summary, dashboard,
  operator console, and CLI JSON, so replacement hypotheses show their source
  outcome, latest retest outcome, action, excess return, and status.
- PR56 carries that replacement context into the next lineage research task
  prompt when a replacement retest improves the lineage, so follow-up
  cross-sample validation targets the exact replacement hypothesis and outcome.
- PR57 persists the next lineage task prompt and rationale in automation run
  steps, so replacement-aware research instructions survive JSONL reload and
  are visible to dashboard/operator-console inspection.
- PR58 makes the improving-lineage cross-sample task executable: the executor
  now creates a `lineage_cross_sample_validation_agenda` handoff artifact that
  names the latest lineage outcome and requires locked evaluation,
  walk-forward validation, and a fresh paper-shadow outcome before confidence
  can increase.
- PR59 surfaces that cross-sample validation agenda in the dashboard and local
  operator console, so the strategy UX shows the concrete hypothesis,
  acceptance criteria, and required evidence artifacts for the next fresh-sample
  validation pass.
- PR60 links improving replacement cards structurally into cross-sample
  validation agendas, so downstream research tools can trace both the lineage
  root and the exact replacement hypothesis without parsing natural-language
  prompts.
- PR61 shows those cross-sample agenda strategy-card links in dashboard and
  operator console, making the root/replacement strategy targets inspectable
  from the research UX without opening raw JSON.
- PR62 makes completed replacement retest autopilot runs prefer the direct
  `lineage_cross_sample_validation_agenda` when that agenda names the
  replacement card, so fresh-sample validation evidence closes under the
  handoff agenda instead of falling back to the older lineage agenda.
- PR63 shows the linked cross-sample autopilot run in dashboard and operator
  console panels, so the UX keeps the validation agenda visible after the task
  plan advances and exposes the completed fresh-sample run, outcome, and next
  research action.
- PR64 extends the lineage research task plan so cross-sample validation does
  not stop at agenda creation: once the agenda exists, the plan requires a
  linked `research_autopilot_run` before the fresh-sample validation task chain
  is treated as fully complete.
- PR65 hardens cross-sample UX evidence selection: dashboard and operator
  console now show linked fresh-sample runs only when the run is unblocked,
  points to an existing paper-shadow outcome, matches the current lineage
  latest outcome, and belongs to the current root/revision/replacement lineage.
- PR66 extracts the shared research-UX selector rules used by dashboard and
  operator console, so cross-sample and retest evidence filtering stays
  consistent across both read-only surfaces.
- PR67 makes blocked cross-sample task plans more actionable by carrying the
  agenda's expected evidence artifacts in `missing_inputs` before the linked
  autopilot run is accepted.
- PR68 makes the blocked cross-sample worker handoff concrete by naming the
  agenda id, strategy cards, latest lineage outcome, and expected fresh-sample
  evidence directly in the task prompt.
- PR69 persists blocked lineage next-task context in automation run logs, so
  `record-lineage-research-task-run` carries the blocked reason and missing
  evidence inputs without requiring the next worker to rebuild the task plan.
- PR70 translates those blocked run-log fields in dashboard and operator
  console views, so the UX shows human-readable Traditional Chinese labels
  instead of raw `next_task_*` step names.
- PR71 adds readable blocked-reason copy for cross-sample run-log blockers while
  preserving the raw reason code for traceability.
- PR72 adds readable missing-input copy for lineage run-log blockers, translating
  core evidence codes such as locked evaluation and walk-forward validation
  while keeping the raw code list visible.
- PR73 centralizes automation step display copy so dashboard and operator
  console render lineage blocker labels and values from the same helper.
- Later M7+ should improve strategy generation, data-source breadth, canonical
  market data, validation depth, leaderboard governance, deeper autopilot
  learning, and self-evolving research skills.
- Vibe-Trading is a useful reference for skills, swarm workflows, MCP tools,
  agent memory, backtest breadth, data loaders, and UX surfaces.
- CoinGecko remains useful for prototype and cross-check work, but serious
  intraday crypto research needs canonical provider comparison before promotion.
- BUY/SELL should remain blocked when evidence is weak, when the model does not
  beat baselines, when research gates fail, or when health/risk gates are not
  clean.
- No research result in this repository should be treated as a real-money order.

## Current Scope

This version intentionally includes:

- active paper research automation remains `BTC-USD` first
- registered M3A asset universe:
  - `BTC-USD`
  - `ETH-USD`
  - `SPY`
  - `QQQ`
  - `TLT`
  - `GLD`
  - `0050.TW`
- hourly public market data
- providers:
  - sample provider
  - CoinGecko provider
  - US ETF/stock CSV fixture provider for `SPY`, `QQQ`, `TLT`, and `GLD`
- storage:
  - SQLite repository for M2 canonical state migration
  - JSONL artifacts for audit export and backward compatibility:
    - `market_candles.jsonl`
    - `macro_events.jsonl`
    - `source_registry.jsonl`
    - `source_documents.jsonl`
    - `source_ingestion_runs.jsonl`
    - `canonical_events.jsonl`
    - `event_reliability_checks.jsonl`
    - `market_reaction_checks.jsonl`
    - `event_edge_evaluations.jsonl`
    - `feature_snapshots.jsonl`
    - `forecasts.jsonl`
    - `scores.jsonl`
    - `reviews.jsonl`
    - `proposals.jsonl`
    - `baseline_evaluations.jsonl`
    - `portfolio_snapshots.jsonl`
    - `strategy_decisions.jsonl`
    - `paper_orders.jsonl`
    - `paper_fills.jsonl`
    - `control_events.jsonl`
    - `equity_curve.jsonl`
    - `risk_snapshots.jsonl`
    - `provider_runs.jsonl`
    - `automation_runs.jsonl`
    - `repair_requests.jsonl`
    - `research_datasets.jsonl`
    - `backtest_runs.jsonl`
    - `backtest_results.jsonl`
    - `walk_forward_validations.jsonl`
    - `strategy_cards.jsonl`
    - `experiment_budgets.jsonl`
    - `experiment_trials.jsonl`
    - `split_manifests.jsonl`
    - `cost_model_snapshots.jsonl`
    - `locked_evaluation_results.jsonl`
    - `leaderboard_entries.jsonl`
    - `paper_shadow_outcomes.jsonl`
    - `research_agendas.jsonl`
    - `research_autopilot_runs.jsonl`
- CLI execution via:
  - `run-once`
  - `replay-range`
  - `render-dashboard`
  - `operator-console`
  - `strategy-lineage`
  - `create-lineage-research-agenda`
  - `lineage-research-plan`
  - `record-lineage-research-task-run`
  - `execute-lineage-research-next-task`
  - `operator-control`
  - `repair-storage`
  - `decide`
  - `decide-all`
  - `health-check`
  - `init-db`
  - `migrate-jsonl-to-sqlite`
  - `export-jsonl`
  - `db-health`
  - `paper-order`
  - `paper-fill`
  - `portfolio-snapshot`
  - `risk-check`
  - `list-assets`
  - `import-candles`
  - `export-candles`
  - `candle-health`
  - `import-stock-csv`
  - `stock-candle-health`
  - `market-calendar`
  - `import-macro-events`
  - `macro-calendar`
  - `import-source-documents`
  - `source-registry`
  - `build-events`
  - `build-market-reactions`
  - `build-event-edge`
  - `build-research-dataset`
  - `research-report`
  - `backtest`
  - `walk-forward`
  - `register-strategy-card`
  - `record-experiment-trial`
  - `lock-evaluation-protocol`
  - `evaluate-leaderboard-gate`
  - `record-paper-shadow-outcome`
  - `create-research-agenda`
  - `record-research-autopilot-run`
  - `propose-strategy-revision`
  - `create-revision-retest-scaffold`
  - `revision-retest-plan`
  - `record-revision-retest-task-run`
  - `record-revision-retest-autopilot-run`
  - `execute-revision-retest-next-task`

This version intentionally excludes:

- browser UI forms; the local operator console remains read-only
- live trading
- real capital
- portfolio optimizer or cross-asset allocation engine
- live broker / exchange adapters
- real orders
- broker reconciliation and external execution
- notifications / Telegram
- full scheduler or autonomous repair daemon orchestration

## Development Environment And Agent Rules

Portable development rules are versioned in this repo:

- `AGENTS.md`: Codex collaboration rules, review rules, routing rules, and role catalog
- `docs/roles/`: role definitions for controller, fixer, verifier, reviewer, UI, data, replay, infra, and related work
- `docs/development-environment.md`: Windows/Codex setup, verification commands, ignored local runtime state, and automation boundaries
- `docs/reviews/`: archived review findings and final reviewer outcomes

Machine-local runtime state is intentionally not committed. This includes
`.codex/`, `paper_storage/`, screenshots, caches, and generated sample runs.

## M1 Strategy Decision Contract

The new decision artifact answers the operator question:

> What should the paper strategy do for the next 24 hours?

Allowed actions:

- `BUY`
- `SELL`
- `HOLD`
- `REDUCE_RISK`
- `STOP_NEW_ENTRIES`

Each `strategy_decisions.jsonl` row records:

- action, symbol, horizon, timestamp
- confidence, evidence grade, risk level
- current and recommended paper position percentage
- tradeable/blocking status
- invalidation conditions
- human-readable reason summary
- linked forecast, score, review, and baseline ids

BUY/SELL requires enough evidence and a positive edge over baseline. Weak,
missing, stale, or unhealthy evidence must produce HOLD, REDUCE_RISK, or
STOP_NEW_ENTRIES instead of fake directional certainty.

## Baseline And Evidence Gates

The decision gate still compares model quality against the naive persistence
baseline for backward-compatible M1 behavior:

- naive persistence baseline: next actual regime equals the previous actual regime
- model directional accuracy: average realized forecast score
- model edge: model accuracy minus baseline accuracy
- recent score: recent rolling model score
- evidence grade: `A`, `B`, `C`, `D`, or `INSUFFICIENT`

M4B also records an expanded baseline suite inside `baseline_evaluations.jsonl`
for research audit:

- no-trade / cash
- buy-and-hold
- moving-average trend
- momentum 7d
- momentum 14d
- deterministic random

Decision gates:

- sample size below 2 -> `INSUFFICIENT`
- no positive edge over baseline -> BUY/SELL blocked
- poor recent score -> `REDUCE_RISK`
- missing/stale forecast or blocking health finding -> `STOP_NEW_ENTRIES`

## Paper Broker Boundary

The broker layer exists only to keep future integration boundaries clean.

M6A defines the broker adapter contract with these methods:

- `get_account_snapshot`
- `get_positions`
- `submit_order`
- `cancel_order`
- `get_order_status`
- `get_fills`
- `health_check`

Supported contract modes are:

- `INTERNAL_PAPER`
- `EXTERNAL_PAPER`
- `SANDBOX`

`INTERNAL_PAPER` is always available. M6C adds a first `SANDBOX` implementation:
`binance_testnet`.

`binance_testnet` is testnet-only:

- requires explicit API key and API secret values from the caller
- refuses non-testnet endpoints
- uses `/api/v3/order/test` for mocked submit tests
- has no cancellation lifecycle or fills yet
- defaults to a blocking HTTP client unless a caller injects a mock/client
- never enables live trading

M6D adds local broker order lifecycle artifacts in `broker_orders.jsonl`.
These records connect local `paper_orders.jsonl` orders to a broker/sandbox
lifecycle status:

- `CREATED`
- `SUBMITTED`
- `ACKNOWLEDGED`
- `PARTIALLY_FILLED`
- `FILLED`
- `CANCELLED`
- `REJECTED`
- `EXPIRED`
- `ERROR`

The `broker-order` CLI writes local lifecycle records from existing paper
orders. It accepts only `EXTERNAL_PAPER` or `SANDBOX` broker modes, uses mock
submit status metadata only, and does not call an external broker.

M6E adds local broker reconciliation artifacts in
`broker_reconciliations.jsonl`. The `broker-reconcile` CLI compares local
broker lifecycle rows and the latest local portfolio snapshot against an
external paper/sandbox snapshot fixture. Unknown external orders, missing
tracked local orders, duplicate broker order references, status mismatches, or
cash/equity/position mismatches are blocking and set `repair_required=true`.

M6F adds paper/sandbox execution safety gates in
`execution_safety_gates.jsonl`. The `execution-gate` CLI checks health,
operator controls, decision tradeability, evidence grade, risk state, broker
health fixture, order sizing, duplicate active orders, latest reconciliation,
and market-open constraints before a future sandbox submit path may proceed.
It performs no submit/cancel operation.

M6G renders broker/sandbox state in the read-only dashboard: broker mode,
broker health gate, account/position snapshot, open order counts, latest fills,
reconciliation status, execution enabled/disabled, and mismatch warnings.

Live broker or exchange modes are intentionally unavailable. There is no API key
handling in source and no real live order path. M2B/M2C add local paper order
and fill artifacts; M6C adds only a gated sandbox/testnet adapter surface for
later milestones.

## Secret and Config Safety

M6B adds safe configuration examples only:

- `.env.example`
- `config/brokers.example.yml`
- `docs/secrets-management.md`

`.env` and `.env.*` are ignored, except `.env.example`. Example files contain
blank placeholders and environment variable names only.

`health-check` scans repo safety files and selected storage artifacts for
obvious secret-looking assignments such as API keys, API secrets, tokens,
webhook URLs, and private keys. If found, it reports
`secret_leak_detected` without echoing the secret value.

This does not add external broker connectivity, notification delivery,
sandbox/testnet submission, or live trading.

## Forecast Contract

Each forecast records enough information to reconstruct and audit the forecast window:

- `anchor_time`: the latest provider-aligned hourly boundary available at run time
- `target_window_start`: the forecast window start boundary
- `target_window_end`: the forecast window end boundary
- `candle_interval_minutes`: the expected candle interval
- `expected_candle_count`: the number of hourly boundaries required for a complete score
- `status`: lifecycle state
- `status_reason`: why the forecast is in that state
- `provider_data_through`: latest provider boundary observed during evaluation
- `observed_candle_count`: how many aligned candles were actually observed for the target window

### Boundary Rule

Forecast creation does **not** use arbitrary wall-clock timestamps. It aligns to the latest provider hourly boundary that is actually available.

Example:

- run time: `2026-04-21T12:37:00Z`
- latest available hourly candle boundary: `2026-04-21T11:00:00Z`
- forecast anchor and target window start: `2026-04-21T11:00:00Z`

## Resolve and Scoring Contract

A forecast may only be scored when **all** of the following are true:

1. `now >= target_window_end`
2. provider data coverage reaches at least `target_window_end`
3. the target window contains the full expected set of hourly boundaries
4. the realized candle set is non-empty and sufficient to classify

If any of those conditions fail, the loop must not score the forecast.

## Forecast States

- `pending`
  - meaning: the target window has not finished yet
  - reason: `awaiting_horizon_end`

- `waiting_for_data`
  - meaning: the target window has finished, but provider coverage has not yet reached the target window end
  - reason: `awaiting_provider_coverage`

- `resolved`
  - meaning: a valid score has been recorded for the forecast
  - reason examples:
    - `scored`
    - `score_already_recorded`

- `unscorable`
  - meaning: enough wall-clock time has passed, but the realized data is invalid or incomplete for trustworthy scoring
  - reason examples:
    - `empty_realized_window`
    - `missing_expected_candles`
    - `insufficient_realized_candles`

## Artifact Provenance

### Score Artifact

Each score records:

- which forecast it belongs to
- the scored target window
- predicted regime
- actual regime
- expected and observed candle counts
- provider data coverage at scoring time
- scoring basis

### Review Artifact

Each review records:

- which scores were used
- which forecasts those scores came from
- threshold used
- decision basis
- whether a proposal is recommended
- why a proposal was or was not recommended

### Proposal Artifact

Each proposal records:

- which review produced it
- which scores were used as the basis
- threshold used
- decision basis
- rationale for generation

### Strategy Decision Artifact

Each decision records:

- paper-only action recommendation
- evidence grade and confidence
- baseline ids used for quality gating
- current paper portfolio context
- invalidation conditions
- whether directional action is blocked and why

### Paper Order Artifact

Each paper order records:

- the strategy decision that produced it
- side (`BUY` or `SELL`)
- target paper position percentage
- current paper position percentage
- local order status
- rationale copied from the decision

Paper orders are local ledger artifacts only. They do not submit to a broker,
exchange, sandbox, or testnet.

### Paper Fill And Portfolio Artifacts

Each paper fill records:

- the local paper order it fills
- fill side and quantity
- market price and slippage-adjusted fill price
- gross value, fee, fee bps, slippage bps
- net cash change

Each portfolio snapshot records:

- cash
- equity / NAV
- positions
- realized and unrealized PnL
- gross and net exposure

Each equity curve point records the portfolio state needed for later risk and
research analysis.

These are local accounting artifacts only. They do not imply external execution.

### Risk Snapshot Artifact

Each risk snapshot records:

- current and max drawdown
- gross and net exposure
- per-symbol paper position percentage
- configured drawdown and exposure thresholds
- risk status: `OK`, `REDUCE_RISK`, or `STOP_NEW_ENTRIES`

Risk snapshots are paper-only gates. They can block or reduce later paper
decisions, but they do not submit broker or exchange orders.

### Control Event Artifact

Each control event records an audited paper-only operator control:

- action (`PAUSE`, `RESUME`, `STOP_NEW_ENTRIES`, `REDUCE_RISK`,
  `EMERGENCY_STOP`, or `SET_MAX_POSITION`)
- actor, reason, timestamp, and optional symbol scope
- whether confirmation was required and supplied
- optional parameter such as `max_position_pct`

Control events are local audit artifacts only. They can block local paper order
creation, but they do not call brokers, exchanges, sandboxes, or live APIs.

### Provider Run Artifact

Each provider run records:

- provider name and operation
- symbol
- success, empty-data, or error status
- candle count
- observed data window
- schema version
- error type/message when the provider fails

Provider runs are audit artifacts only. They make ingestion failures visible to
health-check and the dashboard without adding new data providers or live
execution.

### Automation Run Artifact

Each automation run records one paper-only cycle:

- start and completion time
- status (`completed`, `repair_required`, or `failed`)
- symbol, provider, and command
- ordered step list with step status and linked artifact ids
- linked health-check id
- linked strategy decision id
- linked repair request id when one exists

`run-once` writes this log after each cycle. It is an audit trail only; it does
not create a scheduler, mutate Codex automation TOML, or execute live trades.

### Notification Artifact

M5G adds local notification artifacts in `notification_artifacts.jsonl`.

These are not external push messages. They are read-only, paper-only local
records that mark events an operator should notice:

- new strategy decision
- BUY/SELL blocked by weak evidence, health, research, or risk gates
- `STOP_NEW_ENTRIES`
- blocking health-check result
- repair request created
- drawdown breach

Each notification records severity, title, message, action, source artifact ids,
linked decision/health/repair/risk ids, and `delivery_channel=local_artifact`.
No Telegram token, webhook, broker, exchange, or external notification service
is configured in M5G.

### Strategy Card And Experiment Registry Artifacts

PR6 adds the first Alpha Factory registry artifacts:

- `strategy_cards.jsonl`: versioned strategy hypothesis cards with strategy
  family, symbol universe, signal description, entry/exit/risk rules,
  parameters, data requirements, and linked research evidence.
- `experiment_budgets.jsonl`: per-strategy-card trial budget snapshots. Budget
  exhaustion is explicit and auditable.
- `experiment_trials.jsonl`: append-only trial records. `PASSED`, `FAILED`,
  `ABORTED`, and `INVALID` outcomes are all persisted so failed research is not
  hidden from later evaluation.

This stage is a registry foundation. It does not rank strategies, unlock
BUY/SELL, train models, or promote candidates. Those require later locked
evaluation and leaderboard gates.

### Locked Evaluation And Leaderboard Artifacts

PR7 adds hard-gate artifacts for ranking strategy candidates:

- `split_manifests.jsonl`: locked train / validation / holdout windows with
  embargo metadata.
- `cost_model_snapshots.jsonl`: fee, slippage, turnover, drawdown, and baseline
  suite assumptions used by the gate.
- `locked_evaluation_results.jsonl`: pass/fail hard-gate result for one
  strategy trial.
- `leaderboard_entries.jsonl`: rankable candidates and blocked candidates. A
  blocked candidate has `rankable=false` and `alpha_score=null`.

This stage does not implement CPCV/PBO/DSR/bootstrap statistics yet. It creates
the fixed artifact contract that later statistical gates can extend.

### Paper-Shadow Outcome Artifacts

PR8 adds the first outcome-learning artifact after leaderboard gating:

- `paper_shadow_outcomes.jsonl`: immutable paper-shadow window results linked to
  one leaderboard entry, locked evaluation, strategy card, and experiment trial.

Each outcome records observed return, benchmark return, after-cost excess
return, max adverse excursion, turnover, failure attribution labels, an outcome
grade, and a recommendation such as `PROMOTION_READY`, `RETIRE`, or
`QUARANTINE`. This does not automatically mutate strategy cards or submit
orders; it gives later research/autopilot stages auditable feedback.

### Research Autopilot Loop Artifacts

PR9 adds the first loop-level research artifacts:

- `research_agendas.jsonl`: agenda, hypothesis, target strategy family,
  expected artifacts, acceptance criteria, and blocked actions.
- `research_autopilot_runs.jsonl`: one linked loop record from agenda to
  strategy card, experiment trial, locked evaluation, leaderboard entry,
  strategy decision, paper-shadow outcome, and next research action.

This is an audit loop, not a scheduler. It does not generate strategies by
itself, mutate strategy cards, or place orders. It makes the learning cycle
inspectable so later stages can add real strategy revision workers.

### Strategy Revision Candidates

PR12 adds the first bounded self-evolving strategy primitive:

- `propose-strategy-revision` consumes a failed `paper_shadow_outcome`.
- It creates a DRAFT child `strategy_cards.jsonl` row with `parent_card_id`,
  failure-attribution metadata, and concrete rule/parameter mutations.
- It creates a linked `research_agendas.jsonl` row for retesting the revision.
- It is idempotent for the same outcome and does not promote the revised card.

This is not a full autonomous strategy trainer. It turns evidence from failed
simulated shadow windows into a specific next hypothesis for locked evaluation.

PR13 makes the revision candidate visible:

- the static dashboard shows a `策略修正候選` block inside strategy research;
- the operator console research page shows the DRAFT revision card, source
  paper-shadow failure, parent strategy, rule mutations, and retest agenda;
- the operator console overview preview includes the current revision candidate
  so the first page shows what the AI is trying to fix next.

This still does not automatically run the retest or promote the revised card.

PR14 adds the retest scaffold:

- `create-revision-retest-scaffold` consumes a DRAFT revision card.
- It creates or returns one `PENDING` `experiment_trials.jsonl` row linked to
  the revision card and source paper-shadow outcome.
- It can optionally lock `split_manifests.jsonl` and
  `cost_model_snapshots.jsonl` when explicit train / validation / holdout
  windows are provided.
- It does not create baseline, backtest, walk-forward, locked evaluation,
  leaderboard, or promotion artifacts.

This gives the next research worker a concrete starting point without claiming
the revised strategy has already been validated.

PR15 makes the scaffold visible:

- the dashboard revision panel shows the pending retest trial, dataset, locked
  split manifest, and next required artifacts;
- the operator console research page shows the same scaffold details;
- the operator console overview preview includes the retest scaffold summary.

This is read-only visibility. It does not run the retest or create downstream
research evidence.

PR16 makes the next retest step explicit:

- `revision-retest-plan` reads the DRAFT revision, source paper-shadow outcome,
  pending or passed retest trial, locked split, cost model, baseline, backtest,
  walk-forward, locked evaluation, leaderboard, and paper-shadow evidence.
- It returns ordered task statuses plus the exact next task ID.
- It emits command arguments for runnable research steps such as `backtest` and
  `walk-forward` only when their prerequisite split exists.
- It keeps missing split windows and future paper-shadow returns blocked instead
  of inventing them.

This is still read-only planning. It helps the self-evolving loop know what to
study next, but it does not execute a retest or promote a revised strategy.

PR17 makes the task plan visible:

- the static dashboard shows the next retest research task in the strategy
  revision panel;
- the operator console overview and research page show the same task status,
  missing inputs, blocked reason, and command args;
- the UX still does not execute any command or create downstream evidence.

PR18 makes the task plan auditable:

- `record-revision-retest-task-run` builds the same read-only task plan and
  writes one `automation_runs.jsonl` row with provider `research`.
- The run status records whether the next retest task is ready, blocked,
  complete, or in progress.
- It does not execute command args or create retest evidence.

PR19 shows that audit log in the read-only UX:

- dashboard and operator console render the latest matching retest task run;
- the panel includes run id, status, source command, completed time, and task
  steps;
- rendering remains display-only and never executes command args.

PR20 starts artifact-producing retest execution:

- `execute-revision-retest-next-task` executes only a ready
  `lock_evaluation_protocol` task;
- it calls repository/domain code directly rather than shelling out;
- unsupported ready tasks are rejected until implemented one at a time.

PR21 adds the next executor step:

- `generate_baseline_evaluation` builds and saves a baseline through existing
  domain code;
- the executor records the baseline id and an execution `AutomationRun`;
- `run_backtest` and later tasks remain explicitly unsupported.

### Strategy-Visible UX

PR10 promotes concrete strategy context from raw artifacts into the inspection
surfaces:

- the static dashboard has a `strategy-research` section near the top, before
  raw metadata-heavy panels
- the operator console overview shows a strategy research focus card before
  artifact counts
- the operator console research page shows the current strategy hypothesis,
  strategy rules, experiment trial, locked evidence gates, leaderboard status,
  paper-shadow outcome attribution, research agenda, and autopilot next action

This is still read-only. It does not mutate strategies, execute orders, or hide
the underlying artifacts; it makes the current research logic easier to inspect.

### Repair Request Artifact

Each repair request records:

- observed health failure
- exact reproduction command
- expected behavior
- affected artifacts
- recommended first tests
- paper-only safety boundary
- acceptance criteria

The health checker also writes a Codex-ready prompt under:

```text
.codex/repair_requests/pending/<repair_request_id>.md
```

## Idempotency and Rerun Safety

This version keeps JSONL compatibility and adds a SQLite repository for M2
storage migration. Rerun safety is enforced:

- the same forecast anchor/window resolves to the same forecast identity
- the same forecast cannot be scored twice
- the same review basis does not create duplicate reviews
- the same review does not create duplicate proposals
- the same baseline evidence does not create duplicate baseline evaluations
- the same decision basis does not create duplicate strategy decisions
- the same active symbol cannot receive a second paper order until the open
  paper order is handled by a later lifecycle stage
- rerunning `run-once` in the same hour does not keep creating semantically duplicate artifacts

## Replay Contract

Use `replay-range` for deterministic historical validation.

Replay guarantees:

- input datetimes must be timezone-aware
- the replay runner itself only accepts hour-aligned UTC boundaries
- replay executes on fixed hourly steps only
- replay uses the same forecast / resolve / scoring contract as `run-once`
- replay evaluation summaries are built from the replay-scoped artifacts for the requested symbol and window, not from the entire storage directory
- replay summaries are persisted to the base storage directory, while replay-run artifacts live in a replay-scoped storage path under `.replay/`

### Replay Scoped Storage

Each replay invocation writes its raw artifacts into a deterministic path under the chosen storage directory:

```text
<storage-dir>/.replay/<provider>/<symbol>/<start>-<end>/
```

This avoids contaminating one replay run with hidden forecast, score, review, or proposal state from another replay window or another symbol.

### Replay Metadata

After each replay run, the CLI writes:

- `last_replay_meta.json` in the base storage directory
- `evaluation_summaries.jsonl` in the base storage directory

The replay metadata reports:

- replay window start/end
- cycle count
- forecasts created
- scores created
- the replay-scoped evaluation summary

## Read-Only Inspector

This repository now includes a minimal read-only inspector layer.

Purpose:

- inspect the latest paper-only strategy decision
- inspect current health / repair status
- inspect the current system state without reading JSONL files manually
- inspect the latest forecast / score / review / proposal
- inspect the latest replay summary and raw metadata
- support operator review while the system remains in building mode

Current form:

- static HTML output
- generated from existing persisted artifacts
- no live controls
- no trading actions
- first screen emphasizes:
  - tomorrow's strategy decision
  - health / repair status
  - operator summary
  - current forecast
  - historical replay context
- raw metadata stays collapsed by default so the inspector remains readable before drill-down

### Dashboard Contract

The dashboard is an inspection surface only.

It does not:

- trigger forecasts
- mutate loop state
- write reviews or proposals
- control automation

It only reads:

- `forecasts.jsonl`
- `scores.jsonl`
- `reviews.jsonl`
- `proposals.jsonl`
- `evaluation_summaries.jsonl`
- `baseline_evaluations.jsonl`
- `portfolio_snapshots.jsonl`
- `risk_snapshots.jsonl`
- `strategy_decisions.jsonl`
- `provider_runs.jsonl`
- `repair_requests.jsonl`
- `market_candles.jsonl`
- `last_run_meta.json`
- `last_replay_meta.json`

`render-dashboard` expects an existing storage directory. This is intentional:
if the path is mistyped, the command fails instead of creating an empty artifact
tree that could be mistaken for a real system state.

### Dashboard Command

Generate the current dashboard:

```powershell
python run_forecast_loop.py render-dashboard --storage-dir .\paper_storage\manual-sample
```

By default this writes:

```text
<storage-dir>\dashboard.html
```

You can also choose a specific output path:

```powershell
python run_forecast_loop.py render-dashboard --storage-dir .\paper_storage\manual-sample --output .\dashboard.html
```

### Operator Console Command

M5A adds a local-only, read-only operator console skeleton with these pages:

- overview
- decisions
- portfolio
- research
- health
- control placeholder

Render one page to HTML for inspection:

```powershell
python run_forecast_loop.py operator-console --storage-dir .\paper_storage\manual-sample --page overview --output .\operator-console.html
```

Start the local console server:

```powershell
python run_forecast_loop.py operator-console --storage-dir .\paper_storage\manual-sample --host 127.0.0.1 --port 8765
```

The server only accepts local bind hosts (`127.0.0.1`, `localhost`, `::1`).
The M5A console does not provide forms, live trading, broker submission,
secret display, or real control execution.

M5B expands the `decisions` page into a decision timeline. Each decision card
shows:

- latest decision marker
- action, reason summary, evidence grade, risk, tradeable status
- blocked reason
- linked forecast, score, review, and baseline artifact ids
- invalidation conditions

This remains read-only and paper-only.

M5C expands the `portfolio` page with:

- NAV, cash, realized PnL, and unrealized PnL
- drawdown status and recommended risk action
- gross/net/position exposure
- risk gate current values and limits
- risk findings
- position quantity, average price, market price, market value, position %, and
  unrealized PnL

This also remains read-only and paper-only.

M5D expands the `health` page into a read-only health / repair queue:

- current health status, severity, and repair-required state
- blocking health findings surfaced before the raw finding table
- repair request queue with pending/resolved/ignored status visibility
- repair request detail cards with prompt path, reproduction command, affected
  artifacts, recommended tests, and acceptance criteria

The health page does not execute repairs, mutate repair status, run Codex, or
trigger automation. It only makes existing health-check and repair-request
artifacts inspectable.

M5E adds an audited paper-only control plane through CLI-written
`control_events.jsonl` artifacts and a read-only control page. The control page
shows the current paper-control state, recent audit events, and the exact CLI
commands to write controls.

Supported controls:

- `PAUSE`
- `RESUME`
- `STOP_NEW_ENTRIES`
- `REDUCE_RISK`
- `EMERGENCY_STOP`
- `SET_MAX_POSITION`

`RESUME`, `EMERGENCY_STOP`, and `SET_MAX_POSITION` require `--confirm`.
`EMERGENCY_STOP` and `PAUSE` block local paper order creation. `STOP_NEW_ENTRIES`
and `REDUCE_RISK` block new BUY paper orders while still allowing risk-reducing
SELL orders. `SET_MAX_POSITION` blocks oversized BUY paper orders. No control
event submits a broker/exchange order.

M5F adds automation run logs. The operator console overview shows the latest
automation run, status, linked health/decision/repair ids, and step artifacts.
This remains an inspection surface only.

M5G adds notification artifacts and shows the newest local notifications on the
operator console overview. These notifications are local artifacts only; they do
not send Telegram, push, email, broker, exchange, or external webhook traffic.

PR10 expands the read-only inspection UX for strategy research. The dashboard
and operator console now show the concrete strategy hypothesis, strategy rules,
locked evidence gates, leaderboard state, paper-shadow attribution, and
autopilot next research action without requiring the operator to read JSONL
records first.

## Codex Governance Docs And Prompts

PR11 records the controller workflow as repository documentation instead of a
fake runtime service:

- architecture: `docs/architecture/PR11-codex-governance-docs-prompts.md`
- controller governance: `docs/controller/controller-governance.md`
- Windows runbook: `docs/runbooks/windows-autopilot-controller.md`
- prompt templates:
  - `docs/prompts/controller-decision-template.md`
  - `docs/prompts/worker-handoff-template.md`
  - `docs/prompts/final-reviewer-prompt.md`

These docs define controller decision fields, worker routing, reviewer subagent
requirements, machine gates, runtime/secret exclusion, and the Edge browser
assumption for UX checks.

## Failure and Degrade Behavior

The loop degrades conservatively:

- if the horizon is complete but provider data does not fully cover the window, the forecast remains `waiting_for_data`
- if provider coverage exists but required hourly boundaries are missing, the forecast becomes `unscorable`
- if candles are empty or insufficient for classification, the loop does not crash into scoring; it leaves an auditable terminal state instead
- review and proposal generation only happen when the current run produced valid scores
- if evidence is weak, the decision engine blocks BUY/SELL
- if storage or artifact health is blocking, the decision engine emits `STOP_NEW_ENTRIES`
- health-check writes repair requests instead of relying on silent failures
- run-once writes local notification artifacts for decisions, blocked BUY/SELL
  gates, repair requests, health blocking, and drawdown breaches
- the dashboard degrades read-only: if no artifacts exist yet, it renders explicit empty states instead of failing

## Local Commands

Run tests:

```powershell
python -m pytest -q
```

Run one sample cycle:

```powershell
python run_forecast_loop.py run-once --provider sample --symbol BTC-USD --storage-dir .\paper_storage\manual-sample
```

Run one public-data cycle:

```powershell
python run_forecast_loop.py run-once --provider coingecko --symbol BTC-USD --storage-dir .\paper_storage\manual-coingecko
```

Run a cycle and produce a strategy decision:

```powershell
python run_forecast_loop.py run-once --provider coingecko --symbol BTC-USD --storage-dir .\paper_storage\manual-coingecko --also-decide
```

`run-once` also appends `automation_runs.jsonl` so each cycle can be traced
without reading `last_run_meta.json` alone.

Generate a paper-only strategy decision from existing artifacts:

```powershell
python run_forecast_loop.py decide --storage-dir .\paper_storage\manual-coingecko --symbol BTC-USD --horizon-hours 24
```

Generate independent paper-only strategy decisions for multiple registered
symbols:

```powershell
python run_forecast_loop.py decide-all --storage-dir .\paper_storage\manual-multi-asset --symbols BTC-USD,ETH-USD,SPY,QQQ --horizon-hours 24
```

`decide-all` evaluates each symbol independently. It does not optimize
cross-asset allocation or rebalance a portfolio.

Inspect the latest strategy lineage summary as machine-readable JSON:

```powershell
python run_forecast_loop.py strategy-lineage --storage-dir .\paper_storage\manual-coingecko --symbol BTC-USD
```

`strategy-lineage` is read-only. It exposes the same root strategy, revision
tree, paper-shadow outcome trajectory, performance verdict, and next research
focus used by the dashboard/operator console so automation can route research
without parsing HTML.

Persist the latest strategy lineage focus as a research agenda:

```powershell
python run_forecast_loop.py create-lineage-research-agenda --storage-dir .\paper_storage\manual-coingecko --symbol BTC-USD
```

`create-lineage-research-agenda` writes an idempotent
`strategy_lineage_research_agenda` entry to `research_agendas.jsonl`. It uses
the latest lineage verdict and next research focus to seed the next research
loop; it does not create a decision, mutate a strategy card, or submit any
order.

Turn that lineage agenda into a machine-readable next research task:

```powershell
python run_forecast_loop.py lineage-research-plan --storage-dir .\paper_storage\manual-coingecko --symbol BTC-USD
```

`lineage-research-plan` is read-only. It reports the next concrete task for the
current lineage agenda: propose a DRAFT revision, draft a replacement strategy
hypothesis when the lineage is quarantined, collect missing paper-shadow
evidence, or verify cross-sample persistence after improvement. When it emits a
command, the command is intended to be directly runnable by the next research
worker.

Record the current lineage research task plan as an audit-visible automation
run without executing the task:

```powershell
python run_forecast_loop.py record-lineage-research-task-run --storage-dir .\paper_storage\manual-coingecko --symbol BTC-USD
```

`record-lineage-research-task-run` writes only `automation_runs.jsonl`. It
records the current lineage agenda, root strategy, latest lineage outcome, task
statuses, and next-task readiness so later UX and automation passes can see
which strategy research work item was inspected.

Execute the next supported lineage research task:

```powershell
python run_forecast_loop.py execute-lineage-research-next-task --storage-dir .\paper_storage\manual-coingecko --symbol BTC-USD --now 2026-04-30T13:00:00+00:00
```

This currently executes two lineage tasks. For quarantined lineages it executes
`draft_replacement_strategy_hypothesis`, creating an idempotent DRAFT
replacement `strategy_cards.jsonl` row linked to the quarantined lineage root
and latest paper-shadow outcome. For improving lineages it executes
`verify_cross_sample_persistence`, creating a
`lineage_cross_sample_validation_agenda` in `research_agendas.jsonl` so the next
research worker has an explicit fresh-sample validation handoff. It records an
`AutomationRun`; it does not run the replacement strategy, place an order,
promote a card, or call any broker/exchange adapter.

Start a locked retest scaffold for that replacement card:

```powershell
python run_forecast_loop.py create-revision-retest-scaffold --storage-dir .\paper_storage\manual-coingecko --revision-card-id strategy-card:replacement-example --symbol BTC-USD --dataset-id research-dataset:replacement-retest --max-trials 20 --seed 17
```

Despite the historical command name, this now accepts both DRAFT revision cards
and DRAFT lineage replacement cards. Replacement retests keep compatibility with
the existing `revision-retest-plan` and `execute-revision-retest-next-task`
chain, but trial parameters include `revision_retest_kind =
lineage_replacement` and the source lineage root id.

If the replacement card already has a latest research dataset in storage, the
same executor can advance the first retest task:

```powershell
python run_forecast_loop.py execute-revision-retest-next-task --storage-dir .\paper_storage\manual-coingecko --revision-card-id strategy-card:replacement-example --symbol BTC-USD
```

This records only the pending retest scaffold and an `AutomationRun`. It does
not run a backtest, pass a trial, promote a strategy, create a paper order, or
touch broker/exchange adapters.

Create a local paper order from the latest strategy decision:

```powershell
python run_forecast_loop.py paper-order --storage-dir .\paper_storage\manual-coingecko --decision-id latest
```

Fill the latest local paper order using a synthetic or externally supplied
paper-only mark price:

```powershell
python run_forecast_loop.py paper-fill --storage-dir .\paper_storage\manual-coingecko --order-id latest --market-price 100
```

Mark the paper portfolio to market:

```powershell
python run_forecast_loop.py portfolio-snapshot --storage-dir .\paper_storage\manual-coingecko --market-price 105
```

Run paper-only risk gates against the latest portfolio state:

```powershell
python run_forecast_loop.py risk-check --storage-dir .\paper_storage\manual-coingecko --symbol BTC-USD
```

Write an audited paper-only operator control:

```powershell
python run_forecast_loop.py operator-control --storage-dir .\paper_storage\manual-coingecko --action STOP_NEW_ENTRIES --reason "provider incident"
```

Riskier controls require explicit confirmation:

```powershell
python run_forecast_loop.py operator-control --storage-dir .\paper_storage\manual-coingecko --action EMERGENCY_STOP --reason "manual safety stop" --confirm
python run_forecast_loop.py operator-control --storage-dir .\paper_storage\manual-coingecko --action SET_MAX_POSITION --max-position-pct 0.10 --reason "lower risk cap" --confirm
python run_forecast_loop.py operator-control --storage-dir .\paper_storage\manual-coingecko --action RESUME --reason "operator reviewed health" --confirm
```

List registered assets:

```powershell
python run_forecast_loop.py list-assets
```

Run a health audit and create a Codex repair request if blocking issues exist:

```powershell
python run_forecast_loop.py health-check --storage-dir .\paper_storage\manual-coingecko --symbol BTC-USD
```

Run one deterministic sample replay:

```powershell
python run_forecast_loop.py replay-range --provider sample --symbol BTC-USD --storage-dir .\paper_storage\manual-replay --start 2026-04-21T04:00:00+00:00 --end 2026-04-21T08:00:00+00:00 --horizon-hours 2
```

Import stored historical candles for deterministic replay:

```powershell
python run_forecast_loop.py import-candles --storage-dir .\paper_storage\manual-replay --input .\fixtures\btc-hourly.jsonl --symbol BTC-USD --source fixture
```

Audit stored candle coverage before replay:

```powershell
python run_forecast_loop.py candle-health --storage-dir .\paper_storage\manual-replay --symbol BTC-USD --start 2026-04-21T04:00:00+00:00 --end 2026-04-21T08:00:00+00:00
```

Run replay from stored candles:

```powershell
python run_forecast_loop.py replay-range --provider stored --symbol BTC-USD --storage-dir .\paper_storage\manual-replay --start 2026-04-21T04:00:00+00:00 --end 2026-04-21T08:00:00+00:00 --horizon-hours 2
```

Export stored candles:

```powershell
python run_forecast_loop.py export-candles --storage-dir .\paper_storage\manual-replay --symbol BTC-USD --output .\paper_storage\btc-hourly-export.jsonl
```

Inspect the US ETF/stock market calendar:

```powershell
python run_forecast_loop.py market-calendar --market US --start-date 2026-04-02 --end-date 2026-04-06
```

Import a US ETF/stock CSV fixture with adjusted close:

```powershell
python run_forecast_loop.py import-stock-csv --storage-dir .\paper_storage\manual-stock --input .\fixtures\spy-daily.csv --symbol SPY --source fixture
```

Check US ETF/stock fixture coverage. Weekends and configured US market holidays
are not expected sessions:

```powershell
python run_forecast_loop.py stock-candle-health --storage-dir .\paper_storage\manual-stock --symbol SPY --start-date 2026-04-02 --end-date 2026-04-06
```

Import macro event fixtures:

```powershell
python run_forecast_loop.py import-macro-events --storage-dir .\paper_storage\manual-macro --input .\fixtures\macro-events.jsonl --source fixture
```

Inspect the imported macro calendar:

```powershell
python run_forecast_loop.py macro-calendar --storage-dir .\paper_storage\manual-macro --start 2026-04-01T00:00:00+00:00 --end 2026-04-30T23:59:00+00:00 --event-type CPI --region US
```

Build a leakage-checked research dataset from scored forecasts:

```powershell
python run_forecast_loop.py build-research-dataset --storage-dir .\paper_storage\manual-coingecko --symbol BTC-USD
```

The dataset builder fails closed if any feature timestamp is after the forecast
decision timestamp, or if any label timestamp is not after the decision
timestamp.

Run a paper-only backtest from stored candles:

```powershell
python run_forecast_loop.py backtest --storage-dir .\paper_storage\manual-replay --symbol BTC-USD --start 2026-04-01T00:00:00+00:00 --end 2026-04-30T00:00:00+00:00
```

The M4C backtest engine uses stored candles only and writes
`backtest_runs.jsonl` plus `backtest_results.jsonl`. It reports strategy
return, buy-and-hold benchmark return, max drawdown, Sharpe, turnover, win
rate, and trade count with configurable paper-only fee/slippage assumptions.
The default fixed-rule strategy uses prior-candle signals only; it does not
use the same candle to decide and fill a trade.

Run walk-forward validation from stored candles:

```powershell
python run_forecast_loop.py walk-forward --storage-dir .\paper_storage\manual-replay --symbol BTC-USD --start 2026-04-01T00:00:00+00:00 --end 2026-04-30T00:00:00+00:00 --train-size 8 --validation-size 4 --test-size 4 --step-size 2
```

The M4D walk-forward engine records rolling train / validation / test
boundaries, runs paper-only validation and test backtests, writes
`walk_forward_validations.jsonl`, and reports aggregate validation return, test
return, benchmark return, excess return, test win rate, and overfit-risk flags.

Register a strategy card:

```powershell
python run_forecast_loop.py register-strategy-card --storage-dir .\paper_storage\manual-research --name "MA trend BTC" --family trend_following --version v1 --symbol BTC-USD --hypothesis "BTC trend continuation after moving-average confirmation." --signal-description "Fast moving average above slow moving average." --entry-rule "Enter long when fast_ma > slow_ma." --exit-rule "Exit when fast_ma <= slow_ma." --risk-rule "Max position 10% during research simulation." --parameter fast_window=3 --parameter slow_window=7 --data-requirement market_candles:BTC-USD:1h
```

Record an experiment trial, including failed outcomes:

```powershell
python run_forecast_loop.py record-experiment-trial --storage-dir .\paper_storage\manual-research --strategy-card-id strategy-card:example --trial-index 1 --status FAILED --symbol BTC-USD --max-trials 20 --failure-reason negative_after_cost_edge --metric excess_return=-0.02
```

If the declared trial budget is exhausted, the command still writes an
`ABORTED` trial with `failure_reason=trial_budget_exhausted`. The system should
never silently drop failed or over-budget research attempts.

Lock an evaluation protocol and cost model:

```powershell
python run_forecast_loop.py lock-evaluation-protocol --storage-dir .\paper_storage\manual-research --strategy-card-id strategy-card:example --dataset-id research-dataset:example --symbol BTC-USD --train-start 2026-01-01T00:00:00+00:00 --train-end 2026-02-01T00:00:00+00:00 --validation-start 2026-02-02T00:00:00+00:00 --validation-end 2026-03-01T00:00:00+00:00 --holdout-start 2026-03-02T00:00:00+00:00 --holdout-end 2026-04-01T00:00:00+00:00
```

Evaluate whether a strategy trial may enter the leaderboard:

```powershell
python run_forecast_loop.py evaluate-leaderboard-gate --storage-dir .\paper_storage\manual-research --strategy-card-id strategy-card:example --trial-id experiment-trial:example --split-manifest-id split-manifest:example --cost-model-id cost-model:example --baseline-id baseline:example --backtest-result-id backtest-result:example --walk-forward-validation-id walk-forward:example
```

`evaluate-leaderboard-gate` writes both `locked_evaluation_results.jsonl` and
`leaderboard_entries.jsonl`. If any hard gate fails, the entry remains visible
but not rankable.

Record the simulated paper-shadow result for a leaderboard entry:

```powershell
python run_forecast_loop.py record-paper-shadow-outcome --storage-dir .\paper_storage\manual-research --leaderboard-entry-id leaderboard-entry:example --window-start 2026-04-28T00:00:00+00:00 --window-end 2026-04-29T00:00:00+00:00 --observed-return 0.05 --benchmark-return 0.01
```

`record-paper-shadow-outcome` writes `paper_shadow_outcomes.jsonl`. Positive
after-cost excess return can become `PROMOTION_READY`; negative or high-risk
outcomes recommend `RETIRE`, `REVISE`, or `QUARANTINE` without changing strategy
state automatically.

Create a research agenda:

```powershell
python run_forecast_loop.py create-research-agenda --storage-dir .\paper_storage\manual-research --symbol BTC-USD --title "Trend candidate" --hypothesis "Trend continuation should survive shadow validation." --strategy-family trend_following --strategy-card-id strategy-card:example
```

Record a research autopilot loop from existing artifacts:

```powershell
python run_forecast_loop.py record-research-autopilot-run --storage-dir .\paper_storage\manual-research --agenda-id research-agenda:example --strategy-card-id strategy-card:example --experiment-trial-id experiment-trial:example --locked-evaluation-id locked-evaluation:example --leaderboard-entry-id leaderboard-entry:example --strategy-decision-id decision:example --paper-shadow-outcome-id paper-shadow-outcome:example
```

`record-research-autopilot-run` writes `research_autopilot_runs.jsonl`. Its
`next_research_action` is derived from locked evaluation, leaderboard, decision,
and paper-shadow outcome state.

Propose a DRAFT strategy revision from a failed paper-shadow outcome:

```powershell
python run_forecast_loop.py propose-strategy-revision --storage-dir .\paper_storage\manual-research --paper-shadow-outcome-id paper-shadow-outcome:example --created-at 2026-04-28T14:00:00+00:00
```

`propose-strategy-revision` writes a child `strategy_cards.jsonl` row and a
linked `research_agendas.jsonl` row. The generated strategy card remains
`DRAFT`; it must pass a new locked evaluation and paper-shadow cycle before any
later promotion workflow may trust it.

Create a pending retest scaffold for a DRAFT revision card:

```powershell
python run_forecast_loop.py create-revision-retest-scaffold --storage-dir .\paper_storage\manual-research --revision-card-id strategy-card:example-revision --symbol BTC-USD --dataset-id research-dataset:revision-retest --max-trials 20 --created-at 2026-04-28T14:00:00+00:00
```

Optionally lock a retest split/cost protocol at the same time:

```powershell
python run_forecast_loop.py create-revision-retest-scaffold --storage-dir .\paper_storage\manual-research --revision-card-id strategy-card:example-revision --symbol BTC-USD --dataset-id research-dataset:revision-retest --train-start 2026-01-01T00:00:00+00:00 --train-end 2026-02-01T00:00:00+00:00 --validation-start 2026-02-02T00:00:00+00:00 --validation-end 2026-03-01T00:00:00+00:00 --holdout-start 2026-03-02T00:00:00+00:00 --holdout-end 2026-04-01T00:00:00+00:00
```

`create-revision-retest-scaffold` writes a `PENDING` experiment trial and
returns `next_required_artifacts`. It does not create a locked evaluation result
or leaderboard entry; those require actual baseline, backtest, and walk-forward
evidence.

Inspect the next retest research task without writing artifacts:

```powershell
python run_forecast_loop.py revision-retest-plan --storage-dir .\paper_storage\manual-research --revision-card-id strategy-card:example-revision --symbol BTC-USD
```

`revision-retest-plan` prints JSON with `next_task_id`, task status, missing
inputs, linked artifact IDs, and command arguments for runnable steps. It is a
research planner, not a retest executor.

Record the current retest task plan as an audit-visible run log without
executing it:

```powershell
python run_forecast_loop.py record-revision-retest-task-run --storage-dir .\paper_storage\manual-research --revision-card-id strategy-card:example-revision --symbol BTC-USD --now 2026-04-29T09:30:00+00:00
```

`record-revision-retest-task-run` writes only `automation_runs.jsonl`. It does
not run the displayed command args.

Execute the next whitelisted retest task:

```powershell
python run_forecast_loop.py execute-revision-retest-next-task --storage-dir .\paper_storage\manual-research --revision-card-id strategy-card:example-revision --symbol BTC-USD --now 2026-04-29T10:00:00+00:00
```

Currently this supports `lock_evaluation_protocol`,
`generate_baseline_evaluation`, `run_backtest`, `run_walk_forward`,
`record_passed_retest_trial`, `evaluate_leaderboard_gate`, and explicit
`record_paper_shadow_outcome`. The backtest step uses the locked split manifest
holdout window and stored candles in the same storage directory. The
walk-forward step uses the locked full split window from `train_start` through
`holdout_end`. The passed-trial step links the pending retest trial to the
current dataset, backtest, walk-forward validation, and source paper-shadow
outcome. The leaderboard-gate step writes a locked evaluation result plus a
leaderboard entry from the plan-linked PASSED trial evidence. The shadow-outcome
step remains blocked unless the caller supplies `--shadow-window-start`,
`--shadow-window-end`, `--shadow-observed-return`, and
`--shadow-benchmark-return`; optional `--shadow-max-adverse-excursion`,
`--shadow-turnover`, and `--shadow-note` are passed through when available. Each
executed task writes the created artifact ids plus an execution `AutomationRun`,
then returns before/after task plans.

When a revision retest chain has completed through explicit shadow outcome
recording, the strategy research resolver reports the linked retest trial as
`PASSED` and leaves `Next Required` empty in the read-only surfaces instead of
showing stale scaffold requirements.

The completed revision retest can also be recorded with
`record-research-autopilot-run` without `--strategy-decision-id`. This exception
applies only to DRAFT revision cards with a linked paper-shadow outcome; normal
strategy autopilot runs still require a strategy decision.

Record a completed revision retest chain as a research autopilot run without
manually copying every evidence ID:

```powershell
python run_forecast_loop.py record-revision-retest-autopilot-run --storage-dir .\paper_storage\manual-research --revision-card-id strategy-card:example-revision --symbol BTC-USD --now 2026-04-30T13:30:00+00:00
```

The command refuses incomplete chains and writes no fake strategy decision.
After it is recorded, the dashboard and operator console show the latest
revision-scoped autopilot run beside the retest task plan and task-run log,
including loop status, next research action, blocked reasons,
paper-shadow outcome, and recorded steps.

Generate a Markdown research report from existing artifacts:

```powershell
python run_forecast_loop.py research-report --storage-dir .\paper_storage\manual-replay --symbol BTC-USD --created-at 2026-04-24T12:00:00+00:00
```

The M4E report is written under `reports/research/` by default and summarizes
data coverage, model vs baselines, backtest metrics, walk-forward metrics,
drawdown, overfit risk, and the latest strategy decision gate result. Generated
reports are runtime outputs and are ignored by git.

Render a dashboard for an existing storage directory:

```powershell
python run_forecast_loop.py render-dashboard --storage-dir .\paper_storage\manual-replay
```

Render the M5A local operator console overview:

```powershell
python run_forecast_loop.py operator-console --storage-dir .\paper_storage\manual-replay --page overview --output .\operator-console.html
```

Repair and summarize a storage directory after legacy artifact pollution or
before resuming hourly automation:

```powershell
python run_forecast_loop.py repair-storage --storage-dir .\paper_storage\manual-replay
```

The repair command writes `storage_repair_report.json` with a fresh
`generated_at_utc`, active forecast count, latest forecast id, and quarantine
status. Treat that report as a point-in-time audit record, not a live monitor.

Initialize the M2 SQLite repository:

```powershell
python run_forecast_loop.py init-db --storage-dir .\paper_storage\manual-replay
```

Migrate existing JSONL artifacts into SQLite:

```powershell
python run_forecast_loop.py migrate-jsonl-to-sqlite --storage-dir .\paper_storage\manual-replay
```

Check SQLite schema and artifact health:

```powershell
python run_forecast_loop.py db-health --storage-dir .\paper_storage\manual-replay
```

Export SQLite artifacts back to JSONL compatibility files:

```powershell
python run_forecast_loop.py export-jsonl --storage-dir .\paper_storage\manual-replay --output-dir .\paper_storage\manual-replay-export
```

## Remaining Gaps Intentionally Left for the Next Stage

This milestone improves correctness and auditability, but it does not yet solve everything:

- the current hourly loop still writes JSONL artifacts by default while M2A proves SQLite migration and export parity
- regime classification is still intentionally simple
- active automation remains `BTC-USD` first; non-BTC assets require their own artifacts before `decide-all` can produce non-fail-closed decisions
- per-symbol multi-asset decisions exist, but there is no portfolio optimizer or cross-asset allocation engine
- paper portfolio accounting and risk gates are basic local simulations, not broker reconciliation
- order lifecycle is minimal: created orders can be filled locally, but cancellation and partial fill lifecycle are deferred
- proposal logic is still heuristic and conservative
- health-check creates repair requests, but there is no autonomous repair daemon in this repo
- the static dashboard and local operator console remain read-only; controls
  are written through audited CLI events rather than browser forms
- automation run logs are audit artifacts only; scheduler orchestration and
  external run management remain outside the repo
- replay still writes summary metadata into the base storage directory instead of a more formal run registry or database
- US ETF/stock support is fixture-only; no live or paid data provider is wired
- Taiwan ETF calendar/provider support remains deferred
- macro events are calendar artifacts only; they do not yet influence decisions
- research datasets are artifact builders only; no model training or optimizer is included yet
- backtests are local paper simulations over stored candles; no broker or live execution path is involved
- walk-forward validation is now research evidence for BUY/SELL gates, but it
  still does not train models or execute trades
- research reports summarize existing artifacts only; they do not create new strategy gates
- research quality gates now block BUY/SELL unless sample size, baseline edge,
  backtest, drawdown, and walk-forward evidence pass
- PR9/PR10/PR11 research autopilot, strategy-visible UX, and Codex governance
  docs exist, PR12 can produce evidence-linked DRAFT revision candidates, and
  PR13 makes those candidates visible in the dashboard and operator console,
  PR27 keeps completed chains visible as completed revision evidence, and PR28
  records completed revision retests without fake decision artifacts. PR29 adds
  a one-command autopilot run recorder for completed revision retests, and PR30
  exposes those revision-scoped autopilot runs in the strategy UX. PR31 adds
  strategy lineage summaries for parent/revision outcomes and demotion or
  quarantine signals, but full
  scheduling, autonomous strategy generation, automatic promotion, and deeper
  CPCV/PBO/DSR/bootstrap statistics remain deferred
