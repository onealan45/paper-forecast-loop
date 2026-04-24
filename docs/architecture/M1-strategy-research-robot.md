# M1 Strategy Research Robot Architecture

## Goal

M1 upgrades the project from a forecast validation loop into a paper-only
strategy research robot. Each cycle must be able to produce an auditable
decision for the next horizon: buy, sell, hold, reduce risk, or stop new
entries.

## Current State

The repository already supports:

- provider-aligned forecasts
- matured forecast scoring
- review/proposal artifacts
- deterministic sample replay
- static read-only dashboard
- limited storage repair for legacy forecast quarantine

That is necessary infrastructure, but it does not yet answer the operator's
main question: what should the paper strategy do tomorrow, and how reliable is
that recommendation?

## Storage Decision

SQLite should become the M1 canonical store, but not in the same patch that adds
the decision and repair layers.

Reasoning:

- M1 and later scopes need relational links among decisions, forecasts, scores,
  baselines, portfolio snapshots, paper orders, PnL, risk state, and repair
  requests.
- JSONL is good for append-only audit exports and backward compatibility, but
  weak as the primary query model once paper trading and multi-asset data arrive.
- A full SQLite migration would touch every repository path and artifact test.
  Combining that with decision semantics would make the upgrade harder to
  verify and harder to roll back.

This PR therefore keeps JSONL as the active compatible store and adds the new
artifact families through the existing repository boundary. The next storage
milestone should introduce a `SQLiteRepository` behind the same load/save
methods, then dual-write JSONL audit exports until parity is proven.

## M1 Data Model

New artifact families:

- `strategy_decisions.jsonl`: the paper-only strategy recommendation for the
  next horizon.
- `baseline_evaluations.jsonl`: model quality versus a naive persistence
  baseline.
- `portfolio_snapshots.jsonl`: paper-only position and exposure context.
- `repair_requests.jsonl`: structured health failures that require Codex repair.
- `.codex/repair_requests/pending/*.md`: a Codex-ready prompt for each repair.

No artifact is allowed to execute live trades. Broker/exchange integration is
represented only through an interface and a paper adapter.

## Decision Rules

M1 must avoid fake BUY/SELL confidence:

- BUY/SELL requires enough scored samples and a positive edge over baseline.
- If the model does not beat the baseline, BUY/SELL is blocked.
- If recent scoring is poor, emit `REDUCE_RISK` or `STOP_NEW_ENTRIES`.
- If forecasts are missing, stale, provider-failed, or storage health is
  blocking, emit `STOP_NEW_ENTRIES` and create a repair request.
- Decisions must link back to forecast, score, review, and baseline artifacts.

## Health And Repair

`health-check` replaces the idea that `repair-storage` is enough.

The health subsystem checks:

- storage directory existence
- readable artifact rows
- duplicate ids
- forecast/meta tail alignment
- score/review/proposal/decision evidence references
- latest forecast presence and staleness
- dashboard freshness

When blocking health failures are found, it writes a structured repair request
and a Markdown prompt with reproduction commands, expected behavior, affected
artifacts, first tests to run, safety boundaries, and acceptance criteria.

## Paper Trading Boundary

M1 introduces a broker interface only to keep future live integration from
leaking into the decision engine. The only concrete adapter is
`PaperBrokerAdapter`.

Live adapters are intentionally unavailable and must fail closed. No API key
handling, real broker client, or real order path is allowed in M1.

## This PR Implements

- Strategy decision, baseline, portfolio, broker, health, and repair request
  models.
- JSONL repository methods for the new artifact families.
- Baseline evaluation against naive persistence.
- Paper-only decision engine with evidence gates.
- Health checker and Codex repair request generation.
- `decide` and `health-check` CLI commands, plus optional
  `run-once --also-decide`.
- Dashboard sections that prioritize tomorrow's strategy decision and health
  before raw metadata.
- Tests for weak evidence, baseline blocking, risk reduction, stale/missing
  forecasts, repair requests, paper broker safety, dashboard rendering, and CLI
  behavior.

## Deferred

- Switching the hourly loop from JSONL-default execution to SQLite-backed execution.
- M2D now adds first-pass risk gates and dashboard integration for paper portfolio state; later work still needs operator controls and multi-asset risk aggregation.
- Broker/exchange live adapters.
- Multi-asset strategy allocation.
- Macro and ETF/stock ingestion.
- Production scheduler orchestration beyond the local Codex automation.
