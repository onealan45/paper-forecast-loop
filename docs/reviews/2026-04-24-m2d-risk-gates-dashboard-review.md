# M2D Risk Gates + Portfolio Dashboard Review

## Scope

- Stage: M2D Risk Gates + Portfolio Dashboard
- Branch: `codex/m2d-risk-gates`
- Boundary: internal paper risk and portfolio inspection only; no broker submit, no exchange, no sandbox/testnet, no live trading, no secrets.

## Implementation Summary

- Added `RiskSnapshot`.
- Added `risk_snapshots.jsonl` support to JSONL repository.
- Added SQLite migration/export/db-health parity for `risk_snapshots`.
- Added health-check bad-row and duplicate-id coverage for risk snapshots.
- Added `risk-check` CLI:
  - current drawdown gate
  - max drawdown reporting
  - gross exposure gate
  - per-symbol position exposure gate
  - `OK`, `REDUCE_RISK`, and `STOP_NEW_ENTRIES` statuses
- Connected risk snapshots to strategy decision generation:
  - `STOP_NEW_ENTRIES` risk blocks directional paper decisions.
  - `REDUCE_RISK` risk overrides BUY/SELL and recommends reducing current paper exposure.
  - corrupt storage skips risk evaluation and remains fail-closed through health-check.
- Added dashboard portfolio/risk panel:
  - NAV / equity
  - cash
  - realized and unrealized PnL
  - risk status
  - gross and net exposure
  - drawdown thresholds
- Updated README, PRD, and architecture docs.

## Test Evidence

```powershell
python -m pytest tests/test_risk.py tests/test_dashboard.py::test_dashboard_renders_portfolio_nav_pnl_and_risk tests/test_sqlite_repository.py -q
```

Result: `12 passed`.

```powershell
python -m pytest tests/test_m1_strategy.py::test_cli_decide_fail_closed_on_corrupt_portfolio_snapshot tests/test_risk.py -q
```

Result: `7 passed`.

```powershell
python -m pytest -q
```

Result: `98 passed`.

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
```

Result: passed.

```powershell
python .\run_forecast_loop.py --help
```

Result: passed and showed `risk-check`.

```powershell
git diff --check
```

Result: passed.

## M2D Smoke Evidence

Ignored storage fixture:

```text
paper_storage/manual-m2d-check-20260424T1600Z
```

Commands:

```powershell
python .\run_forecast_loop.py run-once --provider sample --symbol BTC-USD --storage-dir .\paper_storage\manual-m2d-check-20260424T1600Z --now 2026-04-24T16:00:00+00:00 --also-decide
python .\run_forecast_loop.py risk-check --storage-dir .\paper_storage\manual-m2d-check-20260424T1600Z --symbol BTC-USD --now 2026-04-24T16:00:00+00:00
python .\run_forecast_loop.py render-dashboard --storage-dir .\paper_storage\manual-m2d-check-20260424T1600Z
python .\run_forecast_loop.py migrate-jsonl-to-sqlite --storage-dir .\paper_storage\manual-m2d-check-20260424T1600Z
python .\run_forecast_loop.py db-health --storage-dir .\paper_storage\manual-m2d-check-20260424T1600Z
python .\run_forecast_loop.py export-jsonl --storage-dir .\paper_storage\manual-m2d-check-20260424T1600Z --output-dir .\paper_storage\manual-m2d-export-20260424T1600Z
```

Results:

- sample run produced a pending forecast and conservative `HOLD` decision;
- `risk-check` wrote `risk:4061fa5c5dcd9034` with status `OK`;
- dashboard rendered portfolio/risk copy including NAV, risk status, and exposure;
- SQLite migration inserted `risk_snapshots: 1`;
- `db-health` returned `healthy`;
- export wrote `risk_snapshots.jsonl`;
- generated `paper_storage` artifacts remained ignored by `.gitignore`.

## Known Deferrals

- operator controls and audited control plane;
- multi-asset risk aggregation;
- portfolio optimizer;
- external paper/sandbox broker reconciliation;
- typed relational risk tables.

## Final Reviewer

- Reviewer subagent: `019dc03f-f070-7b50-820e-1d76b14c41fd`
- Initial status: `BLOCKED`

Blocking finding:

1. `src/forecast_loop/decision.py` could still emit tradeable `BUY` or `SELL`
   when no fresh risk snapshot existed. CLI paths usually computed risk first,
   but direct/module callers and future schedulers could bypass that and produce
   `risk=none` directional decisions.

Nonblocking risks:

- dashboard currently uses the latest risk snapshot globally, not symbol-matched
  to the latest forecast/decision. Multi-asset storage is deferred, but this
  must be tightened before mixed-symbol storage directories are supported.

## Remediation

- Directional `BUY` and `SELL` now require same-symbol, fresh risk evidence.
- Missing, symbol-mismatched, or stale risk snapshots now convert directional
  actions to `STOP_NEW_ENTRIES` with explicit blocked reasons.
- Added tests covering:
  - strong evidence still produces `BUY` when fresh `OK` risk exists;
  - strong evidence is blocked without a risk snapshot;
  - strong evidence is blocked with a stale risk snapshot.
- Reran targeted remediation tests:
  - `python -m pytest tests/test_m1_strategy.py::test_strategy_decision_buys_only_when_evidence_beats_baseline tests/test_m1_strategy.py::test_strategy_decision_blocks_directional_buy_without_risk_snapshot tests/test_m1_strategy.py::test_strategy_decision_blocks_directional_buy_with_stale_risk_snapshot tests/test_risk.py -q` -> `9 passed`

## Re-review

- Reviewer subagent: `019dc03f-f070-7b50-820e-1d76b14c41fd`
- Status: `APPROVED`
- Blocking findings: none

Reviewer confirmed:

- the prior risk-snapshot fail-open blocker is fixed;
- directional `BUY` and `SELL` now require same-symbol, fresh risk evidence;
- missing, stale, or symbol-mismatched risk evidence blocks directional paper
  actions with explicit `STOP_NEW_ENTRIES` reasons;
- no live trading, broker/exchange submit, sandbox/testnet, API key, secret, or
  tracked runtime artifact risk was found.

Latest full gates after remediation:

- `python -m pytest -q` -> `100 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> passed

Remaining nonblocking risk:

- dashboard uses the latest risk snapshot globally rather than symbol-scoping it
  to the latest forecast/decision. This is acceptable for M2D while multi-asset
  storage is deferred, but must be tightened before M3F or any mixed-symbol
  storage directory.
