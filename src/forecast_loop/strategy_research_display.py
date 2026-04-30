from __future__ import annotations

from forecast_loop.models import PaperShadowOutcome, ResearchAutopilotRun, StrategyCard


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
        parts.append(f"失敗歸因 {', '.join(outcome.failure_attributions)}")

    next_action = autopilot.next_research_action if autopilot else outcome.recommended_strategy_action
    return f"{conclusion}：{'，'.join(parts)}；下一步 {next_action}。"


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"
