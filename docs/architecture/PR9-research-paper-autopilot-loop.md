# PR9 Research / Paper Autopilot Loop

**狀態：** implemented in PR9
**日期：** 2026-04-28
**範圍：** Alpha Factory loop-level audit records

## 目的

PR9 把 PR6-PR8 的 strategy / evaluation / leaderboard / paper-shadow artifacts
串成一個可審查的研究循環紀錄：

```text
agenda -> strategy card -> experiment trial -> locked evaluation -> leaderboard
-> paper decision -> paper-shadow outcome -> next research action
```

這不是完整 autonomous strategy generator，也不是 scheduler。它先建立 loop artifact，
讓下一階段可以把策略修正、重新測試、淘汰與候選提升流程接上。

## 新 Artifacts

### `research_agendas.jsonl`

每列記錄一個研究 agenda：

- agenda id;
- created at;
- symbol;
- title;
- hypothesis;
- priority;
- status;
- target strategy family;
- linked strategy card ids;
- expected artifacts;
- acceptance criteria;
- blocked actions;
- decision basis.

### `research_autopilot_runs.jsonl`

每列記錄一次研究閉環：

- run id;
- created at;
- symbol;
- agenda id;
- strategy card id;
- experiment trial id;
- locked evaluation id;
- leaderboard entry id;
- strategy decision id;
- paper-shadow outcome id;
- ordered steps;
- loop status;
- next research action;
- blocked reasons;
- decision basis.

## Loop Status

第一版狀態規則：

- missing or blocked evidence -> `BLOCKED` / `REPAIR_EVIDENCE_CHAIN`;
- no paper-shadow outcome yet -> `WAITING_FOR_SHADOW_OUTCOME`;
- `PROMOTION_READY` outcome -> `READY_FOR_OPERATOR_REVIEW` /
  `OPERATOR_REVIEW_FOR_PROMOTION`;
- `RETIRE` or `REVISE` outcome -> `REVISION_REQUIRED` /
  `CREATE_REVISION_AGENDA`;
- `QUARANTINE` outcome -> `QUARANTINED` / `QUARANTINE_STRATEGY_CARD`.

## CLI

Create a research agenda:

```powershell
python .\run_forecast_loop.py create-research-agenda --storage-dir .\paper_storage\manual-research --symbol BTC-USD --title "Trend candidate" --hypothesis "Trend continuation should survive shadow validation." --strategy-family trend_following --strategy-card-id strategy-card:example
```

Record the linked autopilot loop:

```powershell
python .\run_forecast_loop.py record-research-autopilot-run --storage-dir .\paper_storage\manual-research --agenda-id research-agenda:example --strategy-card-id strategy-card:example --experiment-trial-id experiment-trial:example --locked-evaluation-id locked-evaluation:example --leaderboard-entry-id leaderboard-entry:example --strategy-decision-id decision:example --paper-shadow-outcome-id paper-shadow-outcome:example
```

## Storage And Health

PR9 supports:

- JSONL save/load;
- SQLite migration/export/db-health parity;
- duplicate id health checks;
- missing strategy card / trial / locked evaluation / leaderboard / decision /
  paper-shadow outcome health findings.

## Deferred

PR9 does not implement:

- automatic strategy generation;
- automatic strategy-card mutation;
- scheduler orchestration;
- dashboard redesign;
- broker execution;
- live order submission.

Next stage should make the UX strategy-visible and then add strategy revision
workers that consume `research_autopilot_runs.jsonl` and create new candidate
strategy cards.
