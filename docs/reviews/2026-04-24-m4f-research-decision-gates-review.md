# M4F Research Decision Gates Review

## Scope

Milestone: M4F Research-Based Decision Gates.

This review archive covers the decision-engine integration of research-quality
gates. It does not cover live trading, broker integration, sandbox/testnet
brokers, secrets, portfolio optimization, or automatic strategy promotion.

## Implementation Summary

- Added `src/forecast_loop/research_gates.py`.
- BUY/SELL now require:
  - minimum scored sample size;
  - positive model edge over baseline;
  - benchmark-beating backtest result;
  - acceptable backtest drawdown;
  - positive walk-forward excess return;
  - walk-forward test return beating benchmark;
  - no walk-forward overfit-risk flags.
- Missing or weak research evidence blocks BUY/SELL with `HOLD`.
- Overfit risk, excessive drawdown, or recent degradation recommends
  `REDUCE_RISK`.
- Existing health/risk fail-closed behavior remains paper-only.

## Verification

- `python -m pytest tests/test_research_gates.py tests/test_m1_strategy.py -q`
  - Result: `30 passed in 0.98s`
- `python -m pytest -q`
  - Result: `168 passed in 8.84s`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Result: passed
- `python .\run_forecast_loop.py --help`
  - Result: passed
- `git diff --check`
  - Result: passed; only CRLF normalization warnings were printed

## Smoke Evidence

Storage: `paper_storage\manual-m4f-check-20260424b` (ignored by git).

- Seeded scored forecasts, a fresh pending BTC-USD forecast, OK risk snapshot,
  backtest run/result, and walk-forward validation.
- Ran `python .\run_forecast_loop.py health-check --storage-dir .\paper_storage\manual-m4f-check-20260424b --symbol BTC-USD --now 2026-04-24T12:00:00+00:00`.
  - Result: `status=degraded`, `severity=warning`, `repair_required=false`
    because `dashboard.html` was not rendered for the smoke storage.
- Ran `python .\run_forecast_loop.py decide --storage-dir .\paper_storage\manual-m4f-check-20260424b --symbol BTC-USD --horizon-hours 24 --now 2026-04-24T12:00:00+00:00`.
  - Result: `action=BUY`, `tradeable=true`, `evidence_grade=B`,
    `blocked_reason=null`, and `research_gate ... flags=none`.
- Ran `python .\run_forecast_loop.py render-dashboard --storage-dir .\paper_storage\manual-m4f-check-20260424b`.
  - Result: dashboard rendered successfully.
- Reran `python .\run_forecast_loop.py health-check --storage-dir .\paper_storage\manual-m4f-check-20260424b --symbol BTC-USD --now 2026-04-24T12:00:00+00:00`.
  - Result: `status=healthy`, `severity=none`, `repair_required=false`.
- Ran `git check-ignore -v` for smoke storage; it is ignored by
  `paper_storage/`.

## Reviewer Findings And Fixes

First reviewer pass returned blocking findings:

- Research-driven `REDUCE_RISK` could become non-tradeable with no
  `blocked_reason` when there was no current paper position.
- README still described walk-forward validation as not gating BUY/SELL.
- PRD still described walk-forward validation as not influencing decision gates.

Fixes applied:

- Non-tradeable research `REDUCE_RISK` now records
  `research_reduce_required_but_no_position`.
- `tests/test_research_gates.py` asserts the no-position `REDUCE_RISK`
  blocked reason.
- README and PRD now state that walk-forward evidence influences paper-only
  BUY/SELL gates through M4F research-quality checks.

## Reviewer Status

Final reviewer subagent: APPROVED.

Reviewer result:

- No blocking findings.
- Prior blockers are fixed:
  - zero-position research `REDUCE_RISK` records
    `research_reduce_required_but_no_position`;
  - README and PRD no longer contradict M4F walk-forward gating;
  - targeted verification passed.

Non-blocking risk:

- M4F depends on available backtest and walk-forward artifacts; without those
  artifacts BUY/SELL correctly fail closed to HOLD.

## Automation Status

Hourly paper automation must remain paper-only. This milestone does not resume,
promote, or alter live execution because no live execution exists.
