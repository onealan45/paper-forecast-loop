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

_OUTCOME_GRADE_LABELS = {
    "BLOCKED": "已阻擋",
    "FAIL": "失敗",
    "INSUFFICIENT": "證據不足",
    "PASS": "通過",
}

_PROMOTION_STAGE_LABELS = {
    "BLOCKED": "已阻擋",
    "CANDIDATE": "候選策略",
    "PAPER_SHADOW_BLOCKED": "paper-shadow 已阻擋",
    "PAPER_SHADOW_FAILED": "paper-shadow 失敗",
    "PAPER_SHADOW_PASSED": "paper-shadow 通過",
    "PROMOTION_READY": "可進入下一階段",
}

_STRATEGY_CARD_STATUS_LABELS = {
    "ACTIVE": "啟用",
    "DRAFT": "草稿",
    "QUARANTINED": "隔離中",
    "RETIRED": "已淘汰",
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

    parts = [f"paper-shadow {format_outcome_grade(outcome.outcome_grade)}"]
    if outcome.excess_return_after_costs is not None:
        parts.append(f"扣成本超額報酬 {_format_percent(outcome.excess_return_after_costs)}")
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


def format_outcome_grade(grade: str) -> str:
    label = _OUTCOME_GRADE_LABELS.get(grade)
    if label is None:
        return grade
    return f"{label} ({grade})"


def format_promotion_stage(stage: str) -> str:
    label = _PROMOTION_STAGE_LABELS.get(stage)
    if label is None:
        return stage
    return f"{label} ({stage})"


def format_strategy_card_status(status: str) -> str:
    label = _STRATEGY_CARD_STATUS_LABELS.get(status)
    if label is None:
        return status
    return f"{label} ({status})"


def _format_failure_attribution(attribution: str) -> str:
    label = _FAILURE_ATTRIBUTION_LABELS.get(attribution)
    if label is None:
        return attribution
    return f"{label} ({attribution})"


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"
