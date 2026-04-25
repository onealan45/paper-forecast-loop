from datetime import UTC, datetime

from forecast_loop.models import HealthCheckResult, HealthFinding, RiskSnapshot, StrategyDecision
from forecast_loop.notifications import generate_notification_artifacts
from forecast_loop.storage import JsonFileRepository


def _decision(now: datetime, *, action: str = "STOP_NEW_ENTRIES") -> StrategyDecision:
    return StrategyDecision(
        decision_id="decision:notify",
        created_at=now,
        symbol="BTC-USD",
        horizon_hours=24,
        action=action,
        confidence=None,
        evidence_grade="INSUFFICIENT",
        risk_level="HIGH",
        tradeable=False,
        blocked_reason="health_check_repair_required",
        recommended_position_pct=0.0,
        current_position_pct=0.0,
        max_position_pct=0.15,
        invalidation_conditions=["health-check returns healthy"],
        reason_summary="測試用停止新進場。",
        forecast_ids=[],
        score_ids=[],
        review_ids=[],
        baseline_ids=[],
        decision_basis="test",
    )


def _health(now: datetime) -> HealthCheckResult:
    return HealthCheckResult(
        check_id="health:notify",
        created_at=now,
        status="unhealthy",
        severity="blocking",
        repair_required=True,
        repair_request_id="repair:notify",
        findings=[
            HealthFinding(
                code="missing_latest_forecast",
                severity="blocking",
                message="missing forecast",
                artifact_path="forecasts.jsonl",
                repair_required=True,
            )
        ],
    )


def _risk(now: datetime) -> RiskSnapshot:
    return RiskSnapshot(
        risk_id="risk:notify",
        created_at=now,
        symbol="BTC-USD",
        status="STOP_NEW_ENTRIES",
        severity="blocking",
        current_drawdown_pct=0.12,
        max_drawdown_pct=0.12,
        gross_exposure_pct=0.1,
        net_exposure_pct=0.1,
        position_pct=0.1,
        max_position_pct=0.15,
        max_gross_exposure_pct=0.20,
        reduce_risk_drawdown_pct=0.05,
        stop_new_entries_drawdown_pct=0.10,
        findings=["current_drawdown 12.00% >= stop threshold 10.00%"],
        recommended_action="STOP_NEW_ENTRIES",
        decision_basis="test",
    )


def test_notification_artifacts_cover_m5g_attention_types(tmp_path):
    now = datetime(2026, 4, 25, 5, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)

    notifications = generate_notification_artifacts(
        repository=repository,
        symbol="BTC-USD",
        now=now,
        decision=_decision(now),
        health_result=_health(now),
        risk_snapshot=_risk(now),
    )

    types = {notification.notification_type for notification in notifications}
    assert types == {
        "NEW_DECISION",
        "BUY_SELL_BLOCKED",
        "STOP_NEW_ENTRIES",
        "HEALTH_BLOCKING",
        "REPAIR_REQUEST_CREATED",
        "DRAWDOWN_BREACH",
    }
    saved = repository.load_notification_artifacts()
    assert saved == notifications
    assert all(notification.delivery_channel == "local_artifact" for notification in saved)
    assert all(notification.status == "pending" for notification in saved)
    assert all("decision:notify" in notification.source_artifact_ids for notification in saved)
    assert any(notification.repair_request_id == "repair:notify" for notification in saved)


def test_notification_generation_is_idempotent_for_same_source_payload(tmp_path):
    now = datetime(2026, 4, 25, 5, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)

    generate_notification_artifacts(
        repository=repository,
        symbol="BTC-USD",
        now=now,
        decision=_decision(now, action="HOLD"),
    )
    generate_notification_artifacts(
        repository=repository,
        symbol="BTC-USD",
        now=now,
        decision=_decision(now, action="HOLD"),
    )

    notifications = repository.load_notification_artifacts()
    assert len(notifications) == 2
    assert {notification.notification_type for notification in notifications} == {"NEW_DECISION", "BUY_SELL_BLOCKED"}
