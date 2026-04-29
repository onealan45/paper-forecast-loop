# PR25 Revision Retest Leaderboard Gate Executor Review

## Reviewer Source

- Reviewer subagent: Carson
- Role: `roles/reviewer.md`
- Model: `gpt-5.5`
- Reasoning effort: `xhigh`
- Scope: PR25 diff only; no file edits by reviewer.

## Reviewed Scope

- `execute-revision-retest-next-task` support for `evaluate_leaderboard_gate`.
- Whitelist boundary: no shell/subprocess, no arbitrary `command_args`.
- Evidence linkage from plan-linked PASSED trial, split, cost model, baseline,
  backtest, and walk-forward IDs.
- `record_paper_shadow_outcome` remains blocked.
- `baseline.model_edge is None` fails closed as blocked leaderboard evidence.
- Tests and docs alignment.

## Initial Finding

### P2: Baseline `model_edge=None` fail-closed path lacked explicit regression coverage

The reviewer confirmed the implementation avoided shell/subprocess execution and
kept `record_paper_shadow_outcome` blocked, but requested explicit regression
coverage for the `model_edge=None` path. The PR25 doc claimed weak baseline edge
handling was covered, while the initial tests only proved the executor/CLI path
and unsupported paper-shadow transition.

Required regression:

- Use the plan-linked baseline with `model_edge=None`.
- Execute `evaluate_leaderboard_gate`.
- Assert no exception.
- Assert `LockedEvaluationResult.rankable is False`.
- Assert `LeaderboardEntry.rankable is False`.
- Assert both blocked reason lists contain `baseline_edge_missing`.

## Resolution

The executor-level leaderboard gate test now asserts:

- locked evaluation is not rankable;
- leaderboard entry is not rankable;
- both artifacts contain `baseline_edge_missing`;
- gate metrics preserve `model_edge` as `None`;
- the after-plan advances to `record_paper_shadow_outcome`.

## Verification

Commands run after resolution:

```powershell
python -m pytest .\tests\test_research_autopilot.py -k "leaderboard_gate_next_task or unsupported_ready_task" -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Results:

- Focused tests: `3 passed, 46 deselected`.
- Full tests: `349 passed`.
- Compileall: passed.
- CLI help: passed.
- Diff check: passed with Windows LF/CRLF warnings only.

## Final Reviewer Result

`APPROVED`

No remaining blocking findings were reported.
