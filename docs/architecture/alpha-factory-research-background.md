# Alpha Factory Research Background

## Purpose

This document integrates the user-provided 2026-04-25 deep research report into
the project background. It records the direction for the next research phase
after M1-M6: the repository should evolve from a paper-only strategy research
robot into a prediction-focused, strategy-generating, self-improving Alpha
Factory.

Current M1-M6 work is a useful foundation. It provides auditable artifacts,
paper-only decisions, health checks, repair requests, research datasets,
baselines, backtests, walk-forward validation, risk gates, and sandbox broker
visibility. It is not yet a full Alpha Factory because it still lacks strong
strategy generation, self-evolving skills, broad data/tool surfaces, deeper
validation statistics, canonical provider comparison, and visible strategy
learning.

The user's updated priority is research and prediction strength. Safety
machinery is not the product goal. The current execution boundary is that the
system must not place real orders or move real capital. This is the current
research/simulation boundary, not a permanent statement that automated trading
will never be designed.

The 2026-04-28 ChatGPT Pro master decision is now recorded in
[`autonomous-alpha-factory-master-decision.md`](autonomous-alpha-factory-master-decision.md).
That decision supersedes loose M7+ sequencing notes when there is a conflict.
The immediate next stage is PR0 Reviewability And Formatting Gate. After PR0,
the priority is M7B-M7F Alpha Evidence Engine work: source registry, source
document import, event reliability, already-priced / market reaction,
historical edge, and decision integration.

## Current Implementation Interpretation

The current repository should be interpreted as an Alpha Factory foundation, not
as the completed factory.

| Layer | Current M1-M6 state | Alpha Factory gap |
|---|---|---|
| Decision layer | Produces paper-only strategy decisions with evidence, risk, blocked reasons, PR8 paper-shadow outcome recommendations, PR12 DRAFT revision candidates, PR13 revision visibility, PR14 pending retest scaffolds, PR15 retest scaffold visibility, PR16 read-only retest task plans, PR17 task-plan UX, PR18 retest task run logs, PR19 run-log UX, PR20 first-step retest execution, PR21 baseline-step execution, PR22 holdout backtest-step execution, PR23 walk-forward-step execution, PR24 passed-trial recording, PR25 leaderboard-gate execution, PR26 explicit shadow-outcome closure, PR27 completed-chain visibility, PR28 revision retest autopilot-run recording without fake decisions, PR29 one-command retest autopilot-run recording, PR30 UX visibility for those completed retest autopilot runs, and PR31 strategy lineage summaries. | Needs richer demotion history and broader automated retest execution. |
| Health and repair | Detects artifact and runtime issues and can write repair requests. | Needs research-specific findings for provider distortion, experiment invalidation, and promotion quarantine. |
| Storage | Has SQLite migration support and JSONL audit/export compatibility. | Needs stronger research snapshot metadata and larger dataset storage conventions. |
| Data providers | Supports sample, CoinGecko, stored candles, and CSV stock fixtures. | Needs canonical primary/secondary provider comparison before serious promotion. |
| Research evidence | Supports baselines, research datasets, backtests, reports, walk-forward, research gates, PR6 strategy-card / experiment-trial registry, PR7 locked-evaluation / leaderboard hard-gate artifacts, PR8 paper-shadow outcome learning, PR9 agenda/autopilot loop records, PR14 revision retest scaffolds, PR16 retest task planning, PR18 run logs, PR19 visible run-log evidence, PR20 protocol-lock execution, PR21 baseline execution, PR22 holdout backtest execution from locked split windows, PR23 walk-forward execution from locked full split windows, PR24 PASSED retest trial recording from existing evidence, PR25 locked evaluation / leaderboard-entry execution from that retest evidence, PR26 paper-shadow outcomes from explicit observation inputs, PR27 resolver visibility for completed retest chains, PR28 research autopilot records for completed revision retests, PR29 CLI recording of those completed chains, PR30 UX visibility for the recorded completed-chain autopilot evidence, and PR31 strategy lineage summaries. | Needs strategy generation, self-evolving skills, CPCV-like paths, PBO, DSR, bootstrap, and parameter stability. |
| UI and operations | Shows read-only decisions, health, portfolio, risk, automation, broker/sandbox state, concrete strategy context, leaderboard state, paper-shadow attribution, next research action, pending revision retest scaffold state, visible next retest task plans, visible audit logs for task-plan inspections, visible completed revision retest autopilot runs, and strategy lineage summaries with demotion/quarantine signals. | Needs richer hypothesis-change history, comparison charts, and demotion trend views. |

## Core Direction

The long-term target is:

> Research-capable, prediction-focused, multi-strategy, self-improving Alpha
> Factory.

The guiding principle is:

> 放開策略搜尋空間，鎖死評估流程。

This means strategy ideas may become broader and more aggressive, but every idea
must pass through the same fixed data snapshots, split manifests, trial budget,
cost model, validation suite, and promotion rules. The system should be allowed
to explore many candidate alphas, but it must reject false positives
aggressively.

The project must keep this current boundary:

- Do not place real orders.
- Do not move real capital.
- Do not require or store real live-trading secrets.

Future automated trading work would require an explicit new user request and a
separate design stage; it should not be smuggled into the current
research/simulation milestones.

Everything else should be evaluated by whether it improves research,
prediction, simulation, backtesting, strategy learning, or strategy explanation.
Research output should answer what strategy is being tested, why it might work,
how it performed, why it failed, and what the system should try next.

## Vibe-Trading Lessons To Adopt

Vibe-Trading is a useful reference because it is much stronger as a broad
research workbench. The project should learn from these patterns:

| Vibe-Trading pattern | How this project should adapt it |
|---|---|
| Finance skill registry | Add first-class strategy and research skills that can be loaded, improved, and reused by the loop. |
| Self-evolving skills | Let the system propose, revise, and retire strategy skills based on backtest and prediction evidence. |
| Swarm workflows | Add research teams such as idea generator, data checker, backtester, prediction reviewer, risk critic, and strategy refiner. |
| MCP tools | Expose research commands as tools so external agents can run backtests, predictions, strategy generation, dataset checks, and reports. |
| Broad data loaders | Add more data-source adapters when useful for prediction, not only when they are public or already normalized. |
| Cross-market backtests | Expand beyond a single BTC loop into multi-market simulation and comparison. |
| Statistical validation utilities | Add Monte Carlo, bootstrap confidence intervals, walk-forward upgrades, and then deeper CPCV/PBO/DSR checks. |
| Agent memory | Persist research lessons, failed hypotheses, strategy preferences, and observed market regimes. |
| Strategy export/review surfaces | Show generated strategy logic, code, assumptions, metrics, and revisions in the UX. |
| Shadow account concept | Compare the system's strategy behavior against a user or baseline behavior in simulation. |

The adaptation should favor research power over conservative UX. Tool-rich loops
are acceptable. Natural-language strategy generation is acceptable. Large tool
access is acceptable when it does not place real orders.

## Research Factory Operating Model

Future strategy expansion should follow this controlled path:

1. Idea intake records the prompt, code hash, parent strategy, strategy family,
   and intended asset universe.
2. Dataset snapshot freezes provider inputs, canonical bars, macro events,
   calendar rules, normalization version, and response hashes.
3. Split manifest freezes train, validation, CPCV-like, holdout, embargo, and
   paper-shadow windows.
4. Trial runner executes within a declared trial budget and records every
   success, failure, abort, and invalid result.
5. Validation suite computes baseline edge, purged fold results, CPCV-like
   summaries, PBO, DSR, bootstrap intervals, drawdown, turnover, and stability.
6. Holdout gate runs only after research gates pass and should not be visible to
   the idea generator during search.
7. Paper-shadow gate monitors the candidate without live execution.
8. Promotion or demotion writes immutable artifacts and updates the leaderboard.
9. Skill evolution updates or creates reusable strategy skills when evidence
   suggests a durable lesson.
10. The UX exposes the concrete strategy, hypothesis, evidence, failure mode,
    and next research action.

This model lets the search space grow without letting the evaluation path move
after results are known.

## Threat Model

Alpha Factory work starts by assuming the research loop can fool itself. The
main risks are:

| Risk | Project-specific failure mode | Required control |
|---|---|---|
| Overfitting | Codex, models, or operators keep generating prompts, features, parameters, and strategy variants until one looks good. | Trial registry, trial budget, deflated Sharpe ratio, probability of backtest overfitting, and locked holdout. |
| Data leakage | Features include information not available at decision time, or labels overlap with train/test folds. | Feature timestamps, label timestamps, no-lookahead checks, purging, embargo, and invariant tests. |
| Lookahead or same-bar bias | A signal is generated and filled using the same bar, or adjusted/future data leaks into a historical decision. | Prior-bar decision rules, explicit fill timing, calendar-aware data, and engine invariants. |
| Selection bias | Failed experiments are omitted, so the leaderboard only sees survivors. | Append-only experiment registry including failed, aborted, and invalid trials. |
| Cost and slippage understatement | High-turnover strategies survive only because costs are too optimistic. | Asset-specific cost models, cost sweeps, slippage sensitivity, and implementation consistency checks. |
| Survivorship bias | Future stock/ETF work only evaluates symbols that still exist. | Listing status, delisted metadata, corporate action handling, and point-in-time universes. |
| Provider distortion | Different providers use different OHLC, volume, calendar, session, and gap-filling rules. | Raw response hashes, provider audit logs, cross-source diff artifacts, and normalization versions. |

## Data Layer Background

The next stage should prioritize data trust before adding more model variety.

Recommended data direction:

- CoinGecko is acceptable for prototype runs, secondary checks, and fallback, but
  `market_chart`-derived pseudo candles should not be the only canonical OHLC
  source for serious intraday crypto research.
- Crypto canonical data should prefer exchange-native klines for the primary
  venue under study, while retaining cross-source comparison and provider
  limitation notes.
- US ETF/stock research should move beyond fixture CSV before serious strategy
  promotion. It needs adjusted prices, market calendar handling, listing status,
  and provider audit metadata.
- Taiwan ETF daily research can start from official daily market data. Intraday
  Taiwan research should be treated as a separate provider and cost-model
  decision.
- Every ingest should retain provider name, request window, response hash,
  received timestamp, timezone/session calendar, normalization version, missing
  bar count, duplicate count, and cross-source diff summary.

SQLite remains useful for local canonical state and relational artifact links.
For larger research datasets, the likely M7+ direction is SQLite metadata plus
versioned columnar snapshots for research features and bars. JSONL remains
valuable as audit export and compatibility format, not as the only long-term
research store.

## Validation Background

Walk-forward validation is necessary but insufficient. It simulates deployment
order, but it should not be the only model selection or promotion mechanism.

The research validation stack should evolve toward:

- Locked final holdout that idea generators cannot repeatedly inspect.
- Split manifests with train, validation, CPCV-like folds, embargo, holdout, and
  paper-shadow periods.
- Purged cross-validation where overlapping labels can leak information.
- CPCV or CPCV-like validation to reduce dependence on one historical path.
- Probability of backtest overfitting to quantify selection risk.
- Deflated Sharpe ratio or equivalent multiple-testing correction.
- Block or stationary bootstrap confidence intervals for dependent returns.
- Parameter stability checks, including subperiod consistency, parameter ridge
  width, and cost robustness.
- Paper-shadow monitoring before any candidate can be considered promoted inside
  paper/sandbox research.

The practical policy is hard gates first, composite ranking second. A candidate
that fails data quality, leakage, overfitting, holdout, drawdown, or cost gates
should not be rescued by a high raw return score.

## Alpha Score Governance

`alpha_score` should rank only candidates that already passed mandatory gates.

Initial hard gates should include:

- schema, data-quality, and leakage checks pass;
- CPCV median excess return is positive;
- deflated Sharpe ratio is positive;
- probability of backtest overfitting is below the configured threshold;
- locked holdout net excess return is positive;
- drawdown and turnover-cost limits are acceptable;
- parameter stability is not single-point fragile;
- paper-shadow period has no blocking data, cost, execution, or risk anomaly.

Only after those gates pass should a composite score rank candidates. Useful
components include holdout net excess return, deflated Sharpe ratio, CPCV median
excess return, bootstrap lower bound, stability score, cost robustness, and
implementation consistency.

The leaderboard should therefore be an evidence table, not a raw-performance
table. It should store strategy family, trial count, dataset snapshot, split
manifest, passed gates, holdout visibility, paper-shadow days, promotion stage,
and demotion reasons.

## M7+ Roadmap Implications

The research report and the 2026-04-28 master decision suggest that the next
major stage should not be live execution. It should make the research factory
materially stronger in this order:

| Stage | Direction | Definition of done |
|---|---|---|
| PR0 | Reviewability and formatting gate | Long single-line source/test files are made reviewable without behavior changes, and a lightweight reviewability guard exists. |
| M7A | Evidence artifact foundation | Source, event, reliability, reaction, edge, and feature artifacts exist with storage and health integrity checks. |
| M7B | Source registry and source document import | Sources are registered with timestamp, license, rate-limit, reliability, and point-in-time policy; fixture/importable documents exist. |
| M7C | Event reliability | Source documents become canonical events with dedupe, entity/symbol links, and reliability checks. |
| M7D | Market reaction | Already-priced / market reaction checks prevent stale or pre-priced events from creating directional evidence. |
| M7E | Historical edge | Event families are evaluated for after-cost edge, sample sufficiency, adverse excursion, drawdown, and stability. |
| M7F | Decision integration | Event-derived evidence can influence decisions only after source, reaction, edge, baseline, research, risk, and health gates pass. |
| PR6 | Strategy card and experiment registry | Strategies become versioned cards, trial budgets are recorded, and failed / aborted / invalid trials are persisted. |
| PR7 | Locked evaluation and leaderboard gates | Split manifests, cost models, locked evaluation results, and leaderboard entries exist; `alpha_score` is blocked until hard gates pass. |
| PR8 | Paper-shadow outcome learning | Leaderboard candidates can record simulated shadow-window results, failure attribution, and promotion / retire / quarantine recommendations. |
| PR9 | Research / paper autopilot loop records | Research agendas and autopilot run artifacts link strategy, evaluation, decision, paper-shadow outcome, and next research action. |
| PR30 | Revision retest autopilot UX | Completed DRAFT revision retest autopilot runs are visible in dashboard and operator console strategy surfaces. |
| PR31 | Strategy lineage visibility | Parent strategy, DRAFT revisions, shadow action counts, failure-attribution concentration, and latest outcome are visible in strategy UX. |
| M8+ | Strategy generation and strategy-visible UX | Paper-shadow scheduling, strategy revision workers, deeper anti-overfit statistics, and UX expose concrete strategy reasoning. |

These stages should preserve the current execution boundary: no real orders and
no real capital movement.

## Minimum Acceptance Gates For M7+

The next implementation stage should not be considered complete unless it can
prove these gates with tests and artifacts:

- The UX exposes at least one concrete strategy, its hypothesis, parameters,
  backtest result, prediction rationale, and next revision.
- The loop can create or revise a reusable strategy skill from prior evidence.
- Vibe-Trading-inspired skills, swarm, MCP, data-loader, memory, and validation
  patterns are evaluated and prioritized in repo documentation.
- No candidate can read or modify the locked holdout path during research
  search.
- Every trial has a stable dataset snapshot id, split manifest id, strategy
  family id, code hash, prompt hash or source hash, seed, trial index, and trial
  budget.
- Failed, aborted, and schema-invalid experiments are persisted.
- Provider audit artifacts include raw response hash, normalization version,
  missing/duplicate bar counts, and calendar/timezone assumptions.
- BUY/SELL remains blocked when the latest research evidence is missing, stale,
  below baseline, overfit-risk flagged, or health/risk blocked.
- Leaderboard ranking is impossible until hard gates pass.
- Paper-shadow promotion can be demoted or quarantined by data, cost, risk,
  execution, or health anomalies.
- No code path can submit live orders or require live broker secrets.

## Sandbox Gate Clarification

Sandbox and broker gates are execution guards, not research guards. They should
not prevent:

- forecast generation;
- strategy generation;
- natural-language strategy editing;
- backtesting;
- simulation;
- prediction;
- research reports;
- strategy skill evolution;
- tool-rich automated research loops.

They should only prevent accidental real broker submission or movement of real
capital. If a gate blocks harmless research, backtesting, or simulation, it is
too strict for this project direction.
