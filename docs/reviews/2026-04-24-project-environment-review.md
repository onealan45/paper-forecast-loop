# 2026-04-24 Project and Development Environment Review

## Scope

Comprehensive review of the paper-only forecasting project, current development environment, dashboard UX, automation state, artifact semantics, replay behavior, and repo documentation.

## Reviewer Sources

- controller / supervisor subagent: repo and readiness risk scan
- contract + replay reviewer subagent: core loop, replay, storage, and artifact semantics
- data + infra reviewer subagent: CLI, automation, development environment, generated artifacts
- ui + docs reviewer subagent: dashboard readability, Traditional Chinese UI, documentation consistency
- final reviewer subagent: consolidated blocker decision

## Decision

`hourly-paper-forecast` should remain paused until the P1 blockers are fixed and verified.

The run/storage core looked healthy, but the operator and replay surfaces were not trustworthy enough to resume automation at the time of review.

## P1 Findings

- Dashboard reported hourly automation as `ACTIVE` while `C:\Users\User\.codex\automations\hourly-paper-forecast\automation.toml` had `status = "PAUSED"`.
- Dashboard selected the latest proposal independently from the latest review, which could show an old proposal under the current review.
- Dashboard summarized `waiting_for_data` as a resolved state, hiding provider coverage wait states.
- New forecasts used lookback candle count for `observed_candle_count`, overstating target-window coverage.
- `replay-range` allowed CoinGecko, but the CoinGecko provider reads a moving 7-day public window and is not deterministic replay input.
- Replay summary proposal filtering could include proposals with empty `score_ids`.

## P2 Findings

- Some failure-state labels fell back to raw snake_case in the Traditional Chinese dashboard UI.
- Dashboard automation status lacked generated-at and source freshness context.
- `ForecastScore.from_dict` could fall back to naive `datetime.now()` values.
- Partial legacy forecast rows could fail with low-level datetime parsing errors.
- Unsupported CoinGecko symbols could raise `KeyError`.
- `render-dashboard` could create directories while being presented as an inspection path.
- Invalid CLI datetimes raised raw `ValueError`.
- `repair-storage` was missing from the README command list.
- `storage_repair_report.json` lacked freshness metadata and could be misread after storage advanced.
- Generated `output/playwright` screenshots were visible in git status.
- PRD and dashboard plan text had stale current-state wording.

## P3 / Backlog Findings

- Sidebar navigation lacked a labelled `nav` landmark.
- Long-run replay and scoring paths have avoidable repeated JSONL scans and rewrites.
- Development setup assumes ambient `pytest` and does not declare a dev dependency group.

## Verification Evidence

- `python --version` returned `3.13.2`.
- `python .\run_forecast_loop.py --help` exposed `run-once`, `replay-range`, `render-dashboard`, and `repair-storage`.
- `python -m pytest -q` passed with `38 passed`.
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` passed.
- Active storage had no duplicate forecast, score, review, or proposal IDs.
- `last_run_meta.json` matched the latest forecast tail at review time.
- No matured pending forecasts were found at review time.

## Follow-Up

Fix the six P1 findings first, keep automation paused during repair, regenerate the dashboard, rerun the full test suite, and request a final reviewer subagent before resuming hourly automation.
