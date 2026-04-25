# M5G Notification Artifacts Review

## Scope

Milestone: M5G Notification Artifacts.

This review covers local, paper-only notification artifact generation,
storage parity, health audit support, and operator console visibility.

It does not cover Telegram, push, email, webhooks, external notification
services, scheduler mutation, broker integration, exchange integration, live
trading, or secret handling.

## Implementation Summary

- Added `NotificationArtifact`.
- Added `notification_artifacts.jsonl` support to JSONL storage.
- Added SQLite migration/export/db-health parity for notification artifacts.
- Added health-check bad-row and duplicate-id audit for notification artifacts.
- Added notification generation for:
  - new strategy decision
  - BUY/SELL blocked
  - `STOP_NEW_ENTRIES`
  - health blocking
  - repair request created
  - drawdown breach
- Updated `run-once --also-decide` to write notification artifacts and record a
  `notifications` automation step.
- Added operator console overview display for latest local notifications.
- Kept notifications local and read-only; no external delivery, secrets,
  scheduler mutation, broker path, exchange path, or live trading path was
  added.

## Verification

- `python -m pytest tests\test_notifications.py tests\test_m1_strategy.py::test_cli_run_once_also_decide_writes_one_command_strategy_decision tests\test_m1_strategy.py::test_health_check_audits_bad_and_duplicate_notification_artifacts tests\test_operator_console.py::test_operator_console_renders_required_pages_read_only tests\test_sqlite_repository.py -q`
  - Result: `11 passed in 2.72s`
- `python -m pytest -q`
  - Result: `190 passed in 6.95s`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Result: passed
- `python .\run_forecast_loop.py --help`
  - Result: passed
- `git diff --check`
  - Result: passed; only CRLF normalization warnings were printed

After reviewer P1 fix:

- `python -m pytest tests\test_notifications.py -q`
  - Result: `3 passed in 0.11s`
- `python -m pytest -q`
  - Result: `191 passed in 6.90s`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Result: passed
- `python .\run_forecast_loop.py --help`
  - Result: passed
- `git diff --check`
  - Result: passed; only CRLF normalization warnings were printed

## Smoke Evidence

Storage/output are under ignored `paper_storage/`.

- Ran one sample paper cycle with decision generation:
  - `python .\run_forecast_loop.py run-once --provider sample --symbol BTC-USD --storage-dir .\paper_storage\manual-m5g-notifications --now 2026-04-25T05:00:00+00:00 --also-decide`
- Result:
  - `new_forecast_status=pending`
  - `decision_action=HOLD`
  - `decision_id=decision:db08dbe55eb76533`
  - `automation_run_id=automation-run:3bd8c0616a56984f`
  - `notification_count=2`
- `notification_artifacts.jsonl` contains:
  - `NEW_DECISION`
  - `BUY_SELL_BLOCKED`
  - `delivery_channel=local_artifact`
  - linked `decision_id`, `health_check_id`, and `risk_id`
- `automation_runs.jsonl` contains:
  - `notifications` step with both notification ids
- Rendered overview:
  - `python .\run_forecast_loop.py operator-console --storage-dir .\paper_storage\manual-m5g-notifications --page overview --output .\paper_storage\manual-m5g-console\overview.html --now 2026-04-25T05:05:00+00:00`
- Rendered HTML contains:
  - `Notifications`
  - `notification:263baff9da4750a4`
  - `notification:8f8e118838299813`
  - `新策略決策`
  - `買進/賣出訊號被擋`

## Reviewer Status

Initial final reviewer subagent: `Helmholtz`
(`019dc29a-39fc-7190-96e4-68410c0c6bbb`).

Initial result: `BLOCKED`.

Blocking finding:

- `DRAWDOWN_BREACH` incorrectly fired for non-drawdown risk gates because
  `_drawdown_breached()` treated every `REDUCE_RISK` or `STOP_NEW_ENTRIES`
  risk snapshot as a drawdown breach. Exposure-only or position-only risk
  findings could therefore create false drawdown notifications.

Fix:

- Restricted `_drawdown_breached()` to
  `current_drawdown_pct >= reduce_risk_drawdown_pct`.
- Added regression coverage proving exposure-only `REDUCE_RISK` at
  `current_drawdown_pct=0.0` does not emit `DRAWDOWN_BREACH`.

Reviewer also confirmed the PR had no external notification delivery, no
scheduler mutation, no live trading path, no broker/exchange submit path, and
no secrets/runtime artifacts.

Final reviewer status after fix: pending re-review.

## Automation Status

M5G records local notification artifacts. It does not change hourly automation
cadence or local Codex automation configuration.
