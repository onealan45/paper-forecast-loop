# PR177: Digest Symbol Integrity Regression Tests

## Context

PR176 added symbol-integrity checks for latest `StrategyResearchDigest`
evidence links. The final reviewer approved the implementation and suggested
two non-blocking regression tests:

- old digest symbol mismatch should not trigger the operational health gate;
- lowercase symbol values should still match case-insensitively.

## Decision

This PR adds those two tests without changing production behavior.

## Verification

```powershell
python -m pytest tests\test_m1_strategy.py::test_health_check_ignores_non_latest_strategy_research_digest_symbol_mismatches tests\test_m1_strategy.py::test_health_check_treats_strategy_research_digest_symbol_matches_case_insensitively -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```
