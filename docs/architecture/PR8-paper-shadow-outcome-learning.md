# PR8 Paper-Shadow Outcome Learning

**狀態：** implemented in PR8
**日期：** 2026-04-28
**範圍：** Alpha Factory candidate feedback layer

## 目的

PR8 把 PR7 leaderboard candidate 接到後續模擬結果。核心規則是：

> 候選策略通過 locked gates 之後，仍要用 paper-shadow outcome 觀察後續結果；
> 結果不佳時要留下 failure attribution，而不是只保留成功故事。

這不是完整 autopilot，也不會自動改 strategy card 狀態。它先建立 outcome artifact，
讓下一階段可以把 agenda -> strategy -> evaluation -> paper decision -> outcome ->
revision 串成閉環。

## 新 Artifact

### `paper_shadow_outcomes.jsonl`

每列記錄一個 leaderboard entry 的 shadow window 結果：

- leaderboard entry id;
- locked evaluation id;
- strategy card id;
- experiment trial id;
- symbol;
- window start / end;
- observed return;
- benchmark return;
- excess return after costs;
- max adverse excursion;
- turnover;
- outcome grade;
- failure attribution labels;
- recommended promotion stage;
- recommended strategy action;
- blocked reasons;
- notes;
- decision basis.

## Outcome Rules

第一版規則刻意簡單，重點是可稽核 feedback loop：

- blocked / non-rankable leaderboard entry -> `PAPER_SHADOW_BLOCKED` and
  `QUARANTINE`;
- positive excess return with no risk breach -> `PASS`,
  `PAPER_SHADOW_PASSED`, `PROMOTION_READY`;
- negative excess return -> `FAIL`, `PAPER_SHADOW_FAILED`, `RETIRE`;
- large adverse excursion or severe negative excess -> `QUARANTINE`;
- high turnover -> failure attribution, not promotion-ready.

## CLI

Record a paper-shadow outcome:

```powershell
python .\run_forecast_loop.py record-paper-shadow-outcome --storage-dir .\paper_storage\manual-research --leaderboard-entry-id leaderboard-entry:example --window-start 2026-04-28T00:00:00+00:00 --window-end 2026-04-29T00:00:00+00:00 --observed-return 0.05 --benchmark-return 0.01
```

Optional:

- `--max-adverse-excursion`
- `--turnover`
- `--created-at`
- `--note`

## Health Checks

Health-check now detects:

- duplicate paper-shadow outcome ids;
- missing leaderboard entry;
- missing locked evaluation;
- missing strategy card;
- missing experiment trial;
- symbol mismatch between outcome and leaderboard entry.

## Storage

PR8 preserves the repo's current dual-storage direction:

- JSONL remains the default audit artifact path.
- SQLite repository supports save/load, JSONL migration, export, and db-health
  counts for `paper_shadow_outcomes`.

## Deferred

PR8 does not implement:

- automatic strategy-card mutation;
- automatic candidate promotion;
- full research autopilot loop;
- dashboard leaderboard/outcome UX;
- scheduled paper-shadow monitoring;
- broker execution;
- real order submission.

Next stage should connect paper-shadow outcomes into an autopilot research loop
that proposes strategy revisions, retests them, and keeps failed hypotheses
visible.
