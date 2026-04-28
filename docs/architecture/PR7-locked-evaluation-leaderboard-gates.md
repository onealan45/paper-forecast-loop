# PR7 Locked Evaluation And Leaderboard Gates

**狀態：** implemented in PR7
**日期：** 2026-04-28
**範圍：** Alpha Factory hard-gate foundation

## 目的

PR7 把 PR6 的 strategy card / experiment trial registry 接到固定評估與
leaderboard gate。核心規則是：

> 沒有通過 hard gates，就沒有 `alpha_score`，也不能 rank。

這不是完整的統計研究套件；CPCV、PBO、DSR、bootstrap 等深度統計仍是後續工作。
PR7 先建立固定 artifact contract，讓後續統計指標有地方落地，並阻止單次漂亮
backtest 直接進 leaderboard。

## 新 Artifacts

### `split_manifests.jsonl`

每列記錄一份 locked split manifest：

- train window
- validation window
- holdout window
- embargo hours
- strategy card id
- dataset id
- status
- locked by

Split manifest 是評估流程的一部分，不應在看完結果後改動。

### `cost_model_snapshots.jsonl`

每列記錄評估時使用的成本假設：

- fee bps
- slippage bps
- max turnover
- max drawdown
- baseline suite version

這讓 leaderboard 不會只根據未扣成本的 raw backtest 排名。

### `locked_evaluation_results.jsonl`

每列記錄一個 experiment trial 的 hard-gate 結果：

- linked strategy card
- linked experiment trial
- linked split manifest
- linked cost model
- linked baseline
- linked backtest
- linked walk-forward validation
- optional linked event-edge evaluation
- blocked reasons
- gate metrics
- `rankable`
- `alpha_score`

若任何 hard gate 失敗，`rankable=false` 且 `alpha_score=null`。

### `leaderboard_entries.jsonl`

每列是 leaderboard 視角的 candidate entry。失敗 entry 也會保留，但 promotion
stage 是 `BLOCKED`。

## Hard Gates

PR7 的第一版 hard gates：

- strategy card exists
- experiment trial exists and status is `PASSED`
- split manifest exists and status is `LOCKED`
- cost model exists and status is `LOCKED`
- baseline exists, sample size sufficient, model edge positive, evidence grade not weak
- holdout/backtest strategy return beats benchmark return
- drawdown does not exceed cost model limit
- turnover does not exceed cost model limit
- walk-forward average excess return positive
- walk-forward overfit risk flags empty
- optional event-edge evaluation passes if supplied

只有全部通過才計算 deterministic `alpha_score`。

## CLI

Create locked split and cost snapshots:

```powershell
python .\run_forecast_loop.py lock-evaluation-protocol --storage-dir .\paper_storage\manual-research --strategy-card-id strategy-card:example --dataset-id research-dataset:example --symbol BTC-USD --train-start 2026-01-01T00:00:00+00:00 --train-end 2026-02-01T00:00:00+00:00 --validation-start 2026-02-02T00:00:00+00:00 --validation-end 2026-03-01T00:00:00+00:00 --holdout-start 2026-03-02T00:00:00+00:00 --holdout-end 2026-04-01T00:00:00+00:00
```

Evaluate leaderboard eligibility:

```powershell
python .\run_forecast_loop.py evaluate-leaderboard-gate --storage-dir .\paper_storage\manual-research --strategy-card-id strategy-card:example --trial-id experiment-trial:example --split-manifest-id split-manifest:example --cost-model-id cost-model:example --baseline-id baseline:example --backtest-result-id backtest-result:example --walk-forward-validation-id walk-forward:example
```

## Deferred

PR7 不做：

- CPCV implementation
- probability of backtest overfitting
- deflated Sharpe ratio
- bootstrap confidence intervals
- paper-shadow learning
- strategy auto-generation
- UX leaderboard surface
- live trading or real broker work

下一階段應把 paper-shadow outcome learning 接上，使 leaderboard entry 能被後續
實盤前模擬結果降級、隔離或淘汰。
