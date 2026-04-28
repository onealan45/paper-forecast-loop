# PR6 Strategy Card And Experiment Registry Review

**日期：** 2026-04-28
**Reviewer：** independent subagent `Socrates`
**範圍：** `codex/strategy-card-experiment-registry`
**結論：** APPROVED

## First Pass Blocking Finding

### [P1] Trial lifecycle can exhaust budget before final failed result

Reviewer 發現 `record_experiment_trial()` 原本把每個既有狀態都算成 consumed
trial。因為 CLI 允許 `PENDING` / `RUNNING`，同一個 `trial_index=1` 在
`max_trials=1` 下先記 `PENDING`，再記最終 `FAILED` 時，最終失敗會被改寫成
`ABORTED/trial_budget_exhausted`，導致真正的失敗結果與 `failure_reason` 被吞掉。

## Fix

修正方向：

- 新增 regression test：
  `test_pending_trial_does_not_exhaust_budget_before_final_result`
- budget accounting 改成只計算 distinct finalized `trial_index`。
- `PENDING` / `RUNNING` lifecycle rows 不消耗 budget。
- 同一 trial 的 final `FAILED` / `ABORTED` / `INVALID` / `PASSED` 可以被記錄，
  不會因先前 pending lifecycle row 被誤判為 over budget。

## Second Pass Result

Reviewer second pass 回覆：

> APPROVED

Non-blocking note:

- `PENDING` / `RUNNING` rows 仍可在 budget exhausted 後被記錄；它們不消耗
  budget，final outcome 才會變成 `ABORTED`。這符合本次 lifecycle 修正，但未來
  runner 應避免在最新 budget snapshot 已 `EXHAUSTED` 時開始新工作。

## Verification Evidence

Main session fresh verification after fix:

```powershell
python -m pytest tests\test_experiment_registry.py tests\test_sqlite_repository.py -q
```

Result: `13 passed`

```powershell
python -m pytest -q
```

Result: `261 passed`

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
```

Result: passed

```powershell
python .\run_forecast_loop.py --help
```

Result: passed; help includes `register-strategy-card` and
`record-experiment-trial`.

```powershell
git diff --check
```

Result: exit 0; LF/CRLF warnings only.

## Merge Recommendation

Approved for PR once final gate passes again after this review archive is added.
