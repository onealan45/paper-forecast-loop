# M5C Portfolio / Risk UI Review

## Scope

Milestone: M5C Portfolio / Risk UI.

This review covers the read-only portfolio/risk page in the local operator
console. It does not cover control-plane behavior, paper order creation,
paper fills, health/repair queue workflow, notifications, broker integration,
sandbox brokers, or live trading.

## Implementation Summary

- Expanded the operator console `portfolio` page.
- Added NAV, cash, realized PnL, and unrealized PnL display.
- Added drawdown status, current drawdown, portfolio max drawdown, and
  recommended risk action.
- Added gross, net, and position exposure display.
- Added risk gate current values and limits:
  - position limit;
  - gross exposure limit;
  - reduce-risk drawdown trigger;
  - stop-new-entries drawdown trigger.
- Added risk findings.
- Expanded positions table with average price and market price.
- Kept the page read-only with no forms, no enabled controls, and no order
  submission path.

## Verification

- `python -m pytest tests\test_operator_console.py -q`
  - Result after blocker fix: `9 passed in 0.34s`
- `python -m pytest -q`
  - Result after blocker fix: `177 passed in 6.03s`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - Result: passed
- `python .\run_forecast_loop.py --help`
  - Result: passed
- `git diff --check`
  - Result: passed; only CRLF normalization warnings were printed

## Smoke Evidence

Storage/output are under ignored `paper_storage/`.

- Ran:
  - `python .\run_forecast_loop.py operator-console --storage-dir .\paper_storage\manual-m4f-check-20260424b --page portfolio --output .\paper_storage\manual-m5c-console\portfolio.html --now 2026-04-25T02:00:00+00:00`
- Result:
  - exit code `0`
  - output mode `render_once`
  - rendered HTML contains `NAV / Cash / PnL`, `Realized PnL`,
    `Unrealized PnL`, `Drawdown`, `Exposure`, `Risk Gates`,
    `Position`, `Gross exposure`, `Reduce-risk drawdown`,
    `Stop-new-entries drawdown`, `Avg Price`, and `Market Price`

## Reviewer Status

First final reviewer subagent result: BLOCKING FINDINGS.

Blocking finding:

- The portfolio page rendered drawdown `Max` from
  `PaperPortfolioSnapshot.max_drawdown_pct`, not `RiskSnapshot.max_drawdown_pct`.
  This could underreport risk max drawdown and mislead the operator.

Fix:

- The portfolio page now renders max drawdown from
  `RiskSnapshot.max_drawdown_pct`.
- `tests/test_operator_console.py` asserts `Max：8.00%` from the risk snapshot
  and rejects the portfolio fixture's lower `Max：2.00%`.

Second final reviewer subagent result: APPROVED.

Reviewer rationale:

- M5C scope is satisfied.
- The portfolio page is read-only.
- Max drawdown now uses `RiskSnapshot.max_drawdown_pct`.
- Required NAV/PnL/exposure/risk gate/findings/position fields are visible.
- No broker/exchange submit path, secrets access, external dependency, or
  storage schema was added.

## Automation Status

M5C does not change hourly automation, paper trading gates, broker adapters, or
live execution. It only improves inspection of existing portfolio and risk
artifacts.
