# PR174: AGENTS Review Quality Rules

## 背景

Repo 已經要求 subagent review、角色分工、以及 review archive。最近幾個 PR
顯示這條規則需要更可執行的細節：

- final reviewer prompt 必須有足夠上下文，讓 reviewer 能獨立判斷。
- reviewer scope 應從 changed files 開始，但不能只看 changed files。
- controller 的驗證結果是 evidence，不是 reviewer 可以直接照抄的 proof。
- residual risks 必須明確寫出來，不能被 controller 或 reviewer 靜默略過。
- 產生新 reviewer 前，應先整理並關閉 stale subagents，避免撞到 worker 上限。

這份 PR 把上述協作規則寫進 `AGENTS.md`，讓未來 autonomous work 使用同一個
review bar。

## 決策

`AGENTS.md` 現在明確要求：

- substantive repo changes 的 review 只能由 subagent 做，範圍包含 code、
  tests、docs、instructions、automation rules。
- controller 可以協調 review、整理 reviewer findings、確認 review artifact
  存在，但不能 self-approve 自己的實質變更。
- reviewer 必須檢查 intent、compatibility、false positives、false
  negatives、severity semantics、test quality，以及 changed files 附近的相依
  code。
- verifier handoff 應包含精確 command evidence。
- docs 必須描述已實作行為與已知限制。
- artifact / research-quality changes 必須保留 traceability，且不得捏造未來
  market results、paper-shadow outcomes、或 evaluation evidence。

## 邊界

- 這是文件與協作規則變更，不改 runtime behavior、CLI behavior、schemas、或
  tests。
- 這不放寬目前邊界：不送出真實訂單、不移動真實資金、不提交 secrets。
- 這不限制研究、回測、模擬、strategy generation、或自我反思能力。

## 驗證

標準 gate：

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```
