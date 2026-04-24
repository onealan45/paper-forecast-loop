# M3E Macro Event Model

## Scope

M3E adds macro event storage and calendar inspection. It does not add macro
features, strategy logic, live data feeds, notifications, broker integration,
sandbox/testnet access, secrets, or live trading.

Supported event types:

- `CPI`
- `PCE`
- `FOMC`
- `GDP`
- `NFP`
- `UNEMPLOYMENT`

## Decision

Macro events enter the system as auditable fixture rows before they influence
research datasets or decisions. The artifact is:

- `macro_events.jsonl` in JSONL storage;
- `macro_events` in SQLite migration/export/db-health.

The import path is idempotent by stable event id derived from event type, region,
scheduled timestamp, and source.

## Commands

```powershell
python .\run_forecast_loop.py import-macro-events --storage-dir <storage> --input <macro-events.jsonl> --source fixture
python .\run_forecast_loop.py macro-calendar --storage-dir <storage> --start 2026-04-01T00:00:00+00:00 --end 2026-04-30T23:59:00+00:00 --event-type CPI --region US
```

## Artifact Shape

Each event row records:

- `event_id`;
- `event_type`;
- `name`;
- `region`;
- `scheduled_at`;
- `source`;
- `imported_at`;
- optional actual, consensus, previous values;
- optional unit, importance, and notes.

`scheduled_at` and `imported_at` must be timezone-aware.

## Deferred

- provider-specific macro importers;
- macro surprise calculation;
- leakage-aware feature generation;
- research-dataset joins;
- decision gates based on macro state;
- notifications for upcoming events.
