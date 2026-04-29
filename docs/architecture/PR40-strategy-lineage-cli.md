# PR40 Strategy Lineage CLI

## Purpose

PR40 adds a read-only `strategy-lineage` CLI command for automation and
research consumers.

Before PR40, the latest strategy lineage summary was visible in the dashboard
and operator console, but machine consumers had to read JSONL artifacts
directly or scrape HTML. The new command exposes the same lineage summary as
JSON.

## Command

```powershell
python run_forecast_loop.py strategy-lineage --storage-dir .\paper_storage\manual-coingecko --symbol BTC-USD
```

The output payload includes:

- `storage_dir`
- `symbol`
- `strategy_lineage`

`strategy_lineage` is `null` when no strategy card lineage can be resolved.
When present, it includes the root card, revision tree, paper-shadow outcome
trajectory, performance verdict, recommended strategy action, and next research
focus.

## Design

The command reuses:

- `resolve_latest_strategy_research_chain`
- `build_strategy_lineage_summary`
- existing `JsonFileRepository` loaders

It does not create forecasts, decisions, retest runs, paper-shadow outcomes, or
repair requests. It is intentionally read-only so hourly automation and
research loops can inspect strategy lineage without changing state.

## Why This Matters

The project direction is research and prediction strength. Strategy lineage is
the current bridge between a strategy idea, its revisions, observed simulated
outcomes, and the next research focus.

Machine-readable lineage output lets future self-evolving strategy workers
route work based on actual lineage evidence instead of UI text.

## Non-Goals

PR40 does not:

- generate a new strategy
- choose a BUY/SELL/HOLD action
- execute any retest task
- submit any paper or sandbox order
- read secrets
- write runtime artifacts

## Verification

Regression coverage asserts that `strategy-lineage` emits the expected latest
lineage summary JSON, including `performance_verdict` and
`next_research_focus`.
