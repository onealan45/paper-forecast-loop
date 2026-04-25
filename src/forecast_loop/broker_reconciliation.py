from __future__ import annotations

from collections import Counter
from datetime import datetime

from forecast_loop.broker import BrokerMode
from forecast_loop.models import (
    BrokerOrder,
    BrokerOrderStatus,
    BrokerReconciliation,
    BrokerReconciliationStatus,
    PaperPortfolioSnapshot,
)


TRACKED_EXTERNAL_STATUSES = {
    BrokerOrderStatus.SUBMITTED.value,
    BrokerOrderStatus.ACKNOWLEDGED.value,
    BrokerOrderStatus.PARTIALLY_FILLED.value,
}
TERMINAL_STATUSES = {
    BrokerOrderStatus.FILLED.value,
    BrokerOrderStatus.CANCELLED.value,
    BrokerOrderStatus.REJECTED.value,
    BrokerOrderStatus.EXPIRED.value,
    BrokerOrderStatus.ERROR.value,
}


def run_broker_reconciliation(
    *,
    repository,
    external_snapshot: dict,
    now: datetime,
    broker: str,
    broker_mode: str,
    cash_tolerance: float = 0.01,
    equity_tolerance: float = 0.01,
    position_tolerance: float = 1e-9,
) -> BrokerReconciliation:
    normalized_broker_mode = _normalize_broker_mode(broker_mode)
    local_orders = [
        order
        for order in repository.load_broker_orders()
        if order.broker == broker and order.broker_mode == normalized_broker_mode
    ]
    external_orders = list(external_snapshot.get("orders", []))
    external_positions = list(external_snapshot.get("positions", []))
    latest_portfolio = _latest_portfolio(repository.load_portfolio_snapshots())

    order_result = _reconcile_orders(local_orders, external_orders)
    portfolio_result = _reconcile_portfolio(
        latest_portfolio=latest_portfolio,
        external_snapshot=external_snapshot,
        external_positions=external_positions,
        cash_tolerance=cash_tolerance,
        equity_tolerance=equity_tolerance,
        position_tolerance=position_tolerance,
    )
    findings = [*order_result["findings"], *portfolio_result["findings"]]
    severity = "blocking" if findings else "none"
    status = BrokerReconciliationStatus.MISMATCH.value if findings else BrokerReconciliationStatus.MATCHED.value
    reconciliation_id = BrokerReconciliation.build_id(
        created_at=now,
        broker=broker,
        broker_mode=normalized_broker_mode,
        local_broker_order_ids=[order.broker_order_id for order in local_orders],
        external_order_refs=order_result["external_order_refs"],
        findings=findings,
    )
    reconciliation = BrokerReconciliation(
        reconciliation_id=reconciliation_id,
        created_at=now,
        broker=broker,
        broker_mode=normalized_broker_mode,
        status=status,
        severity=severity,
        repair_required=bool(findings),
        local_broker_order_ids=[order.broker_order_id for order in local_orders],
        external_order_refs=order_result["external_order_refs"],
        matched_order_refs=order_result["matched_order_refs"],
        missing_external_order_ids=order_result["missing_external_order_ids"],
        unknown_external_order_refs=order_result["unknown_external_order_refs"],
        duplicate_broker_order_refs=order_result["duplicate_broker_order_refs"],
        status_mismatches=order_result["status_mismatches"],
        position_mismatches=portfolio_result["position_mismatches"],
        cash_mismatch=portfolio_result["cash_mismatch"],
        equity_mismatch=portfolio_result["equity_mismatch"],
        findings=findings,
        decision_basis="paper-only broker reconciliation against external paper/sandbox snapshot",
    )
    repository.save_broker_reconciliation(reconciliation)
    return reconciliation


def _normalize_broker_mode(mode: str) -> str:
    normalized = mode.upper().replace("-", "_")
    allowed = {BrokerMode.EXTERNAL_PAPER.value, BrokerMode.SANDBOX.value}
    if normalized not in allowed:
        raise ValueError(
            f"unsupported broker reconciliation mode: {mode}; "
            "allowed modes are EXTERNAL_PAPER and SANDBOX. Live trading is unavailable."
        )
    return normalized


def _reconcile_orders(local_orders: list[BrokerOrder], external_orders: list[dict]) -> dict:
    external_refs = [_external_order_ref(order) for order in external_orders]
    external_refs = [ref for ref in external_refs if ref]
    external_ref_counts = Counter(external_refs)
    duplicate_refs = sorted(ref for ref, count in external_ref_counts.items() if count > 1)
    local_refs = {order.broker_order_ref for order in local_orders if order.broker_order_ref}
    missing_order_ids = [
        order.broker_order_id
        for order in local_orders
        if order.status in TRACKED_EXTERNAL_STATUSES and order.broker_order_ref not in set(external_refs)
    ]
    unknown_refs = sorted(ref for ref in set(external_refs) if ref not in local_refs)
    matched_refs = sorted(ref for ref in set(external_refs) if ref in local_refs)
    status_mismatches = _status_mismatches(local_orders, external_orders)
    findings = []
    if missing_order_ids:
        findings.append(
            {
                "code": "missing_external_order",
                "severity": "blocking",
                "message": "Local tracked broker order is missing from external paper/sandbox snapshot.",
                "broker_order_ids": missing_order_ids,
            }
        )
    if unknown_refs:
        findings.append(
            {
                "code": "unknown_external_order",
                "severity": "blocking",
                "message": "External paper/sandbox snapshot contains orders unknown to the local ledger.",
                "broker_order_refs": unknown_refs,
            }
        )
    if duplicate_refs:
        findings.append(
            {
                "code": "duplicate_external_broker_order_ref",
                "severity": "blocking",
                "message": "External paper/sandbox snapshot contains duplicate broker order references.",
                "broker_order_refs": duplicate_refs,
            }
        )
    if status_mismatches:
        findings.append(
            {
                "code": "broker_order_status_mismatch",
                "severity": "blocking",
                "message": "Local broker order status differs from the external paper/sandbox snapshot.",
                "mismatches": status_mismatches,
            }
        )
    return {
        "external_order_refs": external_refs,
        "matched_order_refs": matched_refs,
        "missing_external_order_ids": missing_order_ids,
        "unknown_external_order_refs": unknown_refs,
        "duplicate_broker_order_refs": duplicate_refs,
        "status_mismatches": status_mismatches,
        "findings": findings,
    }


def _status_mismatches(local_orders: list[BrokerOrder], external_orders: list[dict]) -> list[dict]:
    external_by_ref = {_external_order_ref(order): order for order in external_orders if _external_order_ref(order)}
    mismatches = []
    for local_order in local_orders:
        if not local_order.broker_order_ref or local_order.broker_order_ref not in external_by_ref:
            continue
        external_status = str(external_by_ref[local_order.broker_order_ref].get("status", "")).upper()
        if external_status and external_status != local_order.status:
            mismatches.append(
                {
                    "broker_order_id": local_order.broker_order_id,
                    "broker_order_ref": local_order.broker_order_ref,
                    "local_status": local_order.status,
                    "external_status": external_status,
                }
            )
    return mismatches


def _external_order_ref(order: dict) -> str | None:
    for key in ("broker_order_ref", "order_id", "id", "client_order_id"):
        value = order.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _reconcile_portfolio(
    *,
    latest_portfolio: PaperPortfolioSnapshot | None,
    external_snapshot: dict,
    external_positions: list[dict],
    cash_tolerance: float,
    equity_tolerance: float,
    position_tolerance: float,
) -> dict:
    findings = []
    cash_mismatch = None
    equity_mismatch = None
    position_mismatches = []
    if latest_portfolio is not None:
        cash_mismatch = _numeric_mismatch(
            local_value=latest_portfolio.cash,
            external_value=external_snapshot.get("cash"),
            tolerance=cash_tolerance,
            field="cash",
        )
        equity_mismatch = _numeric_mismatch(
            local_value=latest_portfolio.equity,
            external_value=external_snapshot.get("equity"),
            tolerance=equity_tolerance,
            field="equity",
        )
        position_mismatches = _position_mismatches(latest_portfolio, external_positions, position_tolerance)
    elif external_positions or external_snapshot.get("cash") is not None or external_snapshot.get("equity") is not None:
        findings.append(
            {
                "code": "missing_local_portfolio_snapshot",
                "severity": "blocking",
                "message": "External paper/sandbox account snapshot exists but no local portfolio snapshot is available.",
            }
        )

    if cash_mismatch:
        findings.append(
            {
                "code": "cash_mismatch",
                "severity": "blocking",
                "message": "Local paper cash differs from external paper/sandbox account cash.",
                "mismatch": cash_mismatch,
            }
        )
    if equity_mismatch:
        findings.append(
            {
                "code": "equity_mismatch",
                "severity": "blocking",
                "message": "Local paper equity differs from external paper/sandbox account equity.",
                "mismatch": equity_mismatch,
            }
        )
    if position_mismatches:
        findings.append(
            {
                "code": "position_mismatch",
                "severity": "blocking",
                "message": "Local paper positions differ from external paper/sandbox positions.",
                "mismatches": position_mismatches,
            }
        )
    return {
        "position_mismatches": position_mismatches,
        "cash_mismatch": cash_mismatch,
        "equity_mismatch": equity_mismatch,
        "findings": findings,
    }


def _numeric_mismatch(*, local_value: float, external_value, tolerance: float, field: str) -> dict | None:
    if external_value is None:
        return None
    external_float = float(external_value)
    if abs(float(local_value) - external_float) <= tolerance:
        return None
    return {"field": field, "local": float(local_value), "external": external_float, "tolerance": tolerance}


def _position_mismatches(
    latest_portfolio: PaperPortfolioSnapshot,
    external_positions: list[dict],
    tolerance: float,
) -> list[dict]:
    local_by_symbol = {position.symbol: position for position in latest_portfolio.positions}
    external_by_symbol = {
        str(position.get("symbol")): position
        for position in external_positions
        if position.get("symbol") not in (None, "")
    }
    mismatches = []
    for symbol in sorted(set(local_by_symbol) | set(external_by_symbol)):
        local_quantity = local_by_symbol.get(symbol).quantity if symbol in local_by_symbol else 0.0
        external_quantity = float(external_by_symbol.get(symbol, {}).get("quantity", 0.0) or 0.0)
        if abs(local_quantity - external_quantity) > tolerance:
            mismatches.append(
                {
                    "symbol": symbol,
                    "local_quantity": local_quantity,
                    "external_quantity": external_quantity,
                    "tolerance": tolerance,
                }
            )
    return mismatches


def _latest_portfolio(snapshots: list[PaperPortfolioSnapshot]) -> PaperPortfolioSnapshot | None:
    return snapshots[-1] if snapshots else None
