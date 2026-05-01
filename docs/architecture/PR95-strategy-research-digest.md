# PR95: Strategy Research Digest

## Context

PR81-PR94 improved the readability of strategy research panels, but automation
still had to reconstruct the current strategy story from many artifacts or parse
HTML. That is too weak for a research-first loop where strategy workers need one
compact handoff covering:

- the active strategy hypothesis;
- latest paper-shadow outcome;
- lineage failure concentration;
- linked evidence artifacts;
- next research action.

## Decision

Add `StrategyResearchDigest` as an append-only research artifact stored in:

- `strategy_research_digests.jsonl`
- SQLite artifact type `strategy_research_digests`

Add CLI:

```powershell
python run_forecast_loop.py strategy-research-digest --storage-dir .\paper_storage\manual-coingecko --symbol BTC-USD
```

The command resolves the latest strategy research chain, summarizes lineage
state, persists the digest, and prints JSON for automation consumers.

## Scope

Included:

- `StrategyResearchDigest` model with stable id, serialization, and parsing.
- JSONL repository save/load methods.
- SQLite repository save/load methods and migration/export artifact spec.
- Builder that links strategy card, trial, locked evaluation, leaderboard,
  paper-shadow outcome, research agenda, autopilot run, and lineage outcome ids.
- CLI command for writing the digest.

Excluded:

- dashboard redesign;
- strategy mutation;
- backtest execution;
- broker/exchange execution;
- any real order path.

## Why This Matters

This shifts the project from "readable status panels" toward a stronger
strategy research loop. A future self-evolving worker can now read one artifact
and know what strategy is being studied, what failed, what evidence supports
that conclusion, and what research action should happen next.

## Verification

- `python -m pytest tests/test_strategy_research_digest.py -q`
- `python -m pytest tests/test_sqlite_repository.py -q`
