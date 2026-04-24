# M4E Research Report

## Scope

M4E adds a Markdown research report generator. It summarizes existing paper-only
artifacts and writes a local report file. It does not train models, optimize
parameters, change BUY/SELL gates, add broker integration, use secrets, or add
live trading.

## Decision

Reports are runtime outputs, not canonical state. The generator reads existing
JSONL artifacts and writes Markdown under `reports/research/` by default.

Generated reports are ignored by git through `reports/` in `.gitignore`.

The report includes:

- data coverage;
- model vs baseline evidence;
- backtest metrics;
- walk-forward metrics;
- drawdown;
- overfit risk;
- latest strategy decision gate result;
- paper-only safety boundary.

## Command

```powershell
python .\run_forecast_loop.py research-report --storage-dir .\paper_storage\manual-replay --symbol BTC-USD --created-at 2026-04-24T12:00:00+00:00
```

The output filename format is:

```text
reports/research/YYYY-MM-DD-research-report-<id>.md
```

## Deferred

- automatic report scheduling;
- committing report fixtures as documentation examples;
- report-driven BUY/SELL gate changes;
- richer charts or HTML exports.
