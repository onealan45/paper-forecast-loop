from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from forecast_loop.models import (
    EquityCurvePoint,
    PaperFill,
    PaperOrder,
    PaperOrderSide,
    PaperOrderStatus,
    PaperPortfolioSnapshot,
    PaperPosition,
)


@dataclass(slots=True)
class PaperFillResult:
    status: str
    reason: str | None
    order_id: str | None
    fill: PaperFill | None
    portfolio_snapshot: PaperPortfolioSnapshot | None
    equity_curve_point: EquityCurvePoint | None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "order_id": self.order_id,
            "fill_id": self.fill.fill_id if self.fill else None,
            "portfolio_snapshot_id": self.portfolio_snapshot.snapshot_id if self.portfolio_snapshot else None,
            "equity_curve_point_id": self.equity_curve_point.point_id if self.equity_curve_point else None,
            "fill": self.fill.to_dict() if self.fill else None,
            "portfolio_snapshot": self.portfolio_snapshot.to_dict() if self.portfolio_snapshot else None,
            "equity_curve_point": self.equity_curve_point.to_dict() if self.equity_curve_point else None,
        }


def fill_paper_order(
    *,
    repository,
    order_id: str,
    now: datetime,
    market_price: float = 100.0,
    fee_bps: float = 5.0,
    slippage_bps: float = 10.0,
) -> PaperFillResult:
    if market_price <= 0:
        raise ValueError("market_price must be positive.")
    orders = repository.load_paper_orders()
    order = _select_order(orders, order_id=order_id)
    if order is None:
        return PaperFillResult("skipped", "order_not_found", None if order_id == "latest" else order_id, None, None, None)
    if order.status != PaperOrderStatus.CREATED.value:
        return PaperFillResult("skipped", "order_not_open", order.order_id, None, None, None)

    latest_snapshot = _latest_or_empty_snapshot(repository, now)
    fill_price = _fill_price(order.side, market_price, slippage_bps)
    fill = _build_fill(
        order=order,
        now=now,
        market_price=market_price,
        fill_price=fill_price,
        portfolio=latest_snapshot,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
    )
    if fill is None:
        return PaperFillResult("skipped", "no_fill_required", order.order_id, None, latest_snapshot, None)

    updated_snapshot = _apply_fill(latest_snapshot, fill)
    equity_point = _equity_point_from_snapshot(updated_snapshot)
    order.status = PaperOrderStatus.FILLED.value
    repository.replace_paper_orders(orders)
    repository.save_paper_fill(fill)
    repository.save_portfolio_snapshot(updated_snapshot)
    repository.save_equity_curve_point(equity_point)
    return PaperFillResult("filled", None, order.order_id, fill, updated_snapshot, equity_point)


def create_portfolio_snapshot(
    *,
    repository,
    now: datetime,
    market_price: float = 100.0,
    symbol: str = "BTC-USD",
) -> PaperPortfolioSnapshot:
    if market_price <= 0:
        raise ValueError("market_price must be positive.")
    latest = _latest_or_empty_snapshot(repository, now)
    positions: list[PaperPosition] = []
    for position in latest.positions:
        if position.symbol == symbol:
            market_value = position.quantity * market_price
            unrealized_pnl = (market_price - position.avg_price) * position.quantity
            positions.append(
                PaperPosition(
                    symbol=position.symbol,
                    quantity=position.quantity,
                    avg_price=position.avg_price,
                    market_price=market_price,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    position_pct=0.0,
                )
            )
        else:
            positions.append(position)
    return _snapshot_from_components(
        created_at=now,
        cash=latest.cash,
        positions=positions,
        realized_pnl=latest.realized_pnl,
        max_drawdown_pct=latest.max_drawdown_pct,
    )


def save_portfolio_mark(repository, snapshot: PaperPortfolioSnapshot) -> EquityCurvePoint:
    repository.save_portfolio_snapshot(snapshot)
    point = _equity_point_from_snapshot(snapshot)
    repository.save_equity_curve_point(point)
    return point


def _select_order(orders: list[PaperOrder], *, order_id: str) -> PaperOrder | None:
    if order_id == "latest":
        open_orders = [order for order in orders if order.status == PaperOrderStatus.CREATED.value]
        return open_orders[-1] if open_orders else None
    return next((order for order in orders if order.order_id == order_id), None)


def _latest_or_empty_snapshot(repository, now: datetime) -> PaperPortfolioSnapshot:
    snapshots = repository.load_portfolio_snapshots()
    if snapshots:
        return snapshots[-1]
    snapshot = PaperPortfolioSnapshot.empty(created_at=now)
    repository.save_portfolio_snapshot(snapshot)
    return snapshot


def _fill_price(side: str, market_price: float, slippage_bps: float) -> float:
    adjustment = slippage_bps / 10_000
    if side == PaperOrderSide.BUY.value:
        return market_price * (1 + adjustment)
    return market_price * (1 - adjustment)


def _build_fill(
    *,
    order: PaperOrder,
    now: datetime,
    market_price: float,
    fill_price: float,
    portfolio: PaperPortfolioSnapshot,
    fee_bps: float,
    slippage_bps: float,
) -> PaperFill | None:
    current_value = _position_market_value(portfolio, order.symbol, market_price)
    target_pct = order.target_position_pct if order.target_position_pct is not None else order.current_position_pct
    target_value = (target_pct or 0.0) * portfolio.equity
    delta_value = target_value - current_value
    if order.side == PaperOrderSide.BUY.value:
        gross_value = max(0.0, delta_value)
        quantity = gross_value / fill_price if fill_price else 0.0
        net_cash_change_sign = -1
    else:
        existing = _position_for_symbol(portfolio, order.symbol)
        if existing is None or existing.quantity <= 0:
            return None
        requested_value = max(0.0, -delta_value)
        requested_quantity = requested_value / fill_price if fill_price else 0.0
        quantity = min(existing.quantity, requested_quantity)
        gross_value = quantity * fill_price
        net_cash_change_sign = 1
    if gross_value <= 0 or quantity <= 0:
        return None
    fee = gross_value * (fee_bps / 10_000)
    net_cash_change = net_cash_change_sign * gross_value - fee
    fill_id = PaperFill.build_id(
        order_id=order.order_id,
        symbol=order.symbol,
        side=order.side,
        quantity=quantity,
        fill_price=fill_price,
    )
    return PaperFill(
        fill_id=fill_id,
        order_id=order.order_id,
        decision_id=order.decision_id,
        symbol=order.symbol,
        side=order.side,
        filled_at=now,
        quantity=quantity,
        market_price=market_price,
        fill_price=fill_price,
        gross_value=gross_value,
        fee=fee,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        net_cash_change=net_cash_change,
    )


def _apply_fill(portfolio: PaperPortfolioSnapshot, fill: PaperFill) -> PaperPortfolioSnapshot:
    positions_by_symbol = {position.symbol: position for position in portfolio.positions}
    existing = positions_by_symbol.get(fill.symbol)
    realized_pnl = portfolio.realized_pnl
    cash = portfolio.cash + fill.net_cash_change
    if fill.side == PaperOrderSide.BUY.value:
        old_qty = existing.quantity if existing else 0.0
        old_cost = old_qty * (existing.avg_price if existing else 0.0)
        new_qty = old_qty + fill.quantity
        avg_price = (old_cost + fill.gross_value) / new_qty if new_qty else 0.0
        positions_by_symbol[fill.symbol] = PaperPosition(
            symbol=fill.symbol,
            quantity=new_qty,
            avg_price=avg_price,
            market_price=fill.market_price,
            market_value=new_qty * fill.market_price,
            unrealized_pnl=(fill.market_price - avg_price) * new_qty,
            position_pct=0.0,
        )
    else:
        if existing is None or existing.quantity <= 0:
            return portfolio
        sold_qty = min(fill.quantity, existing.quantity)
        realized_pnl += (fill.fill_price - existing.avg_price) * sold_qty - fill.fee
        new_qty = max(0.0, existing.quantity - sold_qty)
        if new_qty > 0:
            positions_by_symbol[fill.symbol] = PaperPosition(
                symbol=fill.symbol,
                quantity=new_qty,
                avg_price=existing.avg_price,
                market_price=fill.market_price,
                market_value=new_qty * fill.market_price,
                unrealized_pnl=(fill.market_price - existing.avg_price) * new_qty,
                position_pct=0.0,
            )
        else:
            positions_by_symbol.pop(fill.symbol, None)
    return _snapshot_from_components(
        created_at=fill.filled_at,
        cash=cash,
        positions=list(positions_by_symbol.values()),
        realized_pnl=realized_pnl,
        max_drawdown_pct=portfolio.max_drawdown_pct,
    )


def _snapshot_from_components(
    *,
    created_at: datetime,
    cash: float,
    positions: list[PaperPosition],
    realized_pnl: float,
    max_drawdown_pct: float | None,
) -> PaperPortfolioSnapshot:
    total_market_value = sum(position.market_value for position in positions)
    unrealized_pnl = sum(position.unrealized_pnl for position in positions)
    equity = cash + total_market_value
    gross_exposure_pct = abs(total_market_value) / equity if equity else 0.0
    net_exposure_pct = total_market_value / equity if equity else 0.0
    normalized_positions = [
        PaperPosition(
            symbol=position.symbol,
            quantity=position.quantity,
            avg_price=position.avg_price,
            market_price=position.market_price,
            market_value=position.market_value,
            unrealized_pnl=position.unrealized_pnl,
            position_pct=position.market_value / equity if equity else 0.0,
        )
        for position in positions
        if position.quantity > 0
    ]
    snapshot_id = PaperPortfolioSnapshot.build_id(
        created_at=created_at,
        equity=equity,
        cash=cash,
        positions=normalized_positions,
    )
    return PaperPortfolioSnapshot(
        snapshot_id=snapshot_id,
        created_at=created_at,
        equity=equity,
        cash=cash,
        gross_exposure_pct=gross_exposure_pct,
        net_exposure_pct=net_exposure_pct,
        max_drawdown_pct=max_drawdown_pct,
        positions=normalized_positions,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
        nav=equity,
    )


def _position_market_value(portfolio: PaperPortfolioSnapshot, symbol: str, market_price: float) -> float:
    position = _position_for_symbol(portfolio, symbol)
    if position is None:
        return 0.0
    return position.quantity * market_price


def _position_for_symbol(portfolio: PaperPortfolioSnapshot, symbol: str) -> PaperPosition | None:
    for position in portfolio.positions:
        if position.symbol == symbol:
            return position
    return None


def _equity_point_from_snapshot(snapshot: PaperPortfolioSnapshot) -> EquityCurvePoint:
    point_id = EquityCurvePoint.build_id(
        created_at=snapshot.created_at,
        equity=snapshot.equity,
        cash=snapshot.cash,
    )
    return EquityCurvePoint(
        point_id=point_id,
        created_at=snapshot.created_at,
        equity=snapshot.equity,
        cash=snapshot.cash,
        realized_pnl=snapshot.realized_pnl,
        unrealized_pnl=snapshot.unrealized_pnl,
        gross_exposure_pct=snapshot.gross_exposure_pct,
        net_exposure_pct=snapshot.net_exposure_pct,
        max_drawdown_pct=snapshot.max_drawdown_pct,
    )
