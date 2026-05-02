# PR145 Decision-Blocker Backtest Window Review

## Reviewer

- Subagent: `019de78d-8a0b-7612-ab0c-8945428278bf`
- Role: final reviewer
- Scope: PR145 diff only

## Initial Result

`CHANGES_REQUESTED`

### P1 Finding

The first implementation emitted a ready `backtest --start --end` command after
the planner selected candles with `timestamp <= now` and `imported_at <= now`.
The backtest runtime reloads every same-symbol candle in the timestamp span and
does not pin `imported_at` or candle identity, so later-imported or revised
candles could change the supposedly conservative plan-time window.

Required fix:

- pin candle ids/source/as-of cutoff in the command/runtime, or
- keep the task blocked until the selected window can be faithfully replayed.

## Fix Applied

- Changed backtest planning to fail closed when same-symbol candles cover a
  window but the current CLI cannot pin the plan-time as-of candle set.
- The task now reports `blocked_reason=missing_backtest_asof_replay` and
  `missing_inputs=["backtest_asof_replay"]`.
- Updated executor regression coverage so blocked backtest writes no
  `AutomationRun`.
- Updated README, PRD, and PR145 architecture docs to describe the fail-closed
  replay blocker.

## Final Result

`APPROVED`

Blocking findings: none.

Residual risks:

- Backtest completion is still intentionally coarse: any same-symbol
  `backtest_result` at or after the agenda completes `run_backtest`, without
  matching a blocker-specific window or replay manifest. This matches PR145
  semantics but remains a future tightening point.
- Walk-forward still emits a ready command from the same `_candle_window`
  cutoff logic; this is unchanged from PR144 behavior and remains separate from
  the newly fail-closed backtest path.

## Verification Observed

- `python -m pytest tests\test_decision_research_plan.py tests\test_decision_research_executor.py tests\test_backtest.py tests\test_walk_forward.py -q`
  -> `30 passed`
- `python -m pytest -q`
  -> `543 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  -> passed
- `python .\run_forecast_loop.py --help`
  -> passed
- `git diff --check`
  -> passed with LF/CRLF warnings only
- Active storage read-only plan check showed `run_backtest` blocked with
  `missing_backtest_asof_replay` and `run_walk_forward_validation` ready.
