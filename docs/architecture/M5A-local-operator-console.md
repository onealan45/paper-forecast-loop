# M5A Local Operator Console Skeleton

## Decision

M5A adds a local-only, read-only operator console skeleton backed by the current
JSONL artifact repository.

The console is intentionally small:

- `overview`
- `decisions`
- `portfolio`
- `research`
- `health`
- `control` placeholder

## Implementation

- Module: `src/forecast_loop/operator_console.py`
- CLI: `python run_forecast_loop.py operator-console`
- One-shot render mode:
  - `--output <path>`
- Local server mode:
  - default `--host 127.0.0.1 --port 8765`
  - allowed bind hosts: `127.0.0.1`, `localhost`, `::1`

The one-shot render mode exists so the console can be verified in tests and
automation without starting a long-running server.

## Safety Boundary

M5A does not add trading controls.

The console:

- reads existing paper artifacts only;
- does not submit orders;
- does not talk to real brokers or exchanges;
- does not load API keys or `.env`;
- does not expose secrets;
- has no forms;
- shows the future control plane as disabled placeholder UI only.

## Deferred

- M5B decision timeline drilldown.
- M5C richer portfolio/risk UI.
- M5D repair queue workflow.
- M5E audited paper-only control plane.
- Any live trading or real broker/exchange path remains explicitly out of
  scope.
