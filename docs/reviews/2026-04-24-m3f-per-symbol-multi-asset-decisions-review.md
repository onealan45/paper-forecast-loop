# M3F Per-Symbol Multi-Asset Decisions Review

## Scope

- Stage: M3F Per-Symbol Multi-Asset Decisions
- Branch: `codex/m3f-per-symbol-multi-asset-decisions`
- Boundary: `decide-all` CLI, per-symbol health/decision orchestration,
  multi-symbol `last_run_meta` health semantics, docs/tests only; no portfolio
  optimizer, no cross-asset allocation, no broker submit, no sandbox/testnet,
  no live trading, no secrets.

## Implementation Summary

- Added `decide-all --symbols BTC-USD,ETH-USD,SPY,QQQ`.
- `decide-all` validates symbols against the asset registry.
- Duplicate symbols are de-duplicated while preserving order.
- Each symbol runs through the same paper-only fail-closed decision path used by
  `decide`.
- Missing symbol-specific forecast evidence produces a fail-closed
  `STOP_NEW_ENTRIES` decision and repair request rather than a fake directional
  recommendation.
- Health-check ignores `last_run_meta` mismatches when the metadata belongs to a
  different symbol.
- Updated README, PRD, and architecture docs.

## Test Evidence

```powershell
python -m pytest tests/test_m3f_decide_all.py tests/test_m1_strategy.py -q
```

Result: `30 passed`.

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
```

Result: passed.

```powershell
python -m pytest -q
```

Result: `140 passed`.

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Result: passed.

## Smoke Evidence

```powershell
python .\run_forecast_loop.py decide-all --storage-dir .\paper_storage\manual-m3f-check-20260424T2010Z --symbols BTC-USD,ETH-USD,SPY,QQQ --now 2026-04-24T20:10:00+00:00
python .\run_forecast_loop.py health-check --storage-dir .\paper_storage\manual-m3f-check-20260424T2010Z --symbol SPY --now 2026-04-24T20:10:00+00:00
```

Result:

- `decide-all` returned four decisions in request order.
- All four decisions were independent `HOLD` decisions with
  `blocked_reason=insufficient_evidence`.
- SPY health-check returned `degraded` with only `dashboard_missing` warning.
- No false `last_run_meta_mismatch` was emitted for the non-BTC symbol.
- Manual smoke storage is ignored by `.gitignore`.

## Known Deferrals

- portfolio optimizer;
- cross-asset allocation;
- multi-symbol scheduled automation;
- dashboard table of all per-symbol decisions;
- broker or sandbox order fan-out;
- multi-asset risk aggregation.

## Final Reviewer

- Reviewer subagent: Ohm (`019dc100-3b72-7fc1-a390-9f1edcbbb277`)
- Re-review needed: no
- Status: approved; no blocking findings.

Residual non-blocking risks:

- `decide-all` validates registered assets by existence, not asset `status`;
  inactive registered symbols still fail closed unless proper artifacts exist.
- `decide-all` is CLI-only; dashboard multi-symbol timeline is deferred.
