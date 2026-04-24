# M4B Baseline Expansion Review

## Scope

- Stage: M4B Baseline Expansion
- Branch: `codex/m4b-baseline-expansion`
- Boundary: expanded baseline suite recorded in `baseline_evaluations.jsonl`,
  docs/tests only; no model training, no backtest, no walk-forward validation,
  no optimizer, no broker submit, no sandbox/testnet, no live trading, no
  secrets.

## Implementation Summary

- Added `baseline_results` to `BaselineEvaluation`.
- Existing `baseline_accuracy` and `model_edge` remain tied to naive
  persistence for M1 gate compatibility.
- Added baseline suite:
  - `naive_persistence`;
  - `no_trade_cash`;
  - `buy_and_hold`;
  - `moving_average_trend`;
  - `momentum_7d`;
  - `momentum_14d`;
  - `deterministic_random`.
- `no_trade_cash` records no directional prediction and no directional
  accuracy.
- Deterministic random baseline uses stable score identifiers, not runtime
  randomness.
- Updated README, PRD, and architecture docs.

## Test Evidence

```powershell
python -m pytest tests/test_baselines.py tests/test_m1_strategy.py -q
```

Result: `29 passed`.

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
```

Result: passed.

```powershell
python -m pytest -q
```

Result: `151 passed`.

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Result: passed.

## Smoke Evidence

```powershell
python .\run_forecast_loop.py decide --storage-dir .\paper_storage\manual-m4b-check-20260424T2055Z --symbol BTC-USD --now 2026-04-24T20:55:00+00:00
```

Result:

- decision remained compatible with the existing gate and returned `BUY` with
  evidence grade `B`;
- `baseline_evaluations.jsonl` recorded seven baseline results;
- baseline names were `naive_persistence`, `no_trade_cash`, `buy_and_hold`,
  `moving_average_trend`, `momentum_7d`, `momentum_14d`, and
  `deterministic_random`;
- `baseline_accuracy` remained the naive persistence accuracy;
- manual smoke storage is ignored by `.gitignore`.

## Known Deferrals

- choosing the strongest baseline for BUY/SELL gating;
- return-based baseline metrics;
- backtest integration;
- walk-forward stability checks;
- research-based decision gates.

## Final Reviewer

- Reviewer subagent: McClintock (`019dc11b-5204-7252-bb0f-66f8a6e90dc4`)
- Re-review needed: no
- Status: approved; no blocking findings.

Residual non-blocking risk:

- existing legacy `baseline_evaluations.jsonl` rows with the same
  `baseline_id` will not be backfilled with `baseline_results` because storage
  dedupes by `baseline_id`.
