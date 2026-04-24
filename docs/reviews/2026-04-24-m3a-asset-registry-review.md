# M3A Asset Registry Review

## Scope

- Stage: M3A Asset Registry
- Branch: `codex/m3a-asset-registry`
- Boundary: asset registry and `list-assets` only; no ETF/stock provider, no macro data, no `decide-all`, no broker submit, no sandbox/testnet, no live trading, no secrets.

## Implementation Summary

- Added static `Asset` registry in `src/forecast_loop/assets.py`.
- Registered required M3A assets:
  - `BTC-USD`
  - `ETH-USD`
  - `SPY`
  - `QQQ`
  - `TLT`
  - `GLD`
  - `0050.TW`
- Added asset status filtering:
  - `active`
  - `planned`
  - `inactive`
- Added `list-assets` CLI with JSON and text output.
- Updated README, PRD, and architecture docs.

## Test Evidence

```powershell
python -m pytest tests/test_assets.py -q
```

Result: `5 passed`.

```powershell
python -m pytest -q
```

Result: `105 passed`.

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
```

Result: passed.

```powershell
python .\run_forecast_loop.py --help
```

Result: passed and showed `list-assets`.

```powershell
python .\run_forecast_loop.py list-assets
python .\run_forecast_loop.py list-assets --status planned --format text
```

Result: passed and listed the registered assets.

```powershell
git diff --check
```

Result: passed.

## Known Deferrals

- provider audit layer;
- deterministic historical candles;
- ETF/stock data prototype;
- macro event model;
- per-symbol multi-asset decisions;
- portfolio optimization;
- broker or sandbox integration.

## Final Reviewer

- Reviewer subagent: `019dc04d-6561-7943-b077-6eafd110fed9`
- Status: `APPROVED`
- Blocking findings: none

Reviewer confirmed:

- M3A stayed within static asset registry plus `list-assets`;
- no ETF/stock provider, macro data, `decide-all`, optimizer, broker/testnet,
  live trading, secrets, or runtime artifact behavior was added;
- `ETH-USD` being `active` is acceptable because the existing CoinGecko mapping
  supports it, but docs should keep emphasizing BTC-first automation until later
  multi-asset stages.

Reviewer evidence:

- `python -m pytest tests/test_assets.py -q` -> `5 passed`
- `python -m pytest -q` -> `105 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> showed `list-assets`
- JSON/text `list-assets` smoke output works
- `git diff --check` -> passed with only CRLF warnings
