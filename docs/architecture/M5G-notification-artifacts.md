# M5G Notification Artifacts

## Scope

M5G adds local notification artifacts for paper-only operator attention.

This milestone does not add Telegram, push, email, webhooks, external services,
broker integration, exchange integration, live trading, or secret handling.

## Artifact

`notification_artifacts.jsonl` stores append-only `NotificationArtifact` rows.

Each row includes:

- `notification_id`
- `created_at`
- `symbol`
- `notification_type`
- `severity`
- `title`
- `message`
- `status`
- `delivery_channel`
- `action`
- `source_artifact_ids`
- linked `decision_id`, `health_check_id`, `repair_request_id`, and `risk_id`

`delivery_channel` is fixed to `local_artifact` in M5G.

## Notification Types

M5G emits:

- `NEW_DECISION`
- `BUY_SELL_BLOCKED`
- `STOP_NEW_ENTRIES`
- `HEALTH_BLOCKING`
- `REPAIR_REQUEST_CREATED`
- `DRAWDOWN_BREACH`

These notifications are attention markers. They are not delivery receipts and
do not imply a message was sent outside the repo.

## Generation

`run-once --also-decide` generates notifications after health-check, risk-check,
and strategy decision generation.

Rules:

- every generated strategy decision creates `NEW_DECISION`
- non-tradeable decisions with `blocked_reason` create `BUY_SELL_BLOCKED`
- `STOP_NEW_ENTRIES` decisions create `STOP_NEW_ENTRIES`
- blocking health-check results create `HEALTH_BLOCKING`
- health-check results with `repair_request_id` create `REPAIR_REQUEST_CREATED`
- risk snapshots breaching the reduce-risk drawdown threshold create
  `DRAWDOWN_BREACH`

The same run also records a `notifications` step in `automation_runs.jsonl`.

## Storage

M5G follows the existing artifact storage pattern:

- JSONL support in `JsonFileRepository`
- SQLite artifact parity through `ArtifactSpec`
- migration from JSONL to SQLite
- export from SQLite to JSONL
- db-health artifact counting
- health-check bad-row and duplicate-id audit

## Operator Console

The read-only operator console overview shows the latest local notification
artifacts. It does not acknowledge, dismiss, send, or mutate notifications.

## Safety Boundary

M5G remains paper-only.

It does not:

- send external notifications
- read notification secrets
- commit secrets
- mutate scheduler state
- submit orders
- call broker or exchange APIs
- create a live execution path
