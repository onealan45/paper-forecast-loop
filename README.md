# Paper Forecast Loop

Paper-only public-data forecasting and strategy-research loop for `BTC-USD`.

This repository is intentionally narrow. The goal of this milestone is not feature breadth. The goal is the first **trustworthy forecasting research loop**:

- create a forecast on a reproducible hourly boundary
- wait for the target window to complete
- only score when provider coverage is complete
- generate review and proposal artifacts with provenance
- keep reruns safe and idempotent

## Current Scope

This version intentionally includes only:

- single symbol: `BTC-USD`
- hourly public market data
- providers:
  - sample provider
  - CoinGecko provider
- JSONL artifacts:
  - `forecasts.jsonl`
  - `scores.jsonl`
  - `reviews.jsonl`
  - `proposals.jsonl`
- CLI execution via:
  - `run-once`
  - `replay-range`
  - `render-dashboard`

This version intentionally excludes:

- interactive UI controls
- live trading
- real capital
- multi-asset support
- portfolio / NAV / PnL accounting
- notifications / Telegram
- full scheduler or repair daemon orchestration

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

## Idempotency and Rerun Safety

This version keeps JSONL storage, but rerun safety is enforced:

- the same forecast anchor/window resolves to the same forecast identity
- the same forecast cannot be scored twice
- the same review basis does not create duplicate reviews
- the same review does not create duplicate proposals
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
- `last_run_meta.json`
- `last_replay_meta.json`

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

## Failure and Degrade Behavior

The loop degrades conservatively:

- if the horizon is complete but provider data does not fully cover the window, the forecast remains `waiting_for_data`
- if provider coverage exists but required hourly boundaries are missing, the forecast becomes `unscorable`
- if candles are empty or insufficient for classification, the loop does not crash into scoring; it leaves an auditable terminal state instead
- review and proposal generation only happen when the current run produced valid scores
- the dashboard degrades read-only: if no artifacts exist yet, it renders explicit empty states instead of failing

## Local Commands

Run tests:

```powershell
pytest -q
```

Run one sample cycle:

```powershell
python run_forecast_loop.py run-once --provider sample --symbol BTC-USD --storage-dir .\paper_storage\manual-sample
```

Run one public-data cycle:

```powershell
python run_forecast_loop.py run-once --provider coingecko --symbol BTC-USD --storage-dir .\paper_storage\manual-coingecko
```

Run one deterministic sample replay:

```powershell
python run_forecast_loop.py replay-range --provider sample --symbol BTC-USD --storage-dir .\paper_storage\manual-replay --start 2026-04-21T04:00:00+00:00 --end 2026-04-21T08:00:00+00:00 --horizon-hours 2
```

Render a dashboard for an existing storage directory:

```powershell
python run_forecast_loop.py render-dashboard --storage-dir .\paper_storage\manual-replay
```

## Remaining Gaps Intentionally Left for the Next Stage

This milestone improves correctness and auditability, but it does not yet solve everything:

- regime classification is still intentionally simple
- only `BTC-USD` is supported
- there is no portfolio or strategy-performance layer
- proposal logic is still heuristic and conservative
- there is no explicit repair daemon or orchestration state machine in this repo
- the inspector is currently static HTML, not a live operator app
- replay still writes summary metadata into the base storage directory instead of a more formal run registry or database
