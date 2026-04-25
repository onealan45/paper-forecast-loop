from datetime import UTC, datetime
import json

import pytest

from forecast_loop.broker_lifecycle import create_broker_order_lifecycle
from forecast_loop.cli import main
from forecast_loop.health import run_health_check
from forecast_loop.models import (
    BrokerOrderStatus,
    Forecast,
    PaperOrder,
    PaperOrderStatus,
    PaperOrderType,
    StrategyDecision,
)
from forecast_loop.storage import JsonFileRepository


def _forecast(now: datetime) -> Forecast:
    return Forecast(
        forecast_id="forecast:broker-order",
        symbol="BTC-USD",
        created_at=now,
        anchor_time=now,
        target_window_start=now,
        target_window_end=now,
        candle_interval_minutes=60,
        expected_candle_count=1,
        status="pending",
        status_reason="awaiting_horizon_end",
        predicted_regime="trend_up",
        confidence=0.7,
        provider_data_through=now,
        observed_candle_count=0,
    )


def _decision(now: datetime) -> StrategyDecision:
    return StrategyDecision(
        decision_id="decision:broker-order",
        created_at=now,
        symbol="BTC-USD",
        horizon_hours=24,
        action="BUY",
        confidence=0.7,
        evidence_grade="B",
        risk_level="MEDIUM",
        tradeable=True,
        blocked_reason=None,
        recommended_position_pct=0.15,
        current_position_pct=0.0,
        max_position_pct=0.15,
        invalidation_conditions=["test"],
        reason_summary="broker lifecycle test",
        forecast_ids=["forecast:broker-order"],
        score_ids=[],
        review_ids=[],
        baseline_ids=[],
        decision_basis="test",
    )


def _order(now: datetime) -> PaperOrder:
    return PaperOrder(
        order_id="paper-order:broker-order",
        created_at=now,
        decision_id="decision:broker-order",
        symbol="BTC-USD",
        side="BUY",
        order_type=PaperOrderType.TARGET_PERCENT.value,
        status=PaperOrderStatus.CREATED.value,
        target_position_pct=0.15,
        current_position_pct=0.0,
        max_position_pct=0.15,
        rationale="test",
    )


def _repository(tmp_path, now: datetime) -> JsonFileRepository:
    repository = JsonFileRepository(tmp_path)
    repository.save_forecast(_forecast(now))
    repository.save_strategy_decision(_decision(now))
    repository.save_paper_order(_order(now))
    return repository


def test_broker_order_lifecycle_created_from_local_paper_order(tmp_path):
    now = datetime(2026, 4, 25, 7, 0, tzinfo=UTC)
    repository = _repository(tmp_path, now)

    result = create_broker_order_lifecycle(
        repository=repository,
        order_id="latest",
        now=now,
        broker="binance_testnet",
        broker_mode="SANDBOX",
        mock_submit_status="ACKNOWLEDGED",
        broker_order_ref="testnet:123",
    )

    assert result.status == "created"
    assert result.broker_order is not None
    assert result.broker_order.status == BrokerOrderStatus.ACKNOWLEDGED.value
    assert result.broker_order.local_order_id == "paper-order:broker-order"
    assert result.broker_order.broker == "binance_testnet"
    assert result.broker_order.broker_mode == "SANDBOX"
    assert result.broker_order.broker_order_ref == "testnet:123"
    assert result.broker_order.raw_response["live_trading"] is False
    assert repository.load_broker_orders() == [result.broker_order]


def test_broker_order_lifecycle_blocks_duplicate_for_same_local_order(tmp_path):
    now = datetime(2026, 4, 25, 7, 0, tzinfo=UTC)
    repository = _repository(tmp_path, now)

    first = create_broker_order_lifecycle(
        repository=repository,
        order_id="latest",
        now=now,
        broker="binance_testnet",
        broker_mode="SANDBOX",
    )
    second = create_broker_order_lifecycle(
        repository=repository,
        order_id="latest",
        now=now,
        broker="binance_testnet",
        broker_mode="SANDBOX",
    )

    assert first.status == "created"
    assert second.status == "skipped"
    assert second.reason == "duplicate_broker_order"
    assert len(repository.load_broker_orders()) == 1


def test_broker_order_lifecycle_blocks_live_mode(tmp_path):
    now = datetime(2026, 4, 25, 7, 0, tzinfo=UTC)
    repository = _repository(tmp_path, now)

    with pytest.raises(ValueError, match="Live trading is unavailable"):
        create_broker_order_lifecycle(
            repository=repository,
            order_id="latest",
            now=now,
            broker="binance",
            broker_mode="LIVE",
        )

    assert repository.load_broker_orders() == []


def test_cli_broker_order_records_rejected_lifecycle(tmp_path, capsys):
    now = datetime(2026, 4, 25, 7, 0, tzinfo=UTC)
    _repository(tmp_path, now)

    exit_code = main(
        [
            "broker-order",
            "--storage-dir",
            str(tmp_path),
            "--order-id",
            "latest",
            "--mock-submit-status",
            "REJECTED",
            "--now",
            now.isoformat(),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "created"
    assert payload["broker_order"]["status"] == "REJECTED"
    assert payload["broker_order"]["raw_response"]["mock"] is True


def test_cli_broker_order_rejects_live_mode_before_writing(tmp_path, capsys):
    now = datetime(2026, 4, 25, 7, 0, tzinfo=UTC)
    _repository(tmp_path, now)

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "broker-order",
                "--storage-dir",
                str(tmp_path),
                "--order-id",
                "latest",
                "--broker-mode",
                "LIVE",
                "--now",
                now.isoformat(),
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "invalid choice" in captured.err
    assert "LIVE" in captured.err
    assert not (tmp_path / "broker_orders.jsonl").exists()


def test_health_check_audits_bad_and_duplicate_broker_orders(tmp_path):
    now = datetime(2026, 4, 25, 7, 0, tzinfo=UTC)
    repository = _repository(tmp_path, now)
    result = create_broker_order_lifecycle(
        repository=repository,
        order_id="latest",
        now=now,
        broker="binance_testnet",
        broker_mode="SANDBOX",
    )
    payload = result.broker_order.to_dict()
    (tmp_path / "broker_orders.jsonl").write_text(
        "\n".join([json.dumps(payload), json.dumps(payload), "{bad json"]) + "\n",
        encoding="utf-8",
    )

    health = run_health_check(
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=now,
        create_repair_request=False,
    )
    codes = {finding.code for finding in health.findings}

    assert health.repair_required is True
    assert "bad_json_row" in codes
    assert "duplicate_broker_order_id" in codes
