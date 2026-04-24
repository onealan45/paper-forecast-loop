# M2C Paper Fills / Positions / NAV Review

## Scope

- Stage: M2C Paper Fills / Positions / NAV
- Branch: `codex/m2c-paper-fills-nav`
- Boundary: internal paper accounting only; no broker submit, no exchange, no sandbox/testnet, no live trading, no secrets.

## Implementation Summary

- Added `PaperFill`.
- Added `EquityCurvePoint`.
- Extended `PaperPortfolioSnapshot` with `realized_pnl`, `unrealized_pnl`, and `nav`.
- Added `paper_fills.jsonl` and `equity_curve.jsonl` repository support.
- Added SQLite migration/export/health parity for `paper_fills` and `equity_curve`.
- Added health-check parsing and duplicate-id checks for new artifacts.
- Added `paper-fill` CLI.
- Added `portfolio-snapshot` CLI.
- Added local accounting for:
  - fee bps
  - slippage bps
  - fill price
  - gross value
  - net cash change
  - quantity
  - average price
  - cash
  - equity / NAV
  - realized PnL
  - unrealized PnL
  - gross and net exposure
- Filled orders are marked `FILLED` and no longer count as active paper orders.
- Updated README, PRD, and architecture docs.

## Test Evidence

```powershell
python -m pytest tests/test_portfolio.py -q
```

Result: `5 passed`.

```powershell
python -m pytest tests/test_portfolio.py tests/test_sqlite_repository.py tests/test_paper_orders.py -q
```

Result: `17 passed`.

```powershell
python -m pytest -q
```

Result: `89 passed`.

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
```

Result: passed.

```powershell
python .\run_forecast_loop.py --help
```

Result: passed and showed `paper-fill` and `portfolio-snapshot`.

```powershell
git diff --check
```

Result: passed.

## M2C Smoke Evidence

An ignored storage fixture under `paper_storage/manual-m2c-check` was seeded
with a tradeable `BUY` strategy decision.

```powershell
python .\run_forecast_loop.py paper-order --storage-dir .\paper_storage\manual-m2c-check --decision-id latest --now 2026-04-24T12:00:00+00:00
python .\run_forecast_loop.py paper-fill --storage-dir .\paper_storage\manual-m2c-check --order-id latest --market-price 100 --fee-bps 5 --slippage-bps 10 --now 2026-04-24T12:00:00+00:00
python .\run_forecast_loop.py portfolio-snapshot --storage-dir .\paper_storage\manual-m2c-check --market-price 105 --now 2026-04-24T13:00:00+00:00
python .\run_forecast_loop.py migrate-jsonl-to-sqlite --storage-dir .\paper_storage\manual-m2c-check
python .\run_forecast_loop.py db-health --storage-dir .\paper_storage\manual-m2c-check
python .\run_forecast_loop.py export-jsonl --storage-dir .\paper_storage\manual-m2c-check --output-dir .\paper_storage\manual-m2c-export
```

Results:

- paper order was created;
- paper fill was created with slippage-adjusted fill price and fee;
- order was marked `FILLED`;
- portfolio snapshot showed cash, position, equity/NAV, exposure, and PnL;
- mark-to-market snapshot updated unrealized PnL and equity;
- SQLite migration included `paper_fills`, `portfolio_snapshots`, and `equity_curve`;
- `db-health` returned `healthy`;
- export wrote JSONL compatibility artifacts;
- generated `paper_storage` artifacts remained ignored by `.gitignore`.

## Known Deferrals

- Partial fills.
- Cancellation lifecycle.
- Risk gates.
- Dashboard portfolio/risk panels.
- Broker reconciliation.
- External paper/sandbox broker integration.

## Final Reviewer

- Reviewer subagent: `019dc029-d727-73b0-a96e-c724071cd5ee`
- Initial status: `BLOCKED`

Blocking findings:

1. `src/forecast_loop/portfolio.py` overestimated cash/equity/NAV for full
   `SELL` or `REDUCE_RISK` fills when slippage was present. The fill used target
   market value for cash movement while `_apply_fill` capped sold quantity to
   the actual position.
2. Tests did not cover sell/reduce-risk accounting, full exit, partial reduce,
   fee/slippage reconciliation, or `cash + market_value == equity/nav`.

Required remediation:

- cap SELL fill quantity and gross value before writing the fill;
- ensure net cash change, realized PnL, equity, and NAV use the same capped
  quantity and fill price;
- add SELL/REDUCE_RISK accounting tests;
- rerun full gates and re-review before merge.

## Remediation

- Updated SELL fill construction so quantity is capped to the actual position
  before gross value and net cash change are calculated.
- Added full-exit SELL test for cash/equity/NAV/realized PnL reconciliation.
- Added partial-reduce SELL test for cash plus remaining market value equaling
  equity/NAV with fee and slippage.
- Reran gates after remediation:
  - `python -m pytest tests/test_portfolio.py -q` -> `7 passed`
  - `python -m pytest -q` -> `91 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> passed

## Re-review

- Reviewer subagent: `019dc02e-bc6a-7283-b766-1371400d618d`
- Status: `APPROVED`
- Blocking findings: none

Reviewer confirmed:

- the SELL/REDUCE_RISK cash/NAV overstatement blocker is fixed;
- capped quantity is used before calculating gross value, fee, and net cash
  change;
- realized PnL uses the same capped quantity;
- new tests cover full exit and partial reduce reconciliation;
- no live trading, external submit, secret, or tracked runtime artifact risk was
  found.

Nonblocking risk:

- partial-reduce tests verify reconciliation but do not yet assert exact fee,
  net cash change, and realized PnL values. This is acceptable for M2C and can
  be tightened later.
