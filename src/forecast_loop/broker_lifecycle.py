from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from forecast_loop.models import BrokerOrder, BrokerOrderStatus, PaperOrder, PaperOrderStatus


@dataclass(slots=True)
class BrokerOrderResult:
    status: str
    reason: str | None
    broker_order: BrokerOrder | None
    local_order_id: str | None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "broker_order_id": self.broker_order.broker_order_id if self.broker_order else None,
            "local_order_id": self.local_order_id,
            "broker_order": self.broker_order.to_dict() if self.broker_order else None,
        }


def create_broker_order_lifecycle(
    *,
    repository,
    order_id: str,
    now: datetime,
    broker: str,
    broker_mode: str,
    mock_submit_status: str | None = None,
    broker_order_ref: str | None = None,
) -> BrokerOrderResult:
    local_order = _select_local_order(repository.load_paper_orders(), order_id=order_id)
    if local_order is None:
        return BrokerOrderResult(
            status="skipped",
            reason="local_order_not_found",
            broker_order=None,
            local_order_id=None if order_id == "latest" else order_id,
        )
    if local_order.status != PaperOrderStatus.CREATED.value:
        return BrokerOrderResult(
            status="skipped",
            reason="local_order_not_created",
            broker_order=None,
            local_order_id=local_order.order_id,
        )
    existing = _existing_broker_order(repository.load_broker_orders(), local_order.order_id, broker, broker_mode)
    if existing is not None:
        return BrokerOrderResult(
            status="skipped",
            reason="duplicate_broker_order",
            broker_order=existing,
            local_order_id=local_order.order_id,
        )

    status = _normalize_status(mock_submit_status)
    raw_response = _mock_response(status=status, broker_order_ref=broker_order_ref)
    broker_order = _build_broker_order(
        local_order=local_order,
        now=now,
        broker=broker,
        broker_mode=broker_mode,
        status=status,
        raw_response=raw_response,
        broker_order_ref=broker_order_ref or raw_response.get("broker_order_ref"),
    )
    repository.save_broker_order(broker_order)
    return BrokerOrderResult(
        status="created",
        reason=None,
        broker_order=broker_order,
        local_order_id=local_order.order_id,
    )


def _select_local_order(orders: list[PaperOrder], *, order_id: str) -> PaperOrder | None:
    if order_id == "latest":
        return orders[-1] if orders else None
    return next((order for order in orders if order.order_id == order_id), None)


def _existing_broker_order(
    orders: list[BrokerOrder],
    local_order_id: str,
    broker: str,
    broker_mode: str,
) -> BrokerOrder | None:
    return next(
        (
            order
            for order in orders
            if order.local_order_id == local_order_id and order.broker == broker and order.broker_mode == broker_mode
        ),
        None,
    )


def _normalize_status(status: str | None) -> str:
    normalized = (status or BrokerOrderStatus.CREATED.value).upper()
    if normalized not in {item.value for item in BrokerOrderStatus}:
        raise ValueError(f"unsupported broker order lifecycle status: {status}")
    return normalized


def _mock_response(*, status: str, broker_order_ref: str | None) -> dict:
    return {
        "mock": True,
        "status": status,
        "broker_order_ref": broker_order_ref,
        "live_trading": False,
    }


def _build_broker_order(
    *,
    local_order: PaperOrder,
    now: datetime,
    broker: str,
    broker_mode: str,
    status: str,
    raw_response: dict,
    broker_order_ref: str | None,
) -> BrokerOrder:
    broker_order_id = BrokerOrder.build_id(
        local_order_id=local_order.order_id,
        broker=broker,
        broker_mode=broker_mode,
    )
    return BrokerOrder(
        broker_order_id=broker_order_id,
        created_at=now,
        updated_at=now,
        local_order_id=local_order.order_id,
        decision_id=local_order.decision_id,
        symbol=local_order.symbol,
        side=local_order.side,
        quantity=None,
        target_position_pct=local_order.target_position_pct,
        broker=broker,
        broker_mode=broker_mode,
        status=status,
        broker_status=status,
        broker_order_ref=broker_order_ref,
        client_order_id=local_order.order_id,
        error_message="mock error" if status == BrokerOrderStatus.ERROR.value else None,
        raw_response=raw_response,
        decision_basis="paper-only broker order lifecycle mock",
    )
