# M7D Market Reaction Review

## Summary

Review target: `codex/m7d-market-reaction`

Milestone: PR3 / M7D Market Reaction

Reviewer: independent Codex reviewer subagent `Dewey`

Result: `APPROVED`

## Reviewed Scope

M7D adds:

- `forecast_loop.market_reaction.build_market_reactions`
- `build-market-reactions` CLI
- point-in-time market reaction checks from canonical event snapshots,
  reliability checks, and stored candles
- already-priced blocking by pre-event drift or volume shock
- exact hourly candle boundary handling
- tests and architecture documentation

This review explicitly checked that the PR does not add live fetching, secret
handling, broker paths, live order submission, M7E historical edge, or M7F
decision integration.

## Reviewer Result

Reviewer response:

> APPROVED

No blocking findings were reported.

## Reviewer Commands

The reviewer reported running:

```powershell
python -m pytest tests\test_market_reaction.py -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
git diff --check
python .\run_forecast_loop.py --help
python .\run_forecast_loop.py build-market-reactions --help
python .\run_forecast_loop.py build-market-reactions --storage-dir . --created-at not-a-date
python .\run_forecast_loop.py build-market-reactions --storage-dir . --created-at 2026-04-28T12:00:00+00:00 --already-priced-return-threshold 0
python -m pytest -q
```

Reported results:

- `tests\test_market_reaction.py`: `7 passed`
- full pytest: `243 passed`
- compileall: passed
- diff check: passed with LF/CRLF warnings only
- CLI help: passed
- `build-market-reactions --help`: passed and shows `--created-at` required
- malformed datetime and invalid threshold: operator-friendly errors with no traceback
- point-in-time probes with temporary storage: passed

## Merge Gate

M7D may proceed to PR/merge only if local and GitHub machine gates pass:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

M7D-specific smoke must also pass:

```powershell
python .\run_forecast_loop.py import-source-documents --storage-dir <temp-dir> --input .\fixtures\source_documents\sample_news.jsonl --source sample_news --imported-at 2026-04-28T10:05:00+00:00
python .\run_forecast_loop.py build-events --storage-dir <temp-dir> --symbol BTC-USD --created-at 2026-04-28T10:05:00+00:00 --min-reliability-score 60
python .\run_forecast_loop.py import-candles --storage-dir <temp-dir> --input <candles.jsonl> --symbol BTC-USD --source fixture --imported-at 2026-04-28T12:00:00+00:00
python .\run_forecast_loop.py build-market-reactions --storage-dir <temp-dir> --symbol BTC-USD --created-at 2026-04-28T12:00:00+00:00
```
