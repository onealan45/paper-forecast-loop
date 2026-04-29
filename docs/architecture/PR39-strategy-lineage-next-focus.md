# PR39 Strategy Lineage Next Research Focus

## Purpose

PR38 made strategy lineage verdicts readable. PR39 turns that verdict into a
specific next research focus so the user can see what the self-evolving loop
should inspect next without manually interpreting counts and failure labels.

## Scope

PR39 adds `next_research_focus` to `StrategyLineageSummary`.

The field is deterministic and read-only. It is derived from:

- `performance_verdict`
- `latest_recommended_strategy_action`
- `primary_failure_attribution`

It does not mutate strategy cards, promote strategies, schedule execution,
submit orders, or write runtime artifacts.

## Rules

- `證據不足`: `先補齊 paper-shadow outcome 證據，再判斷修正方向。`
- `QUARANTINE_STRATEGY`: `停止加碼此 lineage，優先研究 <failure> 的修正或新策略。`
- `REVISE_STRATEGY` or weak/worsening verdict: `優先修正 <failure>，再重跑 locked retest。`
- Improving verdict: `保留此 lineage，下一步驗證改善是否能跨樣本持續。`
- Otherwise: `維持觀察，等待更多 paper-shadow outcome。`

## UX

Dashboard and operator console now render `下一步研究焦點` after `表現結論`
and before raw `表現軌跡`. The goal is to make the strategy loop read as:

1. What happened?
2. Is it improving or worsening?
3. What should the research loop inspect next?
4. What raw outcome rows support that conclusion?

## Verification

Focused:

```powershell
python -m pytest tests\test_strategy_lineage.py tests\test_dashboard.py tests\test_operator_console.py -q
```

Final:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
git ls-files .codex paper_storage reports output .env
```
