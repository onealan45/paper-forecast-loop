from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from forecast_loop.models import (
    HealthCheckResult,
    PaperOrder,
    PaperOrderSide,
    PaperOrderStatus,
    PaperOrderType,
    StrategyDecision,
)


ACTIVE_ORDER_STATUSES = {PaperOrderStatus.CREATED.value}
ORDERABLE_ACTIONS = {"BUY", "SELL", "REDUCE_RISK"}


@dataclass(slots=True)
class PaperOrderResult:
    status: str
    reason: str | None
    decision_id: str | None
    order: PaperOrder | None
    active_order_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "decision_id": self.decision_id,
            "order_id": self.order.order_id if self.order else None,
            "active_order_id": self.active_order_id,
            "order": self.order.to_dict() if self.order else None,
        }


def create_paper_order_from_decision(
    *,
    repository,
    decision_id: str,
    symbol: str,
    now: datetime,
    health_result: HealthCheckResult | None = None,
) -> PaperOrderResult:
    if health_result is not None and (health_result.severity == "blocking" or health_result.repair_required):
        return PaperOrderResult(
            status="skipped",
            reason="health_blocking",
            decision_id=None,
            order=None,
        )

    decision = _select_decision(repository.load_strategy_decisions(), decision_id=decision_id, symbol=symbol)
    if decision is None:
        return PaperOrderResult(
            status="skipped",
            reason="decision_not_found",
            decision_id=None if decision_id == "latest" else decision_id,
            order=None,
        )

    if decision.action in {"HOLD", "STOP_NEW_ENTRIES"}:
        return PaperOrderResult(
            status="skipped",
            reason="action_creates_no_order",
            decision_id=decision.decision_id,
            order=None,
        )

    if decision.action not in ORDERABLE_ACTIONS:
        return PaperOrderResult(
            status="skipped",
            reason="unsupported_decision_action",
            decision_id=decision.decision_id,
            order=None,
        )

    if not decision.tradeable:
        return PaperOrderResult(
            status="skipped",
            reason="decision_not_tradeable",
            decision_id=decision.decision_id,
            order=None,
        )

    active_order = _active_order_for_symbol(repository.load_paper_orders(), symbol=decision.symbol)
    if active_order is not None:
        return PaperOrderResult(
            status="skipped",
            reason="duplicate_active_order",
            decision_id=decision.decision_id,
            order=None,
            active_order_id=active_order.order_id,
        )

    side = _side_for_decision(decision)
    order_type = PaperOrderType.TARGET_PERCENT.value
    order_id = PaperOrder.build_id(
        decision_id=decision.decision_id,
        symbol=decision.symbol,
        side=side,
        target_position_pct=decision.recommended_position_pct,
        order_type=order_type,
    )
    order = PaperOrder(
        order_id=order_id,
        created_at=now,
        decision_id=decision.decision_id,
        symbol=decision.symbol,
        side=side,
        order_type=order_type,
        status=PaperOrderStatus.CREATED.value,
        target_position_pct=decision.recommended_position_pct,
        current_position_pct=decision.current_position_pct,
        max_position_pct=decision.max_position_pct,
        rationale=decision.reason_summary,
    )
    repository.save_paper_order(order)
    return PaperOrderResult(
        status="created",
        reason=None,
        decision_id=decision.decision_id,
        order=order,
    )


def _select_decision(
    decisions: list[StrategyDecision],
    *,
    decision_id: str,
    symbol: str,
) -> StrategyDecision | None:
    if decision_id == "latest":
        scoped = [decision for decision in decisions if decision.symbol == symbol]
        return scoped[-1] if scoped else None
    return next((decision for decision in decisions if decision.decision_id == decision_id), None)


def _side_for_decision(decision: StrategyDecision) -> str:
    if decision.action == "BUY":
        return PaperOrderSide.BUY.value
    return PaperOrderSide.SELL.value


def _active_order_for_symbol(orders: list[PaperOrder], *, symbol: str) -> PaperOrder | None:
    return next(
        (
            order
            for order in orders
            if order.symbol == symbol and order.status in ACTIVE_ORDER_STATUSES
        ),
        None,
    )
