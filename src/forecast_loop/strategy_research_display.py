from __future__ import annotations

from forecast_loop.models import PaperShadowOutcome, ResearchAutopilotRun, StrategyCard


_FAILURE_ATTRIBUTION_LABELS = {
    "breakout_reversed": "突破後反轉",
    "drawdown_breach": "回撤超標",
    "locked_evaluation_not_rankable": "鎖定評估不可排名",
    "negative_excess_return": "負超額報酬",
    "paper_shadow_failed": "paper-shadow 失敗",
    "turnover_breach": "換手率超標",
    "weak_baseline_edge": "基準優勢不足",
}

_RESEARCH_ACTION_LABELS = {
    "COMPARE_FRESH_SAMPLE_EDGE": "比較新樣本優勢",
    "CREATE_REVISION_AGENDA": "建立修訂研究議程",
    "IGNORE_FOR_CURRENT_LINEAGE": "略過目前 lineage",
    "OPERATOR_REVIEW_FOR_PROMOTION": "等待操作員檢視升級",
    "PROMOTION_READY": "可進入下一階段",
    "PROMOTE_TO_PAPER": "升級到 paper 模擬",
    "QUARANTINE": "隔離策略",
    "QUARANTINE_STRATEGY": "隔離策略",
    "QUARANTINE_STRATEGY_CARD": "隔離策略卡",
    "REPAIR_EVIDENCE_CHAIN": "修復證據鏈",
    "RETEST_REVISION": "重新測試修訂版",
    "RETIRE": "淘汰策略",
    "REVISE_STRATEGY": "修訂策略",
    "UPDATE_LINEAGE_VERDICT": "更新 lineage 判定",
}


def build_strategy_research_conclusion(
    *,
    card: StrategyCard | None,
    outcome: PaperShadowOutcome | None,
    autopilot: ResearchAutopilotRun | None,
) -> str:
    if card is None:
        return "目前沒有策略卡，無法形成策略研究結論。"

    conclusion = f"目前策略 {card.strategy_name}"
    if outcome is None:
        next_action = autopilot.next_research_action if autopilot else "n/a"
        return f"{conclusion}：尚未有 paper-shadow 結果；下一步 {format_research_action(next_action)}。"

    parts = [f"paper-shadow {outcome.outcome_grade}"]
    if outcome.excess_return_after_costs is not None:
        parts.append(f"after-cost excess {_format_percent(outcome.excess_return_after_costs)}")
    if outcome.failure_attributions:
        parts.append(f"失敗歸因 {format_failure_attributions(outcome.failure_attributions)}")

    next_action = autopilot.next_research_action if autopilot else outcome.recommended_strategy_action
    return f"{conclusion}：{'，'.join(parts)}；下一步 {format_research_action(next_action)}。"


def format_failure_attributions(attributions: list[str]) -> str:
    return ", ".join(_format_failure_attribution(attribution) for attribution in attributions)


def format_research_action(action: str) -> str:
    label = _RESEARCH_ACTION_LABELS.get(action)
    if label is None:
        return action
    return f"{label} ({action})"


def _format_failure_attribution(attribution: str) -> str:
    label = _FAILURE_ATTRIBUTION_LABELS.get(attribution)
    if label is None:
        return attribution
    return f"{label} ({attribution})"


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"
