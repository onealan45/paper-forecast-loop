from datetime import UTC, datetime, timedelta
import json

from forecast_loop.cli import main
from forecast_loop.models import Forecast, PaperOrderStatus, StrategyDecision
from forecast_loop.orders import create_paper_order_from_decision
from forecast_loop.storage import JsonFileRepository


def _forecast(now: datetime) -> Forecast:
    return Forecast(
        forecast_id="forecast:order",
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
    action: str,
    tradeable: bool,
    blocked_reason: str | None = None,
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
        tradeable=tradeable,
        blocked_reason=blocked_reason,
        recommended_position_pct=recommended_position_pct,
        current_position_pct=0.0,
        max_position_pct=0.15,
        invalidation_conditions=["test"],
        reason_summary=f"{action} test decision",
        forecast_ids=["forecast:order"],
        score_ids=[],
        review_ids=[],
        baseline_ids=[],
        decision_basis="test",
    )


def _healthy_repository(tmp_path, decision: StrategyDecision) -> JsonFileRepository:
    repository = JsonFileRepository(tmp_path)
    repository.save_forecast(_forecast(decision.created_at))
    repository.save_strategy_decision(decision)
    return repository


def test_paper_order_created_for_tradeable_buy_decision(tmp_path):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    decision = _decision("decision:buy", now=now, action="BUY", tradeable=True)
    repository = _healthy_repository(tmp_path, decision)

    result = create_paper_order_from_decision(
        repository=repository,
        decision_id="latest",
        symbol="BTC-USD",
        now=now,
    )

    assert result.status == "created"
    assert result.order is not None
    assert result.order.side == "BUY"
    assert result.order.status == PaperOrderStatus.CREATED.value
    assert result.order.target_position_pct == 0.15
    assert repository.load_paper_orders() == [result.order]


def test_paper_order_skips_hold_and_stop_new_entries(tmp_path):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository = _healthy_repository(
        tmp_path,
        _decision("decision:hold", now=now, action="HOLD", tradeable=False, blocked_reason="insufficient_evidence"),
    )
    repository.save_strategy_decision(
        _decision(
            "decision:stop",
            now=now,
            action="STOP_NEW_ENTRIES",
            tradeable=False,
            blocked_reason="health_check_repair_required",
            recommended_position_pct=0.0,
        )
    )

    hold_result = create_paper_order_from_decision(
        repository=repository,
        decision_id="decision:hold",
        symbol="BTC-USD",
        now=now,
    )
    stop_result = create_paper_order_from_decision(
        repository=repository,
        decision_id="decision:stop",
        symbol="BTC-USD",
        now=now,
    )

    assert hold_result.status == "skipped"
    assert hold_result.reason == "action_creates_no_order"
    assert stop_result.status == "skipped"
    assert stop_result.reason == "action_creates_no_order"
    assert repository.load_paper_orders() == []


def test_paper_order_skips_non_tradeable_directional_decision(tmp_path):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository = _healthy_repository(
        tmp_path,
        _decision("decision:blocked-buy", now=now, action="BUY", tradeable=False, blocked_reason="model_not_beating_baseline"),
    )

    result = create_paper_order_from_decision(
        repository=repository,
        decision_id="latest",
        symbol="BTC-USD",
        now=now,
    )

    assert result.status == "skipped"
    assert result.reason == "decision_not_tradeable"
    assert repository.load_paper_orders() == []


def test_cli_paper_order_skips_when_health_is_blocking(tmp_path, capsys):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository = _healthy_repository(
        tmp_path,
        _decision("decision:buy", now=now, action="BUY", tradeable=True),
    )
    (tmp_path / "forecasts.jsonl").write_text("{bad json\n", encoding="utf-8")

    exit_code = main(
        [
            "paper-order",
            "--storage-dir",
            str(tmp_path),
            "--decision-id",
            "latest",
            "--now",
            now.isoformat(),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "skipped"
    assert payload["reason"] == "health_blocking"
    assert not (tmp_path / "paper_orders.jsonl").exists()


def test_cli_paper_order_skips_when_order_ledger_is_corrupt(tmp_path, capsys):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository = _healthy_repository(
        tmp_path,
        _decision("decision:buy", now=now, action="BUY", tradeable=True),
    )
    (tmp_path / "paper_orders.jsonl").write_text("{bad json\n", encoding="utf-8")

    exit_code = main(
        [
            "paper-order",
            "--storage-dir",
            str(tmp_path),
            "--decision-id",
            "latest",
            "--now",
            now.isoformat(),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "skipped"
    assert payload["reason"] == "health_blocking"
    assert (tmp_path / "paper_orders.jsonl").read_text(encoding="utf-8") == "{bad json\n"


def test_cli_paper_order_blocks_duplicate_active_order(tmp_path, capsys):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository = _healthy_repository(
        tmp_path,
        _decision("decision:buy", now=now, action="BUY", tradeable=True),
    )

    first_exit = main(
        [
            "paper-order",
            "--storage-dir",
            str(tmp_path),
            "--decision-id",
            "latest",
            "--now",
            now.isoformat(),
        ]
    )
    first_payload = json.loads(capsys.readouterr().out)
    second_exit = main(
        [
            "paper-order",
            "--storage-dir",
            str(tmp_path),
            "--decision-id",
            "latest",
            "--now",
            now.isoformat(),
        ]
    )
    second_payload = json.loads(capsys.readouterr().out)

    assert first_exit == 0
    assert first_payload["status"] == "created"
    assert second_exit == 0
    assert second_payload["status"] == "skipped"
    assert second_payload["reason"] == "duplicate_active_order"
    assert second_payload["active_order_id"] == first_payload["order_id"]
    assert len(repository.load_paper_orders()) == 1


def test_cli_paper_order_reduce_risk_creates_sell_target_percent_order(tmp_path, capsys):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _healthy_repository(
        tmp_path,
        _decision(
            "decision:reduce",
            now=now,
            action="REDUCE_RISK",
            tradeable=True,
            recommended_position_pct=0.05,
        ),
    )

    exit_code = main(
        [
            "paper-order",
            "--storage-dir",
            str(tmp_path),
            "--decision-id",
            "latest",
            "--now",
            now.isoformat(),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "created"
    assert payload["order"]["side"] == "SELL"
    assert payload["order"]["target_position_pct"] == 0.05
