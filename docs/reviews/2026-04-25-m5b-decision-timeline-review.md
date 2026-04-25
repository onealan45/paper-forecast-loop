# M5B Decision Timeline Review

## Scope

Milestone: M5B Decision Timeline.

This review covers the read-only decision timeline in the local operator
console. It does not cover portfolio/risk UI expansion, health/repair queue
workflow, audited controls, notifications, broker integration, sandbox brokers,
or live trading.

## Implementation Summary

- Expanded the operator console `decisions` page.
- Added latest decision summary.
- Added timeline cards showing:
  - action and symbol;
  - reason summary;
  - evidence grade;
  - risk level;
  - tradeable status;
  - recommended/current/max paper position;
  - blocked reason;
  - forecast, score, review, and baseline artifact ids;
  - invalidation conditions.
- Kept the page read-only with no forms, no enabled controls, and no order
  submission path.

## Verification

- `python -m pytest tests\test_operator_console.py -q`
  - Result: `8 passed in 0.34s`
- `python -m pytest -q`
  - Result: `176 passed in 6.07s`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Result: passed
- `python .\run_forecast_loop.py --help`
  - Result: passed
- `git diff --check`
  - Result: passed; only CRLF normalization warnings were printed

## Smoke Evidence

Storage/output are under ignored `paper_storage/`.

- Ran:
  - `python .\run_forecast_loop.py operator-console --storage-dir .\paper_storage\manual-m4f-check-20260424b --page decisions --output .\paper_storage\manual-m5b-console\decisions.html --now 2026-04-25T01:45:00+00:00`
- Result:
  - exit code `0`
  - output mode `render_once`
  - rendered HTML contains `最新決策`, `Decision Timeline`, `買進`,
    `Evidence Links`, `Invalidation Conditions`, `Forecast:`, `Score:`,
    `Baseline:`, and `Blocked reason`

## Reviewer Status

First final reviewer subagent result: APPROVED.

Reviewer rationale:

- M5B stays scoped to read-only rendering of existing
  `strategy_decisions.jsonl` data.
- The decisions page renders latest summary, timeline cards, evidence links,
  invalidation conditions, blocked reason, and paper-position fields.
- No schema, dependencies, forms, enabled controls, broker/exchange submit
  paths, secret access, or live-trading behavior were added.

Reviewer non-blocking risks:

- This review archive still needed the subagent result recorded.
- Test coverage was string-presence heavy and did not have a dedicated
  non-empty review-id / multi-decision ordering test.

Follow-up fix:

- `tests/test_operator_console.py` now covers newest-first timeline ordering,
  non-empty review ids, and blocked reason rendering for a blocked decision.

Second final reviewer subagent result: APPROVED.

Reviewer rationale:

- M5B stays scoped to read-only rendering of existing strategy decision
  artifacts.
- The decisions page exposes latest summary, newest-first timeline cards,
  evidence links including review ids, blocked reasons, position sizing fields,
  and invalidation conditions.
- No schema, dependencies, forms, enabled controls, broker/exchange submission,
  secret access, or live-trading behavior were added.

Reviewer-ran checks:

- `python -m pytest tests\test_operator_console.py -q`
- `python -m pytest -q`

## Automation Status

M5B does not change hourly automation, paper trading gates, broker adapters, or
live execution. It only improves inspection of existing strategy decisions.
