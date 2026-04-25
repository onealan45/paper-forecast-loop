from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from forecast_loop.models import PaperControlAction, PaperControlEvent, StrategyDecision


CONFIRMATION_REQUIRED_ACTIONS = {
    PaperControlAction.RESUME.value,
    PaperControlAction.EMERGENCY_STOP.value,
    PaperControlAction.SET_MAX_POSITION.value,
}
PAPER_ORDER_BLOCKING_ACTIONS = {
    PaperControlAction.PAUSE.value,
    PaperControlAction.EMERGENCY_STOP.value,
}


@dataclass(slots=True)
class PaperControlState:
    paused: bool = False
    stop_new_entries: bool = False
    reduce_risk: bool = False
    emergency_stop: bool = False
    max_position_pct: float | None = None
    latest_control_id: str | None = None

    @property
    def status(self) -> str:
        if self.emergency_stop:
            return "EMERGENCY_STOP"
        if self.paused:
            return "PAUSED"
        if self.reduce_risk:
            return "REDUCE_RISK"
        if self.stop_new_entries:
            return "STOP_NEW_ENTRIES"
        return "ACTIVE"


@dataclass(slots=True)
class PaperControlResult:
    status: str
    reason: str | None
    event: PaperControlEvent | None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "control_id": self.event.control_id if self.event else None,
            "event": self.event.to_dict() if self.event else None,
        }


def record_control_event(
    *,
    repository,
    action: str,
    now: datetime,
    reason: str,
    actor: str = "operator",
    symbol: str | None = None,
    confirmed: bool = False,
    max_position_pct: float | None = None,
) -> PaperControlResult:
    normalized_action = action.upper()
    if normalized_action not in {item.value for item in PaperControlAction}:
        return PaperControlResult(status="rejected", reason="unsupported_control_action", event=None)
    if not reason.strip():
        return PaperControlResult(status="rejected", reason="reason_required", event=None)

    parameter_name = None
    parameter_value = None
    if normalized_action == PaperControlAction.SET_MAX_POSITION.value:
        if max_position_pct is None:
            return PaperControlResult(status="rejected", reason="max_position_pct_required", event=None)
        if max_position_pct < 0 or max_position_pct > 1:
            return PaperControlResult(status="rejected", reason="max_position_pct_out_of_range", event=None)
        parameter_name = "max_position_pct"
        parameter_value = max_position_pct

    requires_confirmation = normalized_action in CONFIRMATION_REQUIRED_ACTIONS
    if requires_confirmation and not confirmed:
        return PaperControlResult(status="rejected", reason="confirmation_required", event=None)

    event = PaperControlEvent(
        control_id=PaperControlEvent.build_id(
            created_at=now,
            action=normalized_action,
            actor=actor,
            reason=reason.strip(),
            symbol=symbol,
            parameter_name=parameter_name,
            parameter_value=parameter_value,
        ),
        created_at=now,
        action=normalized_action,
        actor=actor,
        reason=reason.strip(),
        status="ACTIVE",
        symbol=symbol,
        requires_confirmation=requires_confirmation,
        confirmed=confirmed,
        parameter_name=parameter_name,
        parameter_value=parameter_value,
        decision_basis="paper-only audited operator control",
    )
    repository.save_control_event(event)
    return PaperControlResult(status="recorded", reason=None, event=event)


def current_control_state(events: list[PaperControlEvent], *, symbol: str | None = None) -> PaperControlState:
    state = PaperControlState()
    for event in sorted(events, key=lambda item: item.created_at):
        if event.symbol not in (None, symbol):
            continue
        state.latest_control_id = event.control_id
        if event.action == PaperControlAction.PAUSE.value:
            state.paused = True
        elif event.action == PaperControlAction.RESUME.value:
            state.paused = False
            state.stop_new_entries = False
            state.reduce_risk = False
            state.emergency_stop = False
        elif event.action == PaperControlAction.STOP_NEW_ENTRIES.value:
            state.stop_new_entries = True
        elif event.action == PaperControlAction.REDUCE_RISK.value:
            state.reduce_risk = True
            state.stop_new_entries = True
        elif event.action == PaperControlAction.EMERGENCY_STOP.value:
            state.emergency_stop = True
            state.paused = True
            state.stop_new_entries = True
            state.reduce_risk = True
        elif event.action == PaperControlAction.SET_MAX_POSITION.value:
            state.max_position_pct = event.parameter_value
    return state


def paper_order_control_block_reason(
    *,
    state: PaperControlState,
    decision: StrategyDecision,
) -> str | None:
    if state.emergency_stop:
        return "control_emergency_stop"
    if state.paused:
        return "control_paused"
    if decision.action == "BUY" and state.stop_new_entries:
        return "control_stop_new_entries"
    if decision.action == "BUY" and state.reduce_risk:
        return "control_reduce_risk"
    if (
        decision.action == "BUY"
        and state.max_position_pct is not None
        and decision.recommended_position_pct is not None
        and decision.recommended_position_pct > state.max_position_pct
    ):
        return "control_max_position_exceeded"
    return None
