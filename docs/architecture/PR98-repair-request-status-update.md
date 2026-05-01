# PR98: Repair Request Status Update

## Context

`health-check` can create `repair_requests.jsonl` rows when a storage or runtime
issue is blocking. After the underlying issue is fixed, a later healthy
health-check does not mutate the earlier repair request. This is good for
auditability, but it left stale `pending` repair requests visible in the
operator console even when the latest health status was healthy.

## Decision

Add a small explicit status-update command:

```powershell
python run_forecast_loop.py repair-request --storage-dir .\paper_storage\manual-coingecko --repair-request-id repair:abc123 --status resolved --reason "health-check returned healthy"
```

Supported final statuses:

- `resolved`
- `ignored`

Each update records:

- new status;
- status update timestamp;
- status reason.

## Scope

Included:

- `RepairRequest` status audit fields.
- JSONL and SQLite repository replacement support for repair requests.
- `repair-request` CLI command.
- Operator console display for status reason and update timestamp.
- Regression tests for successful status update, unknown-id failure, and health
  page display.

Excluded:

- automatic repair execution;
- automatic stale-request closure by health-check;
- deleting repair request prompts;
- modifying forecast, decision, or provider artifacts.

## Rationale

Repair requests are operational artifacts, not transient alerts. The system
should preserve them, but operators need a clear way to mark fixed or obsolete
items so the queue reflects current attention needs.

## Verification

- `python -m pytest tests/test_repair_requests.py -q`
- `python -m pytest tests/test_operator_console.py::test_health_page_shows_repair_request_status_reason -q`
- `python -m pytest -q`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
- `python .\run_forecast_loop.py --help`
- `git diff --check`
