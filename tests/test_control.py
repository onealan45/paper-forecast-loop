from datetime import UTC, datetime, timedelta
import json

from forecast_loop.cli import main
from forecast_loop.control import record_control_event
from forecast_loop.health import run_health_check
from forecast_loop.models import Forecast, PaperOrderStatus, StrategyDecision
from forecast_loop.orders import create_paper_order_from_decision
from forecast_loop.storage import JsonFileRepository


def _forecast(now: datetime) -> Forecast:
    return Forecast(
        forecast_id="forecast:control",
        symbol="BTC-USD",
        created_at=now,
        anchor_time=now,
        target_window_start=now,
        target_window_end=now + timedelta(hours=24),
        candle_interval_minutes=60,
        expected_candle_count=25,
        status="pending",
        status_reason="awaiting_horizon_end",
        predicted_regime="trend_up",
        confidence=0.55,
        provider_data_through=now,
        observed_candle_count=0,
    )


def _decision(
    decision_id: str,
    *,
    now: datetime,
    action: str = "BUY",
    recommended_position_pct: float | None = 0.15,
) -> StrategyDecision:
    return StrategyDecision(
        decision_id=decision_id,
        created_at=now,
        symbol="BTC-USD",
        horizon_hours=24,
        action=action,
        confidence=0.7,
        evidence_grade="B",
        risk_level="MEDIUM",
        tradeable=True,
        blocked_reason=None,
        recommended_position_pct=recommended_position_pct,
        current_position_pct=0.0,
        max_position_pct=0.15,
        invalidation_conditions=["test"],
        reason_summary=f"{action} test decision",
        forecast_ids=["forecast:control"],
        score_ids=[],
        review_ids=[],
        baseline_ids=[],
        decision_basis="test",
    )


def _repository_with_decision(tmp_path, decision: StrategyDecision) -> JsonFileRepository:
    repository = JsonFileRepository(tmp_path)
    repository.save_forecast(_forecast(decision.created_at))
    repository.save_strategy_decision(decision)
    return repository


def test_operator_control_records_stop_new_entries_without_confirmation(tmp_path, capsys):
    now = datetime(2026, 4, 25, 3, 0, tzinfo=UTC)

    exit_code = main(
        [
            "operator-control",
            "--storage-dir",
            str(tmp_path),
            "--action",
            "STOP_NEW_ENTRIES",
            "--reason",
            "reduce paper risk during provider incident",
            "--symbol",
            "BTC-USD",
            "--now",
            now.isoformat(),
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    events = JsonFileRepository(tmp_path).load_control_events()

    assert exit_code == 0
    assert payload["status"] == "recorded"
    assert payload["event"]["action"] == "STOP_NEW_ENTRIES"
    assert payload["event"]["confirmed"] is False
    assert payload["event"]["symbol"] == "BTC-USD"
    assert events[0].control_id == payload["control_id"]


def test_operator_control_requires_confirmation_for_risky_controls(tmp_path, capsys):
    now = datetime(2026, 4, 25, 3, 0, tzinfo=UTC)

    emergency_exit = main(
        [
            "operator-control",
            "--storage-dir",
            str(tmp_path),
            "--action",
            "EMERGENCY_STOP",
            "--reason",
            "manual safety stop",
            "--now",
            now.isoformat(),
        ]
    )
    emergency_payload = json.loads(capsys.readouterr().out)

    max_position_exit = main(
        [
            "operator-control",
            "--storage-dir",
            str(tmp_path),
            "--action",
            "SET_MAX_POSITION",
            "--max-position-pct",
            "0.1",
            "--reason",
            "lower max risk",
            "--now",
            now.isoformat(),
        ]
    )
    max_position_payload = json.loads(capsys.readouterr().out)

    assert emergency_exit == 2
    assert emergency_payload["status"] == "rejected"
    assert emergency_payload["reason"] == "confirmation_required"
    assert max_position_exit == 2
    assert max_position_payload["status"] == "rejected"
    assert max_position_payload["reason"] == "confirmation_required"
    assert JsonFileRepository(tmp_path).load_control_events() == []


def test_paper_order_blocks_buy_when_stop_new_entries_control_is_active(tmp_path):
    now = datetime(2026, 4, 25, 3, 0, tzinfo=UTC)
    repository = _repository_with_decision(tmp_path, _decision("decision:buy", now=now))
    record_control_event(
        repository=repository,
        action="STOP_NEW_ENTRIES",
        now=now,
        reason="operator stop",
        symbol="BTC-USD",
    )

    result = create_paper_order_from_decision(
        repository=repository,
        decision_id="latest",
        symbol="BTC-USD",
        now=now,
    )

    assert result.status == "skipped"
    assert result.reason == "control_stop_new_entries"
    assert repository.load_paper_orders() == []


def test_paper_order_allows_reduce_risk_sell_when_stop_new_entries_is_active(tmp_path):
    now = datetime(2026, 4, 25, 3, 0, tzinfo=UTC)
    repository = _repository_with_decision(
        tmp_path,
        _decision("decision:reduce", now=now, action="REDUCE_RISK", recommended_position_pct=0.05),
    )
    record_control_event(
        repository=repository,
        action="STOP_NEW_ENTRIES",
        now=now,
        reason="operator stop",
        symbol="BTC-USD",
    )

    result = create_paper_order_from_decision(
        repository=repository,
        decision_id="latest",
        symbol="BTC-USD",
        now=now,
    )

    assert result.status == "created"
    assert result.order is not None
    assert result.order.side == "SELL"
    assert result.order.status == PaperOrderStatus.CREATED.value


def test_emergency_stop_blocks_all_paper_orders(tmp_path):
    now = datetime(2026, 4, 25, 3, 0, tzinfo=UTC)
    repository = _repository_with_decision(tmp_path, _decision("decision:buy", now=now))
    record_control_event(
        repository=repository,
        action="EMERGENCY_STOP",
        now=now,
        reason="manual safety stop",
        symbol="BTC-USD",
        confirmed=True,
    )

    result = create_paper_order_from_decision(
        repository=repository,
        decision_id="latest",
        symbol="BTC-USD",
        now=now,
    )

    assert result.status == "skipped"
    assert result.reason == "control_emergency_stop"
    assert repository.load_paper_orders() == []


def test_set_max_position_blocks_oversized_buy(tmp_path):
    now = datetime(2026, 4, 25, 3, 0, tzinfo=UTC)
    repository = _repository_with_decision(tmp_path, _decision("decision:buy", now=now))
    record_control_event(
        repository=repository,
        action="SET_MAX_POSITION",
        now=now,
        reason="cap position risk",
        symbol="BTC-USD",
        confirmed=True,
        max_position_pct=0.05,
    )

    result = create_paper_order_from_decision(
        repository=repository,
        decision_id="latest",
        symbol="BTC-USD",
        now=now,
    )

    assert result.status == "skipped"
    assert result.reason == "control_max_position_exceeded"
    assert repository.load_paper_orders() == []


def test_health_check_audits_bad_and_duplicate_control_events(tmp_path):
    now = datetime(2026, 4, 25, 3, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_forecast(_forecast(now))
    event_result = record_control_event(
        repository=repository,
        action="STOP_NEW_ENTRIES",
        now=now,
        reason="operator stop",
        symbol="BTC-USD",
    )
    event_payload = event_result.event.to_dict()
    (tmp_path / "control_events.jsonl").write_text(
        "\n".join(
            [
                json.dumps(event_payload),
                json.dumps(event_payload),
                "{bad json",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_health_check(
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=now,
        create_repair_request=False,
    )
    codes = {finding.code for finding in result.findings}

    assert result.repair_required is True
    assert "bad_json_row" in codes
    assert "duplicate_control_id" in codes
