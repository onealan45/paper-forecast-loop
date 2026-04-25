from __future__ import annotations

from datetime import datetime, timedelta

from forecast_loop.baselines import build_baseline_evaluation
from forecast_loop.models import (
    BaselineEvaluation,
    HealthCheckResult,
    PaperPortfolioSnapshot,
    RiskSnapshot,
    Review,
    StrategyDecision,
)
from forecast_loop.research_gates import ResearchGateResult, evaluate_research_gates


BULLISH_REGIMES = {"trend_up", "volatile_bull"}
BEARISH_REGIMES = {"trend_down", "volatile_bear"}


def generate_strategy_decision(
    *,
    repository,
    symbol: str,
    horizon_hours: int,
    now: datetime,
    health_result: HealthCheckResult | None = None,
    risk_snapshot: RiskSnapshot | None = None,
    max_position_pct: float = 0.15,
    stale_after_hours: int = 48,
    risk_stale_after_hours: int = 2,
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
    latest_backtest = _latest_for_symbol(repository.load_backtest_results(), symbol)
    latest_walk_forward = _latest_for_symbol(repository.load_walk_forward_validations(), symbol)
    research_gate = evaluate_research_gates(
        baseline=baseline,
        latest_backtest=latest_backtest,
        latest_walk_forward=latest_walk_forward,
    )
    portfolio = _latest_or_empty_portfolio(repository, now)
    current_position_pct = portfolio.position_pct_for(symbol)
    risk_snapshot = risk_snapshot or _latest_risk_snapshot(repository, symbol)
    risk_blocked_reason = _risk_blocked_reason(
        risk_snapshot=risk_snapshot,
        symbol=symbol,
        now=now,
        risk_stale_after_hours=risk_stale_after_hours,
    )
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
        "risk-check 缺少或過期，無法確認 drawdown 與曝險 gate。",
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
    elif risk_snapshot is not None and risk_snapshot.status == "STOP_NEW_ENTRIES":
        action = "STOP_NEW_ENTRIES"
        tradeable = False
        blocked_reason = "risk_stop_new_entries"
        reason_summary = "風險檢查觸發停止新進場 gate；暫停方向性 paper order。"
        risk_level = "HIGH"
        recommended_position_pct = min(current_position_pct, max_position_pct)
    elif risk_snapshot is not None and risk_snapshot.status == "REDUCE_RISK":
        action = "REDUCE_RISK"
        tradeable = current_position_pct > 0
        blocked_reason = None if tradeable else "risk_reduce_required_but_no_position"
        reason_summary = "風險檢查偵測 drawdown 或曝險超標，建議先降低 paper 風險。"
        risk_level = "HIGH"
        recommended_position_pct = max(0.0, min(current_position_pct, max_position_pct) * 0.5)
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
    elif research_gate.recommended_action == "REDUCE_RISK":
        action = "REDUCE_RISK"
        tradeable = current_position_pct > 0
        blocked_reason = None if tradeable else "research_reduce_required_but_no_position"
        reason_summary = "研究品質 gate 偵測近期退化、回測風險或 walk-forward 風險，建議降低 paper 風險。"
        risk_level = research_gate.risk_level
        recommended_position_pct = max(0.0, min(current_position_pct, max_position_pct) * 0.5)
    elif not research_gate.directional_allowed:
        action = "HOLD"
        tradeable = False
        blocked_reason = research_gate.blocked_reason
        reason_summary = "研究品質 gate 未通過；BUY/SELL 在樣本、baseline、backtest、walk-forward 或 drawdown 證據不足時被擋住。"
        risk_level = research_gate.risk_level
    elif baseline.evidence_grade not in {"A", "B"}:
        action = "HOLD"
        tradeable = False
        blocked_reason = "evidence_grade_too_weak_for_directional_action"
        reason_summary = "證據方向偏正面，但強度不足以支持買進或賣出。"
        risk_level = "MEDIUM"
    elif latest_forecast.predicted_regime in BULLISH_REGIMES:
        if risk_blocked_reason is not None:
            action = "STOP_NEW_ENTRIES"
            tradeable = False
            blocked_reason = risk_blocked_reason
            reason_summary = "方向性買進需要新鮮 risk-check；缺少風險證據時停止新進場。"
            risk_level = "HIGH"
            recommended_position_pct = min(current_position_pct, max_position_pct)
        else:
            action = "BUY"
            tradeable = True
            reason_summary = "最新 forecast 偏多，且模型證據在品質足夠時打贏 baseline。"
            risk_level = "MEDIUM"
            recommended_position_pct = max_position_pct
    elif latest_forecast.predicted_regime in BEARISH_REGIMES:
        if risk_blocked_reason is not None:
            action = "STOP_NEW_ENTRIES"
            tradeable = False
            blocked_reason = risk_blocked_reason
            reason_summary = "方向性賣出需要新鮮 risk-check；缺少風險證據時停止新進場。"
            risk_level = "HIGH"
            recommended_position_pct = min(current_position_pct, max_position_pct)
        else:
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
    decision_basis = _decision_basis(
        action=action,
        baseline=baseline,
        blocked_reason=blocked_reason,
        risk_snapshot=risk_snapshot,
        research_gate=research_gate,
    )
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


def _latest_risk_snapshot(repository, symbol: str) -> RiskSnapshot | None:
    snapshots = [snapshot for snapshot in repository.load_risk_snapshots() if snapshot.symbol == symbol]
    return snapshots[-1] if snapshots else None


def _latest_for_symbol(items: list, symbol: str):
    scoped = [item for item in items if getattr(item, "symbol", None) == symbol]
    return max(scoped, key=lambda item: item.created_at) if scoped else None


def _risk_blocked_reason(
    *,
    risk_snapshot: RiskSnapshot | None,
    symbol: str,
    now: datetime,
    risk_stale_after_hours: int,
) -> str | None:
    if risk_snapshot is None:
        return "risk_snapshot_missing"
    if risk_snapshot.symbol != symbol:
        return "risk_snapshot_symbol_mismatch"
    if now - risk_snapshot.created_at > timedelta(hours=risk_stale_after_hours):
        return "risk_snapshot_stale"
    return None


def _review_ids_for_baseline(reviews: list[Review], baseline: BaselineEvaluation) -> list[str]:
    baseline_score_ids = set(baseline.score_ids)
    return [
        review.review_id
        for review in reviews
        if baseline_score_ids and set(review.score_ids).issubset(baseline_score_ids)
    ]


def _decision_basis(
    *,
    action: str,
    baseline: BaselineEvaluation,
    blocked_reason: str | None,
    risk_snapshot: RiskSnapshot | None,
    research_gate: ResearchGateResult,
) -> str:
    risk_basis = "none" if risk_snapshot is None else f"{risk_snapshot.risk_id}:{risk_snapshot.status}"
    return (
        f"action={action}; evidence_grade={baseline.evidence_grade}; "
        f"sample_size={baseline.sample_size}; model_edge={baseline.model_edge}; "
        f"recent_score={baseline.recent_score}; risk={risk_basis}; "
        f"blocked_reason={blocked_reason or 'none'}; {research_gate.decision_basis}"
    )
