from __future__ import annotations

from dataclasses import dataclass

from forecast_loop.models import BaselineEvaluation, BacktestResult, WalkForwardValidation


@dataclass(frozen=True, slots=True)
class ResearchGateResult:
    directional_allowed: bool
    blocked_reason: str | None
    recommended_action: str | None
    risk_level: str
    flags: list[str]
    decision_basis: str


def evaluate_research_gates(
    *,
    baseline: BaselineEvaluation,
    latest_backtest: BacktestResult | None,
    latest_walk_forward: WalkForwardValidation | None,
    min_sample_size: int = 5,
    min_model_edge: float = 0.0,
    max_drawdown: float = 0.25,
) -> ResearchGateResult:
    flags: list[str] = []
    recommended_action: str | None = None
    risk_level = "MEDIUM"

    if baseline.sample_size < min_sample_size:
        flags.append("research_sample_size_too_low")
    if baseline.model_edge is None or baseline.model_edge <= min_model_edge:
        flags.append("research_model_edge_not_positive")
    if latest_backtest is None:
        flags.append("research_backtest_missing")
    else:
        if latest_backtest.strategy_return <= latest_backtest.benchmark_return:
            flags.append("research_backtest_not_beating_benchmark")
        if latest_backtest.max_drawdown > max_drawdown:
            flags.append("research_backtest_drawdown_too_high")
    if latest_walk_forward is None:
        flags.append("research_walk_forward_missing")
    else:
        if latest_walk_forward.average_excess_return <= 0:
            flags.append("research_walk_forward_excess_return_not_positive")
        if latest_walk_forward.average_test_return <= latest_walk_forward.average_benchmark_return:
            flags.append("research_walk_forward_not_beating_benchmark")
        if latest_walk_forward.overfit_risk_flags:
            flags.append("research_walk_forward_overfit_risk")

    if "research_backtest_drawdown_too_high" in flags or "research_walk_forward_overfit_risk" in flags:
        recommended_action = "REDUCE_RISK"
        risk_level = "HIGH"
    if baseline.recent_score is not None and baseline.recent_score < 0.40:
        recommended_action = "REDUCE_RISK"
        risk_level = "HIGH"
        flags.append("research_recent_degradation")

    directional_allowed = not flags
    blocked_reason = None if directional_allowed else flags[0]
    return ResearchGateResult(
        directional_allowed=directional_allowed,
        blocked_reason=blocked_reason,
        recommended_action=recommended_action,
        risk_level=risk_level,
        flags=sorted(set(flags)),
        decision_basis=_decision_basis(
            baseline=baseline,
            latest_backtest=latest_backtest,
            latest_walk_forward=latest_walk_forward,
            flags=flags,
        ),
    )


def _decision_basis(
    *,
    baseline: BaselineEvaluation,
    latest_backtest: BacktestResult | None,
    latest_walk_forward: WalkForwardValidation | None,
    flags: list[str],
) -> str:
    return (
        "research_gate="
        f"sample_size={baseline.sample_size}; "
        f"model_edge={baseline.model_edge}; "
        f"recent_score={baseline.recent_score}; "
        f"backtest_result={latest_backtest.result_id if latest_backtest else 'missing'}; "
        f"backtest_strategy_return={latest_backtest.strategy_return if latest_backtest else None}; "
        f"backtest_benchmark_return={latest_backtest.benchmark_return if latest_backtest else None}; "
        f"backtest_max_drawdown={latest_backtest.max_drawdown if latest_backtest else None}; "
        f"walk_forward={latest_walk_forward.validation_id if latest_walk_forward else 'missing'}; "
        f"walk_forward_average_excess_return={latest_walk_forward.average_excess_return if latest_walk_forward else None}; "
        f"walk_forward_average_test_return={latest_walk_forward.average_test_return if latest_walk_forward else None}; "
        f"walk_forward_average_benchmark_return={latest_walk_forward.average_benchmark_return if latest_walk_forward else None}; "
        f"flags={','.join(sorted(set(flags))) or 'none'}"
    )
