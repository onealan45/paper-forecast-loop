# Paper Forecast Loop

Paper-only public-data strategy research robot for `BTC-USD`.

This repository is intentionally narrow. The M1 goal is not feature breadth. The
goal is the first **auditable strategy research robot**:

- create a forecast on a reproducible hourly boundary
- wait for the target window to complete
- only score when provider coverage is complete
- generate review and proposal artifacts with provenance
- compare prediction quality against baselines
- produce a paper-only strategy decision for the next horizon
- create Codex repair requests when health checks find blocking issues
- keep reruns safe and idempotent

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
- CLI execution via:
  - `run-once`
  - `replay-range`
  - `render-dashboard`
  - `operator-console`
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
  - `build-research-dataset`
  - `research-report`
  - `backtest`
  - `walk-forward`

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
