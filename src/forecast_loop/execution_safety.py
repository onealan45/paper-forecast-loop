from __future__ import annotations

from datetime import datetime

from forecast_loop.assets import get_asset
from forecast_loop.broker import BrokerMode
from forecast_loop.control import current_control_state, paper_order_control_block_reason
from forecast_loop.health import run_health_check
from forecast_loop.market_calendar import is_us_equity_trading_day
from forecast_loop.models import (
    BrokerOrder,
    BrokerOrderStatus,
    BrokerReconciliation,
    ExecutionSafetyGate,
    ExecutionSafetyGateStatus,
    PaperOrder,
    PaperOrderStatus,
    RiskSnapshot,
    StrategyDecision,
)


ORDERABLE_ACTIONS = {"BUY", "SELL", "REDUCE_RISK"}
EVIDENCE_RANK = {"INSUFFICIENT": 0, "D": 1, "C": 2, "B": 3, "A": 4}
ACTIVE_BROKER_ORDER_STATUSES = {
    BrokerOrderStatus.CREATED.value,
    BrokerOrderStatus.SUBMITTED.value,
    BrokerOrderStatus.ACKNOWLEDGED.value,
    BrokerOrderStatus.PARTIALLY_FILLED.value,
}


def evaluate_execution_safety_gate(
    *,
    repository,
    storage_dir,
    symbol: str,
    now: datetime,
    broker: str,
    broker_mode: str,
    broker_health: dict,
    decision_id: str = "latest",
    order_id: str = "latest",
    min_evidence_grade: str = "B",
    max_order_position_pct: float = 0.10,
) -> ExecutionSafetyGate:
    normalized_broker_mode = _normalize_broker_mode(broker_mode)
    decision = _select_decision(repository.load_strategy_decisions(), decision_id=decision_id, symbol=symbol)
    order = _select_order(repository.load_paper_orders(), order_id=order_id, symbol=symbol, decision=decision)
    risk = _latest_for_symbol(repository.load_risk_snapshots(), symbol)
    reconciliation = _latest_reconciliation(repository.load_broker_reconciliations(), broker, normalized_broker_mode)
    health_result = run_health_check(
        storage_dir=storage_dir,
        symbol=symbol,
        now=now,
        create_repair_request=False,
    )
    checks = [
        _check("health_check", health_result.status == "healthy", f"health_status={health_result.status}", health_result.check_id),
        *_decision_checks(decision, min_evidence_grade),
        *_control_checks(repository, decision),
        *_risk_checks(risk, decision),
        *_broker_health_checks(broker_health, normalized_broker_mode),
        *_order_checks(
            order=order,
            decision=decision,
            orders=repository.load_paper_orders(),
            broker_orders=repository.load_broker_orders(),
            broker=broker,
            broker_mode=normalized_broker_mode,
            max_order_position_pct=max_order_position_pct,
        ),
        *_reconciliation_checks(reconciliation),
        _market_check(symbol, now),
    ]
    allowed = all(check["status"] == "pass" for check in checks)
    gate = ExecutionSafetyGate(
        gate_id=ExecutionSafetyGate.build_id(
            created_at=now,
            symbol=symbol,
            decision_id=decision.decision_id if decision else None,
            order_id=order.order_id if order else None,
            broker=broker,
            broker_mode=normalized_broker_mode,
            checks=checks,
        ),
        created_at=now,
        symbol=symbol,
        decision_id=decision.decision_id if decision else None,
        order_id=order.order_id if order else None,
        broker=broker,
        broker_mode=normalized_broker_mode,
        status=ExecutionSafetyGateStatus.PASS.value if allowed else ExecutionSafetyGateStatus.BLOCKED.value,
        severity="none" if allowed else "blocking",
        allowed=allowed,
        checks=checks,
        health_check_id=health_result.check_id,
        risk_id=risk.risk_id if risk else None,
        broker_reconciliation_id=reconciliation.reconciliation_id if reconciliation else None,
        decision_basis="paper-only external execution safety gate; no broker submit is performed",
    )
    repository.save_execution_safety_gate(gate)
    return gate


def _normalize_broker_mode(mode: str) -> str:
    normalized = mode.upper().replace("-", "_")
    allowed = {BrokerMode.EXTERNAL_PAPER.value, BrokerMode.SANDBOX.value}
    if normalized not in allowed:
        raise ValueError(
            f"unsupported execution safety broker mode: {mode}; "
            "allowed modes are EXTERNAL_PAPER and SANDBOX. Live trading is unavailable."
        )
    return normalized


def _select_decision(decisions: list[StrategyDecision], *, decision_id: str, symbol: str) -> StrategyDecision | None:
    if decision_id == "latest":
        scoped = [decision for decision in decisions if decision.symbol == symbol]
        return scoped[-1] if scoped else None
    return next((decision for decision in decisions if decision.decision_id == decision_id), None)


def _select_order(
    orders: list[PaperOrder],
    *,
    order_id: str,
    symbol: str,
    decision: StrategyDecision | None,
) -> PaperOrder | None:
    if order_id != "latest":
        return next((order for order in orders if order.order_id == order_id), None)
    scoped = [order for order in orders if order.symbol == symbol]
    if decision is not None:
        matching = [order for order in scoped if order.decision_id == decision.decision_id]
        if matching:
            return matching[-1]
    return scoped[-1] if scoped else None


def _latest_for_symbol(snapshots: list[RiskSnapshot], symbol: str) -> RiskSnapshot | None:
    scoped = [snapshot for snapshot in snapshots if snapshot.symbol == symbol]
    return scoped[-1] if scoped else None


def _latest_reconciliation(
    reconciliations: list[BrokerReconciliation],
    broker: str,
    broker_mode: str,
) -> BrokerReconciliation | None:
    scoped = [
        reconciliation
        for reconciliation in reconciliations
        if reconciliation.broker == broker and reconciliation.broker_mode == broker_mode
    ]
    return scoped[-1] if scoped else None


def _decision_checks(decision: StrategyDecision | None, min_grade: str) -> list[dict]:
    if decision is None:
        return [_check("decision_exists", False, "decision not found")]
    grade_passes = EVIDENCE_RANK.get(decision.evidence_grade, 0) >= EVIDENCE_RANK.get(min_grade, 3)
    return [
        _check("decision_exists", True, f"decision_id={decision.decision_id}", decision.decision_id),
        _check("decision_tradeable", decision.tradeable, f"tradeable={decision.tradeable}", decision.decision_id),
        _check("decision_action_orderable", decision.action in ORDERABLE_ACTIONS, f"action={decision.action}", decision.decision_id),
        _check(
            "evidence_grade",
            grade_passes,
            f"evidence_grade={decision.evidence_grade}; minimum={min_grade}",
            decision.decision_id,
        ),
    ]


def _control_checks(repository, decision: StrategyDecision | None) -> list[dict]:
    if decision is None:
        return [_check("operator_control", False, "decision missing")]
    state = current_control_state(repository.load_control_events(), symbol=decision.symbol)
    reason = paper_order_control_block_reason(state=state, decision=decision)
    return [_check("operator_control", reason is None, reason or f"control_status={state.status}", state.latest_control_id)]


def _risk_checks(risk: RiskSnapshot | None, decision: StrategyDecision | None) -> list[dict]:
    if risk is None:
        return [_check("risk_snapshot", False, "risk snapshot missing")]
    risk_passes = risk.severity != "blocking"
    if decision is not None and decision.action == "BUY" and risk.severity != "none":
        risk_passes = False
    return [
        _check("risk_snapshot", True, f"risk_id={risk.risk_id}", risk.risk_id),
        _check("risk_limits", risk_passes, f"risk_status={risk.status}; severity={risk.severity}", risk.risk_id),
    ]


def _broker_health_checks(broker_health: dict, broker_mode: str) -> list[dict]:
    status = str(broker_health.get("status", "")).lower()
    mode = broker_health.get("mode")
    live_available = bool(broker_health.get("live_trading_available", False))
    mode_passes = mode in (None, broker_mode)
    return [
        _check("broker_health", status == "healthy", f"broker_health_status={status or 'missing'}"),
        _check("broker_mode", mode_passes, f"broker_health_mode={mode}; expected={broker_mode}"),
        _check("broker_live_unavailable", not live_available, "live_trading_available must be false"),
    ]


def _order_checks(
    *,
    order: PaperOrder | None,
    decision: StrategyDecision | None,
    orders: list[PaperOrder],
    broker_orders: list[BrokerOrder],
    broker: str,
    broker_mode: str,
    max_order_position_pct: float,
) -> list[dict]:
    if order is None:
        return [_check("paper_order_exists", False, "paper order not found")]
    delta = _order_delta(decision=decision, order=order)
    duplicate_paper = next(
        (
            item
            for item in orders
            if item.order_id != order.order_id
            and item.symbol == order.symbol
            and item.status == PaperOrderStatus.CREATED.value
        ),
        None,
    )
    duplicate_broker = next(
        (
            item
            for item in broker_orders
            if item.symbol == order.symbol
            and item.broker == broker
            and item.broker_mode == broker_mode
            and item.status in ACTIVE_BROKER_ORDER_STATUSES
        ),
        None,
    )
    return [
        _check("paper_order_exists", True, f"order_id={order.order_id}", order.order_id),
        _check("paper_order_open", order.status == PaperOrderStatus.CREATED.value, f"order_status={order.status}", order.order_id),
        _check(
            "max_order_size",
            delta is not None and delta <= max_order_position_pct,
            f"order_delta_pct={delta}; max_order_position_pct={max_order_position_pct}",
            order.order_id,
        ),
        _check(
            "duplicate_active_paper_order",
            duplicate_paper is None,
            f"duplicate_order_id={duplicate_paper.order_id if duplicate_paper else None}",
            duplicate_paper.order_id if duplicate_paper else None,
        ),
        _check(
            "duplicate_active_broker_order",
            duplicate_broker is None,
            f"duplicate_broker_order_id={duplicate_broker.broker_order_id if duplicate_broker else None}",
            duplicate_broker.broker_order_id if duplicate_broker else None,
        ),
    ]


def _reconciliation_checks(reconciliation: BrokerReconciliation | None) -> list[dict]:
    if reconciliation is None:
        return [_check("broker_reconciliation", False, "broker reconciliation missing")]
    return [
        _check(
            "broker_reconciliation",
            not reconciliation.repair_required and reconciliation.severity != "blocking",
            f"reconciliation_status={reconciliation.status}; repair_required={reconciliation.repair_required}",
            reconciliation.reconciliation_id,
        )
    ]


def _market_check(symbol: str, now: datetime) -> dict:
    asset = get_asset(symbol)
    if asset is None:
        return _check("market_open", False, f"asset registry missing symbol={symbol}")
    if asset.asset_class == "crypto":
        return _check("market_open", True, "crypto market is continuous")
    if asset.market == "US":
        is_open = is_us_equity_trading_day(now.date())
        return _check("market_open", is_open, f"US market trading_day={is_open}")
    return _check("market_open", False, f"unsupported market for execution gate: {asset.market}")


def _order_delta(*, decision: StrategyDecision | None, order: PaperOrder) -> float | None:
    target = order.target_position_pct
    current = order.current_position_pct
    if target is None and decision is not None:
        target = decision.recommended_position_pct
    if current is None and decision is not None:
        current = decision.current_position_pct
    if target is None or current is None:
        return None
    return abs(float(target) - float(current))


def _check(code: str, passed: bool, message: str, artifact_id: str | None = None) -> dict:
    return {
        "code": code,
        "status": "pass" if passed else "fail",
        "severity": "none" if passed else "blocking",
        "message": message,
        "artifact_id": artifact_id,
    }
