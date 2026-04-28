# Autonomous Alpha Factory Master Decision

**日期基準：** 2026-04-28  
**來源：** ChatGPT Pro master decision brief  
**狀態：** Repo execution contract after M7A  

## Summary

M7A 的方向正確，但它只建立了證據 artifact、storage parity、以及
health-check integrity 檢查。它還不是能提升策略品質的情報引擎。

接下來的 repo 方向不是繼續擴 broker/testnet，也不是先做 UI polish。
第一優先順序是建立 **Autonomous Alpha Factory** 的研究與預測能力：

- 先讓 repo 可審查、可維護、適合 subagent 協作。
- 再完成 source / event / market reaction / historical edge / decision
  integration 這條 Alpha Evidence Engine。
- 接著加入 strategy registry、experiment registry、locked evaluation、
  paper-shadow learning、leaderboard、operator digest、strategy-visible UX。

核心原則保持不變：

> 放開策略搜尋空間，鎖死評估流程。

Codex 可以提出更多策略、研究更多資料、使用更多工具、做更多模擬；但
evaluation protocol、holdout、trial budget、cost model、gates、leaderboard
rule 不可以在看完結果後被調整。

## Immediate Priority

下一個 PR 必須是 **PR0 - Reviewability And Formatting Gate**。

PR0 是 behavior-preserving cleanup，不應新增策略邏輯。它的目標是讓後續
M7B-M7F 能在可讀、可 review、可定位錯誤的程式碼上開發。

PR0 必須做到：

- 重新格式化病態長單行 Python source 和 test。
- 不改 CLI、artifact schema、模型行為、測試期待值。
- 加上輕量 reviewability guard，例如 `.py` source line 超過 1000 字元時
  fail，必要時排除明確 generated file。
- 更新 formatter / reviewability policy。
- 由獨立 reviewer subagent review，不能 self-review。
- 將 final review 歸檔到 `docs/reviews/`。

## Required PR Sequence

接下來按這個順序走；除非文件、測試、reviewer 都能證明某階段已完成，否則
不要跳過。

| PR | Name | Goal |
|---|---|---|
| PR0 | Reviewability And Formatting Gate | 先修可審查性，不改行為。 |
| PR1 | M7B Source Registry And Source Document Import | 建立 source registry 與 fixture/importable source document layer。 |
| PR2 | M7C Event Reliability | 做 canonical event normalization、dedupe、entity/symbol linking、source reliability gate。 |
| PR3 | M7D Market Reaction | 做 already-priced / market reaction gate，避免把已反映價格的事件當新 alpha。 |
| PR4 | M7E Historical Edge | 做 event-family historical edge evaluation，確認事件類型是否有 after-cost edge。 |
| PR5 | M7F Decision Integration | 將 event-derived evidence 串進 `decision.py` / `research_gates.py`，但不得繞過既有 gates。 |
| PR6 | Strategy Card And Experiment Registry | 建立 strategy card、experiment registry、trial budget、failed/aborted experiment persistence。 |
| PR7 | Locked Evaluation And Leaderboard Gates | 鎖 split manifest、holdout、cost model、baseline suite、anti-overfit gates、leaderboard rules。 |
| PR8 | Paper-Shadow Outcome Learning | 加入 outcome scoring、failure attribution、strategy update / retire / quarantine。 |
| PR9 | Research/Paper Autopilot Loop | 串起 agenda -> strategy -> data -> backtest -> gates -> paper decision -> outcome -> revision。 |
| PR10 | Strategy-Visible UX | UX 優先顯示 strategy hypothesis、evidence gates、backtest、leaderboard、failure attribution。 |
| PR11 | Codex Governance Docs And Prompts | 補 controller artifacts、worker prompts、acceptance docs、Windows autopilot runbook。 |

## ChatGPT Pro Controller Model

不要在 repo 裡假裝有一個線上的 ChatGPT Pro Controller runtime service。
ChatGPT Pro 是實際工作流程中的高層決策者；repo 要保存的是決策與工作契約，
不是虛構的產品服務。

Repo 應使用 artifact / docs 表達 controller decision：

- controller decision artifact
- research agenda
- worker prompt
- acceptance gate
- operator digest
- review archive

最小 controller decision artifact 應包含：

- `controller_decision_id`
- `created_at`
- `decision_type`
- `scope`
- `decision`
- `rationale`
- `allowed_worker_roles`
- `blocked_actions`
- `affected_files`
- `acceptance_summary`

這個 artifact 之後可以落成 JSONL / SQLite storage；現在先以本文件作為權威
決策紀錄。

## Worker And Review Rules

後續 agentic 工作應以小角色集分工，避免單一 agent 同時實作、驗證、review
自己的工作。

建議角色：

- `explorer`: 查 repo、列缺口，不改檔。
- `formatter`: 只做可讀性/格式化，不改行為。
- `feature`: 實作有明確 acceptance criteria 的 bounded feature。
- `data`: 建 ingestion、source registry、fixture、provider audit。
- `backtester`: 實作 backtest、validation、edge evaluation。
- `verifier`: 跑測試、補 invariant，不做大型 production rewrite。
- `reviewer`: 找 blocker、missing tests、gate bypass、overclaim、leakage、secret/live-trading leak。
- `docs`: 文件只反映已實作事實，不捏造功能。
- `ui`: 顯示 strategy/evidence/leaderboard，不隱藏 gate failure。
- `infra`: CI、scheduler docs、local runbook、portable config docs。

Review policy：

- reviewer 必須是獨立 subagent。
- reviewer 不得寫 production code。
- final review 必須歸檔到 `docs/reviews/`。
- 不允許 self-review 當作 merge gate。

## Evidence Engine Rules

M7B-M7F 的目標是把 M7A artifact foundation 變成能影響決策品質的 engine。

任何 event/news/macro/on-chain/fundamental evidence 進入 BUY/SELL 前，至少要
通過：

- source document import 與 source registry；
- timestamp, source id, hash, license/rate-limit/availability metadata；
- canonical event normalization 與 dedupe；
- source reliability gate；
- market reaction / already-priced gate；
- historical edge gate；
- point-in-time feature snapshot；
- baseline / research / risk / health gates。

LLM narrative 或自然語言摘要本身不得直接產生 BUY/SELL。它可以產生 hypothesis、
strategy card、research agenda、或 feature proposal，但 directional decision
必須由 locked evaluation 和可追溯 artifact 支撐。

## Evaluation Rules

策略搜尋空間可以放大，但評估流程必須鎖住。

後續 stages 必須逐步建立：

- fixed dataset snapshots；
- split manifests；
- no-lookahead / leakage checks；
- trial budget；
- failed / aborted / invalid experiment persistence；
- transaction cost and slippage model；
- baseline suite；
- walk-forward；
- locked holdout；
- anti-overfit metrics or placeholders；
- paper-shadow outcome scoring；
- failure attribution；
- promotion / demotion / quarantine rules；
- leaderboard hard gates。

Candidate strategy 不得因為單次漂亮 backtest 就被提升。弱證據、樣本不足、
已反映價格、negative after-cost edge、overfit risk、provider distortion、
health/risk block 都應導致 HOLD、REDUCE_RISK、STOP_NEW_ENTRIES、quarantine、
或 no ranking。

## Boundary Statement

目前階段允許自動化：

- research；
- backtest；
- simulation；
- paper-shadow；
- sandbox-test；
- strategy generation；
- strategy revision；
- data-source research；
- artifact generation；
- repair request generation；
- PR creation and review。

目前階段不允許：

- real broker live endpoint；
- real order submission；
- real capital movement；
- live API key handling in source；
- committed secrets；
- automatic promotion to real-money trading；
- evaluation gate weakening after seeing results。

這是當前執行邊界，不是永久產品邊界。未來如果使用者明確要求自動交易，必須
另開獨立設計階段，先處理 live-readiness、broker safety、secrets、operator
approval、audit、legal/risk assumptions，而不能從當前研究 loop 偷渡。

## Documentation Language Rule

使用者可讀內容使用台灣繁體中文：

- README user-facing sections；
- PRD；
- architecture docs；
- runbooks；
- reviews；
- operator digest；
- dashboard/user-facing labels。

維持英文的內容：

- code；
- CLI names；
- artifact names；
- schema fields；
- file names；
- variable names。

## Standard Verification

每個後續 PR 至少跑：

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

涉及 CLI / storage / dashboard / ingestion / backtest 的 PR 需要加 milestone-specific
smoke tests。

## Acceptance For Following This Decision

後續工作只有符合以下條件才算有遵守本決策：

- PR0 先完成，除非 reviewer 證明 repo 已可審查。
- M7B-M7F 優先於更多 broker/testnet/UI polish。
- M7A 的 deferred work 不再被描述成已完成 intelligence engine。
- ChatGPT Pro Controller 只以 artifact/docs/prompts 表達，不假裝成 runtime service。
- 策略搜尋可以變廣，但 evaluation gate 不能事後移動。
- UX 逐步把 strategy hypothesis、evidence、backtest、failure attribution、leaderboard 放到一線。
- review 必須由獨立 reviewer subagent 完成。
- 不提交 `.codex/`、`paper_storage/`、`reports/`、`output/`、`.env`、secrets。
