# PR184 Dashboard Replay/Provider Symbol-Time Review

## Reviewer

- Reviewer subagent: Averroes
- Model: GPT-5.5
- Reasoning effort: xhigh
- Scope: `c7385ff..HEAD`
- Verdict: APPROVED

## Review Summary

The reviewer found no blocking issues. The reviewed change correctly stops the
dashboard from selecting replay and provider evidence by raw JSONL tail order.

Validated behavior:

- `latest_replay_summary` is selected from replay summaries whose
  `forecast_ids` or `scored_forecast_ids` intersect the active dashboard
  symbol's forecast ids, then by latest `generated_at`.
- If active-symbol forecast ids exist but no replay summary matches them, the
  dashboard may show a fallback replay only as stale historical context.
- `latest_provider_run` is selected from provider runs matching the active
  dashboard symbol, then by latest `created_at`.
- Tests cover stale file-tail ordering, cross-symbol contamination, and
  unmatched replay fallback freshness.
- The changed files are limited to dashboard construction, dashboard tests, and
  PR184 architecture documentation.
- No runtime artifacts, secrets, or live execution paths were introduced.

## Verification Evidence

Controller-run checks before final review:

```powershell
python -m pytest -q
# 613 passed in 32.76s

python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
# passed

python .\run_forecast_loop.py --help
# passed

git diff --check
# passed

python .\run_forecast_loop.py health-check --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD --symbol BTC-USD
# {"status": "healthy", "severity": "none", "repair_required": false, "findings": []}
```

Reviewer-run targeted checks:

```powershell
# PR184 targeted dashboard tests
# 4 passed in 0.50s
```

## Residual Risks

- Equal timestamp tie-break behavior still follows the existing `max(...)`
  semantics and is not explicitly defined.
- Legacy replay summaries without `forecast_ids` or `scored_forecast_ids` cannot
  be precisely aligned to active forecast evidence; they are shown only through
  stale historical fallback.
- Final reviewer did not rerun the full 613-test suite, but reviewed the
  controller-provided full verification evidence and ran targeted PR184 tests.

