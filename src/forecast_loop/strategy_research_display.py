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
        return f"{conclusion}：尚未有 paper-shadow 結果；下一步 {autopilot.next_research_action if autopilot else 'n/a'}。"

    parts = [f"paper-shadow {outcome.outcome_grade}"]
    if outcome.excess_return_after_costs is not None:
        parts.append(f"after-cost excess {_format_percent(outcome.excess_return_after_costs)}")
    if outcome.failure_attributions:
        parts.append(f"失敗歸因 {format_failure_attributions(outcome.failure_attributions)}")

    next_action = autopilot.next_research_action if autopilot else outcome.recommended_strategy_action
    return f"{conclusion}：{'，'.join(parts)}；下一步 {next_action}。"


def format_failure_attributions(attributions: list[str]) -> str:
    return ", ".join(_format_failure_attribution(attribution) for attribution in attributions)


def _format_failure_attribution(attribution: str) -> str:
    label = _FAILURE_ATTRIBUTION_LABELS.get(attribution)
    if label is None:
        return attribution
    return f"{label} ({attribution})"


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"
