# PR41 Strategy Lineage Research Agenda

## Purpose

PR41 adds `create-lineage-research-agenda`, a CLI command that turns the latest
strategy lineage `next_research_focus` into a persisted research agenda.

PR40 made lineage summaries machine-readable. PR41 makes that output actionable
for the next research loop by writing a stable `ResearchAgenda` artifact.

## Command

```powershell
python run_forecast_loop.py create-lineage-research-agenda --storage-dir .\paper_storage\manual-coingecko --symbol BTC-USD
```

Optional:

```powershell
python run_forecast_loop.py create-lineage-research-agenda --storage-dir .\paper_storage\manual-coingecko --symbol BTC-USD --created-at 2026-04-29T10:00:00+00:00
```

## Output

The command prints:

- `research_agenda`
- `strategy_lineage`

The agenda uses:

- `decision_basis = strategy_lineage_research_agenda`
- `strategy_card_ids = root strategy plus revision cards`
- `hypothesis = latest lineage next research focus plus verdict/action context`
- `priority = HIGH` for quarantine, revise, worsening, weak, or insufficient evidence

The agenda ID is deterministic. Re-running the command for the same lineage
focus does not append duplicate agenda rows.

## Design

The new `forecast_loop.lineage_agenda` module owns lineage-to-agenda conversion.
It reuses:

- `resolve_latest_strategy_research_chain`
- `build_strategy_lineage_summary`
- existing `ResearchAgenda` artifact schema

This keeps the CLI thin and avoids duplicating lineage logic.

## Non-Goals

PR41 does not:

- generate a new strategy card
- mutate an existing strategy card
- run a retest
- create a strategy decision
- submit paper, sandbox, or live orders
- add any live broker behavior

## Why This Matters

The user priority is stronger research, prediction, and self-evolving strategy
work. PR41 creates a concrete bridge from observed lineage performance to the
next research agenda, so future workers can act on lineage evidence rather than
only display it.

## Verification

Tests cover:

- creating a lineage-derived research agenda from a worsening/quarantine lineage
- preserving root and revision card IDs
- including the lineage next research focus in the agenda hypothesis
- idempotent re-runs
- missing lineage operator-friendly CLI error without traceback
