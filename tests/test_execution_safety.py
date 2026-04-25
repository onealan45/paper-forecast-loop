from datetime import UTC, datetime, timedelta
import json

import pytest

from forecast_loop.cli import main
from forecast_loop.health import run_health_check
from forecast_loop.models import (
    BrokerOrder,
    BrokerOrderStatus,
    BrokerReconciliation,
    Forecast,
    PaperOrder,
    PaperOrderStatus,
    PaperOrderType,
    RiskSnapshot,
    StrategyDecision,
)
from forecast_loop.storage import JsonFileRepository


def _forecast(now: datetime, symbol: str = "BTC-USD") -> Forecast:
    return Forecast(
        forecast_id=f"forecast:{symbol}",
        symbol=symbol,
        created_at=now,
        anchor_time=now,
        target_window_start=now,
        target_window_end=now + timedelta(hours=24),
        candle_interval_minutes=60,
        expected_candle_count=25,
        status="pending",
        status_reason="awaiting_horizon_end",
        predicted_regime="trend_up",
        confidence=0.7,
        provider_data_through=now,
        observed_candle_count=0,
    )


def _decision(now: datetime, symbol: str = "BTC-USD", *, evidence_grade: str = "B") -> StrategyDecision:
    return StrategyDecision(
        decision_id=f"decision:{symbol}",
        created_at=now,
        symbol=symbol,
        horizon_hours=24,
        action="BUY",
        confidence=0.7,
        evidence_grade=evidence_grade,
        risk_level="LOW",
        tradeable=True,
        blocked_reason=None,
        recommended_position_pct=0.08,
        current_position_pct=0.0,
        max_position_pct=0.15,
        invalidation_conditions=["test"],
        reason_summary="execution gate test",
        forecast_ids=[f"forecast:{symbol}"],
        score_ids=[],
        review_ids=[],
        baseline_ids=[],
        decision_basis="test",
    )


def _order(now: datetime, decision: StrategyDecision) -> PaperOrder:
    return PaperOrder(
        order_id=f"paper-order:{decision.symbol}",
        created_at=now,
        decision_id=decision.decision_id,
        symbol=decision.symbol,
        side="BUY",
        order_type=PaperOrderType.TARGET_PERCENT.value,
        status=PaperOrderStatus.CREATED.value,
        target_position_pct=decision.recommended_position_pct,
        current_position_pct=decision.current_position_pct,
        max_position_pct=decision.max_position_pct,
        rationale="execution gate test",
    )


def _risk(now: datetime, symbol: str = "BTC-USD", *, severity: str = "none") -> RiskSnapshot:
    return RiskSnapshot(
        risk_id=f"risk:{symbol}:{severity}",
        created_at=now,
        symbol=symbol,
        status="OK" if severity == "none" else "REDUCE_RISK",
        severity=severity,
        current_drawdown_pct=0.0,
        max_drawdown_pct=0.0,
        gross_exposure_pct=0.08,
        net_exposure_pct=0.08,
        position_pct=0.0,
        max_position_pct=0.15,
        max_gross_exposure_pct=0.2,
        reduce_risk_drawdown_pct=0.05,
        stop_new_entries_drawdown_pct=0.1,
        findings=[] if severity == "none" else ["test risk warning"],
        recommended_action="HOLD",
        decision_basis="test",
    )


def _reconciliation(now: datetime, *, repair_required: bool = False) -> BrokerReconciliation:
    return BrokerReconciliation(
        reconciliation_id="broker-reconciliation:execution-gate",
        created_at=now,
        broker="binance_testnet",
        broker_mode="SANDBOX",
        status="MATCHED" if not repair_required else "MISMATCH",
        severity="none" if not repair_required else "blocking",
        repair_required=repair_required,
        local_broker_order_ids=[],
        external_order_refs=[],
        matched_order_refs=[],
        missing_external_order_ids=[],
        unknown_external_order_refs=[],
        duplicate_broker_order_refs=[],
        status_mismatches=[],
        position_mismatches=[],
        cash_mismatch=None,
        equity_mismatch=None,
        findings=[] if not repair_required else [{"code": "test"}],
        decision_basis="test",
    )


def _seed_ready_storage(tmp_path, now: datetime, symbol: str = "BTC-USD", *, evidence_grade: str = "B"):
    repository = JsonFileRepository(tmp_path)
    forecast = _forecast(now, symbol)
    decision = _decision(now, symbol, evidence_grade=evidence_grade)
    order = _order(now, decision)
    repository.save_forecast(forecast)
    repository.save_strategy_decision(decision)
    repository.save_paper_order(order)
    repository.save_risk_snapshot(_risk(now, symbol))
    repository.save_broker_reconciliation(_reconciliation(now))
    (tmp_path / "dashboard.html").write_text("Dashboard 產生時間", encoding="utf-8")
    return repository, decision, order


def _broker_health_file(tmp_path, *, status: str = "healthy", live_available: bool = False) -> str:
    path = tmp_path / "broker_health.json"
    path.write_text(
        json.dumps(
            {
                "status": status,
                "mode": "SANDBOX",
                "broker": "binance_testnet",
                "live_trading_available": live_available,
            }
        ),
        encoding="utf-8",
    )
    return str(path)


def test_cli_execution_gate_passes_when_all_safety_inputs_clear(tmp_path, capsys):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_ready_storage(tmp_path, now)

    exit_code = main(
        [
            "execution-gate",
            "--storage-dir",
            str(tmp_path),
            "--broker-health",
            _broker_health_file(tmp_path),
            "--now",
            now.isoformat(),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "PASS"
    assert payload["allowed"] is True
    assert JsonFileRepository(tmp_path).load_execution_safety_gates()[0].gate_id == payload["gate_id"]


def test_execution_gate_blocks_weak_evidence_and_duplicate_broker_order(tmp_path, capsys):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository, _, order = _seed_ready_storage(tmp_path, now, evidence_grade="D")
    repository.save_broker_order(
        BrokerOrder(
            broker_order_id="broker-order:duplicate",
            created_at=now,
            updated_at=now,
            local_order_id=order.order_id,
            decision_id=order.decision_id,
            symbol=order.symbol,
            side=order.side,
            quantity=None,
            target_position_pct=order.target_position_pct,
            broker="binance_testnet",
            broker_mode="SANDBOX",
            status=BrokerOrderStatus.ACKNOWLEDGED.value,
            broker_status="ACKNOWLEDGED",
            broker_order_ref="external:duplicate",
            client_order_id=order.order_id,
            error_message=None,
            raw_response={"mock": True},
            decision_basis="test",
        )
    )

    exit_code = main(
        [
            "execution-gate",
            "--storage-dir",
            str(tmp_path),
            "--broker-health",
            _broker_health_file(tmp_path),
            "--now",
            now.isoformat(),
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    failed_codes = {check["code"] for check in payload["checks"] if check["status"] == "fail"}

    assert exit_code == 2
    assert payload["status"] == "BLOCKED"
    assert "evidence_grade" in failed_codes
    assert "duplicate_active_broker_order" in failed_codes


def test_execution_gate_blocks_unhealthy_broker_and_closed_stock_market(tmp_path, capsys):
    saturday = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    _seed_ready_storage(tmp_path, saturday, symbol="SPY")

    exit_code = main(
        [
            "execution-gate",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "SPY",
            "--broker-health",
            _broker_health_file(tmp_path, status="unhealthy", live_available=True),
            "--now",
            saturday.isoformat(),
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    failed_codes = {check["code"] for check in payload["checks"] if check["status"] == "fail"}

    assert exit_code == 2
    assert "broker_health" in failed_codes
    assert "broker_live_unavailable" in failed_codes
    assert "market_open" in failed_codes


def test_cli_execution_gate_rejects_live_mode_before_writing(tmp_path, capsys):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_ready_storage(tmp_path, now)

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "execution-gate",
                "--storage-dir",
                str(tmp_path),
                "--broker-health",
                _broker_health_file(tmp_path),
                "--broker-mode",
                "LIVE",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "invalid choice" in captured.err
    assert "LIVE" in captured.err
    assert not (tmp_path / "execution_safety_gates.jsonl").exists()


def test_health_check_audits_bad_and_duplicate_execution_gates(tmp_path):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_ready_storage(tmp_path, now)
    assert main(
        [
            "execution-gate",
            "--storage-dir",
            str(tmp_path),
            "--broker-health",
            _broker_health_file(tmp_path),
            "--now",
            now.isoformat(),
        ]
    ) == 0
    payload = (tmp_path / "execution_safety_gates.jsonl").read_text(encoding="utf-8").splitlines()[0]
    (tmp_path / "execution_safety_gates.jsonl").write_text(f"{payload}\n{payload}\n{{bad json\n", encoding="utf-8")

    health = run_health_check(
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=now,
        create_repair_request=False,
    )
    codes = {finding.code for finding in health.findings}

    assert "bad_json_row" in codes
    assert "duplicate_gate_id" in codes
