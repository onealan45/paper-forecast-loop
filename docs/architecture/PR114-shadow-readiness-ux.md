# PR114 Shadow Readiness UX

## Problem

PR112 and PR113 added useful readiness context to revision retest task-plan
rationale strings. The CLI JSON exposed that context, but the dashboard and
operator console still showed only blocked reason, missing inputs, and command
args. A human operator had to inspect raw JSON or infer why the current
paper-shadow outcome remained blocked.

## Decision

The dashboard and operator console now parse known shadow readiness keys from
the task rationale and render them as Traditional Chinese labels:

- `earliest_window_start` -> `最早合法觀察開始`
- `latest_stored_candle` -> `最新已儲存 K 線`
- `first_aligned_window_start` -> `第一個 K 線對齊開始`
- `next_required_window_end` -> `下一個需要的結束 K 線`
- `candidate_window_ready` -> `候選視窗狀態`

The display helper lives in `automation_step_display.py` so both UX surfaces use
the same copy.

## Boundary

This is display-only. It does not change retest planning, executor readiness,
shadow outcome recording, candle fetching, or post-leaderboard enforcement.

## Active Storage Example

The current BTC-USD active retest remains blocked because the latest stored
candle is `2026-05-01T18:00:00+00:00`, while the next required end candle is
still `missing`. The UI now shows that directly as
`候選視窗尚未完整 (false)`.

## Acceptance

- Dashboard renders the shadow readiness block in the revision retest task
  plan.
- Operator console renders the same shadow readiness block.
- Both surfaces show Traditional Chinese labels while retaining raw values.
- No task becomes executable because of this display change.
