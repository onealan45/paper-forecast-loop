from __future__ import annotations

from datetime import datetime

from forecast_loop.models import HealthCheckResult, NotificationArtifact, RiskSnapshot, StrategyDecision


def generate_notification_artifacts(
    *,
    repository,
    symbol: str,
    now: datetime,
    decision: StrategyDecision | None = None,
    health_result: HealthCheckResult | None = None,
    risk_snapshot: RiskSnapshot | None = None,
) -> list[NotificationArtifact]:
    """Create local, read-only notification artifacts for operator attention."""
    notifications: list[NotificationArtifact] = []

    if decision is not None:
        notifications.append(
            _notification(
                created_at=now,
                symbol=symbol,
                notification_type="NEW_DECISION",
                severity="info",
                title="新策略決策",
                message=(
                    f"{symbol} 最新 paper-only 決策為 {decision.action}；"
                    f"證據等級 {decision.evidence_grade}，可交易={str(decision.tradeable).lower()}。"
                ),
                action=decision.action,
                decision=decision,
                health_result=health_result,
                risk_snapshot=risk_snapshot,
                decision_basis="new strategy decision artifact",
            )
        )
        if decision.blocked_reason and not decision.tradeable:
            notifications.append(
                _notification(
                    created_at=now,
                    symbol=symbol,
                    notification_type="BUY_SELL_BLOCKED",
                    severity="warning",
                    title="買進/賣出訊號被擋",
                    message=f"{symbol} 不產生 BUY/SELL：{decision.blocked_reason}。",
                    action=decision.action,
                    decision=decision,
                    health_result=health_result,
                    risk_snapshot=risk_snapshot,
                    decision_basis="blocked buy/sell decision gate",
                )
            )
        if decision.action == "STOP_NEW_ENTRIES":
            notifications.append(
                _notification(
                    created_at=now,
                    symbol=symbol,
                    notification_type="STOP_NEW_ENTRIES",
                    severity="blocking",
                    title="停止新進場",
                    message=f"{symbol} 進入停止新進場；原因：{decision.blocked_reason or decision.reason_summary}",
                    action=decision.action,
                    decision=decision,
                    health_result=health_result,
                    risk_snapshot=risk_snapshot,
                    decision_basis="stop new entries decision",
                )
            )

    if health_result is not None and _health_is_blocking(health_result):
        notifications.append(
            _notification(
                created_at=now,
                symbol=symbol,
                notification_type="HEALTH_BLOCKING",
                severity="blocking",
                title="健康檢查阻塞",
                message=f"{symbol} health-check={health_result.status}；repair_required={str(health_result.repair_required).lower()}。",
                action=None,
                decision=decision,
                health_result=health_result,
                risk_snapshot=risk_snapshot,
                decision_basis="blocking health check",
            )
        )
    if health_result is not None and health_result.repair_request_id:
        notifications.append(
            _notification(
                created_at=now,
                symbol=symbol,
                notification_type="REPAIR_REQUEST_CREATED",
                severity="blocking",
                title="修復請求已建立",
                message=f"{symbol} 已建立 Codex repair request：{health_result.repair_request_id}。",
                action=None,
                decision=decision,
                health_result=health_result,
                risk_snapshot=risk_snapshot,
                decision_basis="repair request created",
            )
        )

    if risk_snapshot is not None and _drawdown_breached(risk_snapshot):
        notifications.append(
            _notification(
                created_at=now,
                symbol=symbol,
                notification_type="DRAWDOWN_BREACH",
                severity=risk_snapshot.severity if risk_snapshot.severity in {"warning", "blocking"} else "warning",
                title="回撤門檻觸發",
                message=(
                    f"{symbol} current_drawdown={risk_snapshot.current_drawdown_pct:.2%}；"
                    f"建議動作 {risk_snapshot.recommended_action}。"
                ),
                action=risk_snapshot.recommended_action,
                decision=decision,
                health_result=health_result,
                risk_snapshot=risk_snapshot,
                decision_basis="risk drawdown breach",
            )
        )

    for notification in notifications:
        repository.save_notification_artifact(notification)
    return notifications


def _notification(
    *,
    created_at: datetime,
    symbol: str,
    notification_type: str,
    severity: str,
    title: str,
    message: str,
    action: str | None,
    decision: StrategyDecision | None,
    health_result: HealthCheckResult | None,
    risk_snapshot: RiskSnapshot | None,
    decision_basis: str,
) -> NotificationArtifact:
    source_artifact_ids = _source_ids(decision, health_result, risk_snapshot)
    return NotificationArtifact(
        notification_id=NotificationArtifact.build_id(
            created_at=created_at,
            symbol=symbol,
            notification_type=notification_type,
            source_artifact_ids=source_artifact_ids,
            message=message,
        ),
        created_at=created_at,
        symbol=symbol,
        notification_type=notification_type,
        severity=severity,
        title=title,
        message=message,
        status="pending",
        delivery_channel="local_artifact",
        action=action,
        source_artifact_ids=source_artifact_ids,
        decision_id=decision.decision_id if decision else None,
        health_check_id=health_result.check_id if health_result else None,
        repair_request_id=health_result.repair_request_id if health_result else None,
        risk_id=risk_snapshot.risk_id if risk_snapshot else None,
        decision_basis=decision_basis,
    )


def _source_ids(
    decision: StrategyDecision | None,
    health_result: HealthCheckResult | None,
    risk_snapshot: RiskSnapshot | None,
) -> list[str]:
    ids = [
        decision.decision_id if decision else None,
        health_result.check_id if health_result else None,
        health_result.repair_request_id if health_result else None,
        risk_snapshot.risk_id if risk_snapshot else None,
    ]
    return [item for item in ids if item]


def _health_is_blocking(health_result: HealthCheckResult) -> bool:
    return health_result.repair_required or health_result.severity == "blocking" or health_result.status == "unhealthy"


def _drawdown_breached(risk_snapshot: RiskSnapshot) -> bool:
    return risk_snapshot.current_drawdown_pct >= risk_snapshot.reduce_risk_drawdown_pct
