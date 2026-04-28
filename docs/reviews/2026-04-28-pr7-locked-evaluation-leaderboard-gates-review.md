# PR7 Locked Evaluation And Leaderboard Gates Review

## Reviewer

- Reviewer: Helmholtz subagent
- Role: `docs/roles/reviewer.md`
- Scope: PR7 locked evaluation protocol, leaderboard hard gates, JSONL/SQLite parity, health-check links, CLI commands, docs, and tests.
- Date: 2026-04-28

## Initial Blocking Finding

### P1: Gate accepts mismatched evidence artifacts

`evaluate_leaderboard_gate` verified that the experiment trial belonged to the requested strategy card, but it did not verify that split, cost model, baseline, backtest, walk-forward, or optional event-edge artifacts belonged to the same trial/card/dataset/symbol. The reviewer reproduced an ETH trial using BTC artifacts from another card; the old implementation returned `rankable=True`, a positive `alpha_score`, and no blocked reasons.

Merge recommendation at this stage: **NOT APPROVED**.

## Fix Summary

- Added a regression test: `test_leaderboard_gate_blocks_mismatched_evidence_artifacts`.
- Added `_check_artifact_alignment` before rankability and alpha scoring.
- Required card/trial/evidence alignment for:
  - strategy card symbol membership
  - split strategy card, dataset, and symbol
  - cost model symbol
  - baseline symbol
  - trial backtest result id and backtest symbol
  - trial walk-forward validation id and walk-forward symbol
  - walk-forward backtest result membership
  - optional event-edge id and symbol
- Preserved the blocked leaderboard entry behavior: blocked candidates still write an entry, but `rankable=false` and `alpha_score=null`.

## Re-Review Result

Reviewer found no P1/P2 blocking findings after the fix. The reviewer manually smoked the original mismatch shape and confirmed it now returns:

- `passed=false`
- `rankable=false`
- `alpha_score=null`
- blocked reasons covering split/cost/baseline/backtest/walk-forward mismatch

Final recommendation: **APPROVED**.

## Non-Blocking Risk

- P3: lineage checks are still limited by the current artifact schema. Baseline and cost model alignment are primarily symbol/status based rather than full evidence-hash lineage. This is acceptable for PR7 hard-gate foundation and should be improved in a later research-lineage milestone.

## Verification

- `python -m pytest tests\test_locked_evaluation.py::test_leaderboard_gate_blocks_mismatched_evidence_artifacts -q` -> `1 passed`
- `python -m pytest tests\test_locked_evaluation.py tests\test_sqlite_repository.py tests\test_experiment_registry.py -q` -> `20 passed`
- `python -m pytest -q` -> `268 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> passed; LF/CRLF warnings only

## Automation And Safety Notes

- No runtime or secrets files were part of the PR7 review scope.
- No live trading path was added.
- PR7 remains research/simulation focused: it prevents unrelated evidence from promoting a strategy candidate into the leaderboard.
