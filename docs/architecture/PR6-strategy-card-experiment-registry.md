# PR6 Strategy Card And Experiment Registry

**狀態：** implemented in PR6
**日期：** 2026-04-28
**範圍：** Alpha Factory registry foundation

## 目的

PR6 的目的不是直接提升 BUY/SELL，也不是建立 leaderboard。它先補上研究
工廠需要的最小可稽核註冊層：

- 策略假說要變成 versioned strategy card。
- 每張 strategy card 要有 trial budget。
- 每次 experiment trial 都要落地，包括 `FAILED`、`ABORTED`、`INVALID`。

這解決 selection bias 的第一個資料問題：不能只留下成功實驗，也不能讓超出
budget 的研究嘗試消失。

## 新 Artifacts

### `strategy_cards.jsonl`

每列是一張策略卡，欄位包含：

- `card_id`
- `strategy_name`
- `strategy_family`
- `version`
- `status`
- `symbols`
- `hypothesis`
- `signal_description`
- `entry_rules`
- `exit_rules`
- `risk_rules`
- `parameters`
- `data_requirements`
- linked feature / backtest / walk-forward / event-edge ids
- `parent_card_id`
- `author`
- `decision_basis`

Strategy card 是研究假說與策略規則的登錄，不是交易授權。

### `experiment_budgets.jsonl`

每列是 strategy card 的 trial budget snapshot，欄位包含：

- `budget_id`
- `strategy_card_id`
- `max_trials`
- `used_trials`
- `remaining_trials`
- `status`

Budget snapshot 讓後續 reviewer 可以看到 trial search 是否已超出約束。

### `experiment_trials.jsonl`

每列是一個 experiment trial，欄位包含：

- `trial_id`
- `strategy_card_id`
- `trial_index`
- `status`
- `symbol`
- optional dataset / backtest / walk-forward / event-edge ids
- `seed`
- `prompt_hash`
- `code_hash`
- `parameters`
- `metric_summary`
- `failure_reason`
- `started_at`
- `completed_at`

`PASSED`、`FAILED`、`ABORTED`、`INVALID` 都會保留。若 trial budget 已耗盡，
系統仍會寫入一列 `ABORTED` trial，並將
`failure_reason=trial_budget_exhausted`。

## CLI

Register a strategy card:

```powershell
python .\run_forecast_loop.py register-strategy-card --storage-dir .\paper_storage\manual-research --name "MA trend BTC" --family trend_following --version v1 --symbol BTC-USD --hypothesis "BTC trend continuation after moving-average confirmation." --signal-description "Fast moving average above slow moving average." --entry-rule "Enter long when fast_ma > slow_ma." --exit-rule "Exit when fast_ma <= slow_ma." --risk-rule "Max position 10% during research simulation." --parameter fast_window=3 --parameter slow_window=7 --data-requirement market_candles:BTC-USD:1h
```

Record an experiment trial:

```powershell
python .\run_forecast_loop.py record-experiment-trial --storage-dir .\paper_storage\manual-research --strategy-card-id strategy-card:example --trial-index 1 --status FAILED --symbol BTC-USD --max-trials 20 --failure-reason negative_after_cost_edge --metric excess_return=-0.02
```

## Health And Storage

`health-check` 現在會檢查：

- duplicate `card_id`
- duplicate `budget_id`
- duplicate `trial_id`
- strategy card parent link
- strategy card linked feature / backtest / walk-forward / event-edge ids
- experiment budget linked strategy card
- experiment trial linked strategy card
- experiment trial linked dataset / backtest / walk-forward / event-edge ids

SQLite migration、SQLite health、JSONL export 也包含三種新 artifact。

## 明確不做

PR6 不做：

- leaderboard ranking
- locked split manifest
- holdout policy
- paper-shadow outcome learning
- automatic strategy generation
- strategy promotion
- decision gate relaxation
- live broker / live order path

下一階段應在 PR7 建立 locked evaluation 和 leaderboard gates，讓 strategy card
與 experiment trial 能進入固定評估流程。
