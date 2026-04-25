# Alpha Factory Research Background

## Purpose

This document integrates the user-provided 2026-04-25 deep research report into
the project background. It records the direction for the next research phase
after M1-M6: the repository should evolve from a paper-only strategy research
robot into a trustworthy, reproducible, and extensible Alpha Factory.

Current M1-M6 work is a useful foundation. It provides auditable artifacts,
paper-only decisions, health checks, repair requests, research datasets,
baselines, backtests, walk-forward validation, risk gates, and sandbox broker
visibility. It is not yet a full Alpha Factory because it still lacks broad
strategy generation, locked experiment governance, deeper validation statistics,
canonical provider comparison, and evidence-driven promotion/demotion.

## Core Direction

The long-term target is:

> Paper-only, evidence-gated, multi-strategy, artifact-native Alpha Factory.

The guiding principle is:

> 放開策略搜尋空間，鎖死評估流程。

This means strategy ideas may become broader and more aggressive, but every idea
must pass through the same fixed data snapshots, split manifests, trial budget,
cost model, validation suite, and promotion rules. The system should be allowed
to explore many candidate alphas, but it must reject false positives
aggressively.

The project must keep these boundaries:

- Paper-only research remains the default operating mode.
- Live trading, live broker order submission, real capital, and automatic
  promotion to live remain out of scope.
- Sandbox/testnet interfaces are allowed only behind explicit paper/sandbox
  safety gates.
- Research output should answer whether a candidate is trustworthy, not only
  whether one backtest looked profitable.

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

The research report suggests that the next major stage should not be live
execution. It should harden the research factory:

| Stage | Direction | Definition of done |
|---|---|---|
| M7A | Data contracts and audit spine | Ingests produce schema-checked provider audits with response hashes and normalization metadata. |
| M7B | Canonical market data layer | Primary and secondary providers can be compared, gaps and duplicates are detected, and snapshots are reproducible. |
| M7C | Experiment registry and locked splits | Every trial, including failures, is recorded with dataset snapshot, split manifest, seed, code hash, and trial budget. |
| M7D | Validation engine upgrade | Purged folds, CPCV-like paths, PBO, DSR, bootstrap intervals, and stability reports are available. |
| M7E | Leaderboard and promotion engine | Candidates move through research, holdout, shadow, promoted, demoted, and archived states by artifact-driven gates. |
| M7F | Paper shadow sandbox and quarantine | Paper-only shadow monitoring can quarantine candidates on data, cost, risk, or execution anomalies. |

These stages should preserve the M1-M6 safety boundary: paper-only by default,
sandbox/testnet only when explicitly gated, and no live trading path.
