# M3F Per-Symbol Multi-Asset Decisions

## Scope

M3F adds `decide-all` for independent paper-only decisions across registered
assets. It does not add portfolio optimization, cross-asset allocation,
multi-symbol automation, broker integration, sandbox/testnet access, secrets,
or live trading.

## Decision

The existing strategy decision engine remains the single source for each
symbol. `decide-all` parses a comma-separated symbol list, validates each
symbol against the asset registry, and calls the same fail-closed decision path
used by `decide`.

Each symbol receives its own:

- health-check;
- risk-check when health is not repair-required;
- baseline evaluation;
- strategy decision.

The command returns one JSON envelope containing all decisions in request order.
Duplicate symbols are de-duplicated while preserving the first occurrence.

## Command

```powershell
python .\run_forecast_loop.py decide-all --storage-dir <storage> --symbols BTC-USD,ETH-USD,SPY,QQQ --horizon-hours 24
```

## Multi-Symbol Health Semantics

`last_run_meta.json` remains a single latest-run metadata file. In multi-symbol
storage, it may legitimately describe a different symbol than the one currently
being audited. Health-check therefore only enforces
`last_run_meta.json.new_forecast.forecast_id` when the metadata symbol matches
the health-check symbol.

Missing or stale forecasts for any requested symbol still fail closed and can
create Codex repair request artifacts.

## Deferred

- portfolio optimizer;
- cross-asset allocation;
- multi-symbol scheduled automation;
- dashboard table of all per-symbol decisions;
- broker or sandbox order fan-out;
- multi-asset risk aggregation.
