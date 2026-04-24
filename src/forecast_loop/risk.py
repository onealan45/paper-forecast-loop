from __future__ import annotations

from datetime import datetime

from forecast_loop.models import EquityCurvePoint, PaperPortfolioSnapshot, RiskSnapshot


def evaluate_risk(
    *,
    repository,
    symbol: str,
    now: datetime,
    max_position_pct: float = 0.15,
    max_gross_exposure_pct: float = 0.20,
    reduce_risk_drawdown_pct: float = 0.05,
    stop_new_entries_drawdown_pct: float = 0.10,
) -> RiskSnapshot:
    portfolio = _latest_or_empty_portfolio(repository, now)
    equity_curve = repository.load_equity_curve_points()
    current_drawdown = _current_drawdown_pct(portfolio, equity_curve)
    max_drawdown = _max_drawdown_pct(portfolio, equity_curve, current_drawdown)
    position_pct = portfolio.position_pct_for(symbol)
    findings: list[str] = []

    if current_drawdown >= stop_new_entries_drawdown_pct:
        findings.append(
            f"current_drawdown {current_drawdown:.2%} >= stop threshold {stop_new_entries_drawdown_pct:.2%}"
        )
    elif current_drawdown >= reduce_risk_drawdown_pct:
        findings.append(
            f"current_drawdown {current_drawdown:.2%} >= reduce-risk threshold {reduce_risk_drawdown_pct:.2%}"
        )

    if portfolio.gross_exposure_pct > max_gross_exposure_pct:
        findings.append(f"gross_exposure {portfolio.gross_exposure_pct:.2%} > limit {max_gross_exposure_pct:.2%}")
    if abs(position_pct) > max_position_pct:
        findings.append(f"position {position_pct:.2%} > limit {max_position_pct:.2%}")

    status, severity, recommended_action = _risk_status(
        current_drawdown_pct=current_drawdown,
        stop_new_entries_drawdown_pct=stop_new_entries_drawdown_pct,
        findings=findings,
    )
    decision_basis = (
        f"status={status}; current_drawdown={current_drawdown}; max_drawdown={max_drawdown}; "
        f"gross_exposure={portfolio.gross_exposure_pct}; net_exposure={portfolio.net_exposure_pct}; "
        f"position_pct={position_pct}; findings={len(findings)}"
    )
    risk_id = RiskSnapshot.build_id(
        created_at=now,
        symbol=symbol,
        status=status,
        current_drawdown_pct=current_drawdown,
        gross_exposure_pct=portfolio.gross_exposure_pct,
        findings=findings,
    )
    snapshot = RiskSnapshot(
        risk_id=risk_id,
        created_at=now,
        symbol=symbol,
        status=status,
        severity=severity,
        current_drawdown_pct=current_drawdown,
        max_drawdown_pct=max_drawdown,
        gross_exposure_pct=portfolio.gross_exposure_pct,
        net_exposure_pct=portfolio.net_exposure_pct,
        position_pct=position_pct,
        max_position_pct=max_position_pct,
        max_gross_exposure_pct=max_gross_exposure_pct,
        reduce_risk_drawdown_pct=reduce_risk_drawdown_pct,
        stop_new_entries_drawdown_pct=stop_new_entries_drawdown_pct,
        findings=findings,
        recommended_action=recommended_action,
        decision_basis=decision_basis,
    )
    repository.save_risk_snapshot(snapshot)
    return snapshot


def _latest_or_empty_portfolio(repository, now: datetime) -> PaperPortfolioSnapshot:
    snapshots = repository.load_portfolio_snapshots()
    return snapshots[-1] if snapshots else PaperPortfolioSnapshot.empty(created_at=now)


def _current_drawdown_pct(portfolio: PaperPortfolioSnapshot, equity_curve: list[EquityCurvePoint]) -> float:
    current_equity = portfolio.equity
    prior_equity_values = [point.equity for point in equity_curve]
    peak = max([current_equity, *prior_equity_values], default=current_equity)
    if peak <= 0:
        return 0.0
    return max(0.0, (peak - current_equity) / peak)


def _max_drawdown_pct(
    portfolio: PaperPortfolioSnapshot,
    equity_curve: list[EquityCurvePoint],
    current_drawdown: float,
) -> float:
    recorded = [point.max_drawdown_pct for point in equity_curve if point.max_drawdown_pct is not None]
    if portfolio.max_drawdown_pct is not None:
        recorded.append(portfolio.max_drawdown_pct)
    recorded.append(current_drawdown)
    return max(recorded, default=0.0)


def _risk_status(
    *,
    current_drawdown_pct: float,
    stop_new_entries_drawdown_pct: float,
    findings: list[str],
) -> tuple[str, str, str]:
    if current_drawdown_pct >= stop_new_entries_drawdown_pct:
        return "STOP_NEW_ENTRIES", "blocking", "STOP_NEW_ENTRIES"
    if findings:
        return "REDUCE_RISK", "warning", "REDUCE_RISK"
    return "OK", "none", "HOLD"
