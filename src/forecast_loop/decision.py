from __future__ import annotations

from datetime import datetime, timedelta

from forecast_loop.baselines import build_baseline_evaluation
from forecast_loop.models import (
    BaselineEvaluation,
    HealthCheckResult,
    PaperPortfolioSnapshot,
    Review,
    StrategyDecision,
)


BULLISH_REGIMES = {"trend_up", "volatile_bull"}
BEARISH_REGIMES = {"trend_down", "volatile_bear"}


def generate_strategy_decision(
    *,
    repository,
    symbol: str,
    horizon_hours: int,
    now: datetime,
    health_result: HealthCheckResult | None = None,
    max_position_pct: float = 0.15,
    stale_after_hours: int = 48,
) -> StrategyDecision:
    if health_result is not None and health_result.repair_required:
        decision = StrategyDecision.build_fail_closed(
            symbol=symbol,
            horizon_hours=horizon_hours,
            created_at=now,
            blocked_reason="health_check_repair_required",
            reason_summary="health-check 需要修復；Codex 修復完成前停止新進場。",
            repair_request_id=health_result.repair_request_id,
        )
        try:
            repository.save_strategy_decision(decision)
        except Exception:
            # Corrupt storage must not prevent the CLI from returning a conservative decision.
            pass
        return decision

    forecasts = [forecast for forecast in repository.load_forecasts() if forecast.symbol == symbol]
    scores = repository.load_scores()
    reviews = repository.load_reviews()
    baseline = build_baseline_evaluation(
        symbol=symbol,
        generated_at=now,
        forecasts=forecasts,
        scores=scores,
    )
    repository.save_baseline_evaluation(baseline)
    portfolio = _latest_or_empty_portfolio(repository, now)
    current_position_pct = portfolio.position_pct_for(symbol)
    latest_forecast = forecasts[-1] if forecasts else None
    linked_review_ids = _review_ids_for_baseline(reviews, baseline)

    action = "HOLD"
    tradeable = False
    blocked_reason: str | None = None
    reason_summary = "目前證據不足以支持方向性的 paper-only 建議。"
    risk_level = "UNKNOWN"
    recommended_position_pct: float | None = current_position_pct
    evidence_grade = baseline.evidence_grade
    confidence = latest_forecast.confidence if latest_forecast else None
    invalidation_conditions = [
        "新的 provider 資料推翻最新 forecast regime。",
        "health-check 回報 storage、scoring 或 dashboard integrity 的 blocking 問題。",
        "近期模型分數跌破決策門檻。",
    ]

    if latest_forecast is None:
        action = "STOP_NEW_ENTRIES"
        tradeable = False
        blocked_reason = "missing_latest_forecast"
        reason_summary = "目前沒有最新 forecast；系統不能產生方向性的 paper-only 決策。"
        risk_level = "HIGH"
        evidence_grade = "INSUFFICIENT"
        recommended_position_pct = 0.0
    elif now - latest_forecast.anchor_time > timedelta(hours=stale_after_hours):
        action = "STOP_NEW_ENTRIES"
        tradeable = False
        blocked_reason = "latest_forecast_stale"
        reason_summary = "最新 forecast 已超過允許時效；停止新進場直到資料恢復新鮮。"
        risk_level = "HIGH"
        evidence_grade = "INSUFFICIENT"
        recommended_position_pct = min(current_position_pct, max_position_pct)
    elif baseline.evidence_grade == "INSUFFICIENT":
        action = "HOLD"
        tradeable = False
        blocked_reason = "insufficient_evidence"
        reason_summary = "已評分 forecast 樣本不足，不足以支持買進或賣出。"
        risk_level = "UNKNOWN"
    elif baseline.model_edge is None or baseline.model_edge <= 0:
        action = "HOLD"
        tradeable = False
        blocked_reason = "model_not_beating_baseline"
        reason_summary = "模型證據沒有打贏 naive persistence baseline，因此買進/賣出被擋住。"
        risk_level = "MEDIUM"
    elif baseline.recent_score is not None and baseline.recent_score < 0.40:
        action = "REDUCE_RISK"
        tradeable = True
        blocked_reason = None
        reason_summary = "雖然相對 baseline 仍有部分 edge，但近期 forecast 分數偏弱，建議降低 paper 風險。"
        risk_level = "HIGH"
        recommended_position_pct = max(0.0, min(current_position_pct, max_position_pct) * 0.5)
    elif baseline.evidence_grade not in {"A", "B"}:
        action = "HOLD"
        tradeable = False
        blocked_reason = "evidence_grade_too_weak_for_directional_action"
        reason_summary = "證據方向偏正面，但強度不足以支持買進或賣出。"
        risk_level = "MEDIUM"
    elif latest_forecast.predicted_regime in BULLISH_REGIMES:
        action = "BUY"
        tradeable = True
        reason_summary = "最新 forecast 偏多，且模型證據在品質足夠時打贏 baseline。"
        risk_level = "MEDIUM"
        recommended_position_pct = max_position_pct
    elif latest_forecast.predicted_regime in BEARISH_REGIMES:
        action = "SELL"
        tradeable = True
        reason_summary = "最新 forecast 偏空，且模型證據在品質足夠時打贏 baseline。"
        risk_level = "MEDIUM"
        recommended_position_pct = 0.0
    else:
        action = "HOLD"
        tradeable = False
        blocked_reason = "unknown_forecast_regime"
        reason_summary = "最新 forecast regime 方向性不足，不應產生買進或賣出。"
        risk_level = "UNKNOWN"

    forecast_ids = [latest_forecast.forecast_id] if latest_forecast else []
    decision_basis = _decision_basis(action=action, baseline=baseline, blocked_reason=blocked_reason)
    decision_id = StrategyDecision.build_id(
        symbol=symbol,
        horizon_hours=horizon_hours,
        action=action,
        forecast_ids=forecast_ids,
        score_ids=baseline.score_ids,
        review_ids=linked_review_ids,
        baseline_ids=[baseline.baseline_id],
        decision_basis=decision_basis,
    )
    decision = StrategyDecision(
        decision_id=decision_id,
        created_at=now,
        symbol=symbol,
        horizon_hours=horizon_hours,
        action=action,
        confidence=confidence,
        evidence_grade=evidence_grade,
        risk_level=risk_level,
        tradeable=tradeable,
        blocked_reason=blocked_reason,
        recommended_position_pct=recommended_position_pct,
        current_position_pct=current_position_pct,
        max_position_pct=max_position_pct,
        invalidation_conditions=invalidation_conditions,
        reason_summary=reason_summary,
        forecast_ids=forecast_ids,
        score_ids=baseline.score_ids,
        review_ids=linked_review_ids,
        baseline_ids=[baseline.baseline_id],
        decision_basis=decision_basis,
    )
    repository.save_strategy_decision(decision)
    return decision


def _latest_or_empty_portfolio(repository, now: datetime) -> PaperPortfolioSnapshot:
    snapshots = repository.load_portfolio_snapshots()
    if snapshots:
        return snapshots[-1]
    snapshot = PaperPortfolioSnapshot.empty(created_at=now)
    repository.save_portfolio_snapshot(snapshot)
    return snapshot


def _review_ids_for_baseline(reviews: list[Review], baseline: BaselineEvaluation) -> list[str]:
    baseline_score_ids = set(baseline.score_ids)
    return [
        review.review_id
        for review in reviews
        if baseline_score_ids and set(review.score_ids).issubset(baseline_score_ids)
    ]


def _decision_basis(*, action: str, baseline: BaselineEvaluation, blocked_reason: str | None) -> str:
    return (
        f"action={action}; evidence_grade={baseline.evidence_grade}; "
        f"sample_size={baseline.sample_size}; model_edge={baseline.model_edge}; "
        f"recent_score={baseline.recent_score}; blocked_reason={blocked_reason or 'none'}"
    )
