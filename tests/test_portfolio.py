from datetime import UTC, datetime, timedelta
import json

from forecast_loop.cli import main
from forecast_loop.models import Forecast, PaperOrder, PaperOrderStatus, PaperOrderType, StrategyDecision
from forecast_loop.portfolio import create_portfolio_snapshot, fill_paper_order, save_portfolio_mark
from forecast_loop.storage import JsonFileRepository


def _forecast(now: datetime) -> Forecast:
    return Forecast(
        forecast_id="forecast:fill",
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
        confidence=0.7,
        provider_data_through=now,
        observed_candle_count=0,
    )


def _decision(now: datetime, decision_id: str = "decision:fill") -> StrategyDecision:
    return StrategyDecision(
        decision_id=decision_id,
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
        reason_summary="test tradeable decision",
        forecast_ids=["forecast:fill"],
        score_ids=[],
        review_ids=[],
        baseline_ids=[],
        decision_basis="test",
    )


def _order(now: datetime, decision: StrategyDecision, *, order_id: str = "paper-order:fill") -> PaperOrder:
    return PaperOrder(
        order_id=order_id,
        created_at=now,
        decision_id=decision.decision_id,
        symbol="BTC-USD",
        side="BUY",
        order_type=PaperOrderType.TARGET_PERCENT.value,
        status=PaperOrderStatus.CREATED.value,
        target_position_pct=0.15,
        current_position_pct=0.0,
        max_position_pct=0.15,
        rationale="test",
    )


def _sell_order(
    now: datetime,
    decision: StrategyDecision,
    *,
    order_id: str = "paper-order:sell",
    target_position_pct: float = 0.0,
) -> PaperOrder:
    return PaperOrder(
        order_id=order_id,
        created_at=now,
        decision_id=decision.decision_id,
        symbol="BTC-USD",
        side="SELL",
        order_type=PaperOrderType.TARGET_PERCENT.value,
        status=PaperOrderStatus.CREATED.value,
        target_position_pct=target_position_pct,
        current_position_pct=0.15,
        max_position_pct=0.15,
        rationale="test sell",
    )


def _healthy_repository(tmp_path, now: datetime) -> tuple[JsonFileRepository, PaperOrder]:
    repository = JsonFileRepository(tmp_path)
    decision = _decision(now)
    order = _order(now, decision)
    repository.save_forecast(_forecast(now))
    repository.save_strategy_decision(decision)
    repository.save_paper_order(order)
    return repository, order


def test_fill_paper_order_writes_fill_snapshot_equity_curve_and_marks_order_filled(tmp_path):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository, order = _healthy_repository(tmp_path, now)

    result = fill_paper_order(
        repository=repository,
        order_id=order.order_id,
        now=now,
        market_price=100.0,
        fee_bps=5.0,
        slippage_bps=10.0,
    )

    assert result.status == "filled"
    assert result.fill is not None
    assert result.fill.fill_price == 100.1
    assert result.fill.gross_value == 1500.0
    assert result.fill.fee == 0.75
    assert result.portfolio_snapshot is not None
    assert result.portfolio_snapshot.cash == 8499.25
    assert round(result.portfolio_snapshot.equity, 2) == 9997.75
    assert len(result.portfolio_snapshot.positions) == 1
    assert repository.load_paper_orders()[0].status == PaperOrderStatus.FILLED.value
    assert repository.load_paper_fills() == [result.fill]
    assert repository.load_portfolio_snapshots()[-1] == result.portfolio_snapshot
    assert repository.load_equity_curve_points()[-1] == result.equity_curve_point


def test_fill_paper_order_skips_already_filled_order(tmp_path):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository, order = _healthy_repository(tmp_path, now)
    first = fill_paper_order(repository=repository, order_id=order.order_id, now=now)
    second = fill_paper_order(repository=repository, order_id=order.order_id, now=now)

    assert first.status == "filled"
    assert second.status == "skipped"
    assert second.reason == "order_not_open"
    assert len(repository.load_paper_fills()) == 1


def test_portfolio_snapshot_marks_existing_position_to_market(tmp_path):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository, order = _healthy_repository(tmp_path, now)
    fill_paper_order(repository=repository, order_id=order.order_id, now=now, market_price=100.0)

    snapshot = create_portfolio_snapshot(
        repository=repository,
        now=now + timedelta(hours=1),
        market_price=110.0,
        symbol="BTC-USD",
    )
    point = save_portfolio_mark(repository, snapshot)

    assert snapshot.positions[0].market_price == 110.0
    assert snapshot.unrealized_pnl > 0
    assert snapshot.equity > repository.load_portfolio_snapshots()[0].equity
    assert point.equity == snapshot.equity


def test_sell_fill_full_exit_uses_capped_quantity_for_cash_nav_and_realized_pnl(tmp_path):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository, buy_order = _healthy_repository(tmp_path, now)
    buy = fill_paper_order(
        repository=repository,
        order_id=buy_order.order_id,
        now=now,
        market_price=100.0,
        fee_bps=0.0,
        slippage_bps=0.0,
    )
    assert buy.status == "filled"
    decision = _decision(now, decision_id="decision:sell")
    sell_order = _sell_order(now, decision)
    repository.save_strategy_decision(decision)
    repository.save_paper_order(sell_order)

    sell = fill_paper_order(
        repository=repository,
        order_id=sell_order.order_id,
        now=now + timedelta(hours=1),
        market_price=100.0,
        fee_bps=0.0,
        slippage_bps=10.0,
    )

    assert sell.status == "filled"
    assert sell.fill is not None
    assert round(sell.fill.quantity, 10) == round(15.0, 10)
    assert sell.fill.fill_price == 99.9
    assert sell.fill.gross_value == 1498.5
    assert sell.portfolio_snapshot is not None
    assert sell.portfolio_snapshot.positions == []
    assert sell.portfolio_snapshot.cash == 9998.5
    assert sell.portfolio_snapshot.equity == sell.portfolio_snapshot.cash
    assert sell.portfolio_snapshot.nav == sell.portfolio_snapshot.equity
    assert abs(sell.portfolio_snapshot.realized_pnl - (-1.5)) < 1e-9


def test_sell_fill_partial_reduce_reconciles_cash_remaining_position_and_nav(tmp_path):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository, buy_order = _healthy_repository(tmp_path, now)
    buy = fill_paper_order(
        repository=repository,
        order_id=buy_order.order_id,
        now=now,
        market_price=100.0,
        fee_bps=0.0,
        slippage_bps=0.0,
    )
    assert buy.status == "filled"
    decision = _decision(now, decision_id="decision:reduce")
    sell_order = _sell_order(now, decision, order_id="paper-order:reduce", target_position_pct=0.05)
    repository.save_strategy_decision(decision)
    repository.save_paper_order(sell_order)

    sell = fill_paper_order(
        repository=repository,
        order_id=sell_order.order_id,
        now=now + timedelta(hours=1),
        market_price=100.0,
        fee_bps=5.0,
        slippage_bps=10.0,
    )

    assert sell.status == "filled"
    assert sell.fill is not None
    snapshot = sell.portfolio_snapshot
    assert snapshot is not None
    assert len(snapshot.positions) == 1
    remaining_market_value = snapshot.positions[0].market_value
    assert abs((snapshot.cash + remaining_market_value) - snapshot.equity) < 1e-9
    assert snapshot.nav == snapshot.equity
    assert sell.fill.fee > 0
    assert snapshot.realized_pnl < 0


def test_cli_paper_fill_and_portfolio_snapshot(tmp_path, capsys):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _healthy_repository(tmp_path, now)

    fill_exit = main(
        [
            "paper-fill",
            "--storage-dir",
            str(tmp_path),
            "--order-id",
            "latest",
            "--market-price",
            "100",
            "--now",
            now.isoformat(),
        ]
    )
    fill_payload = json.loads(capsys.readouterr().out)
    snapshot_exit = main(
        [
            "portfolio-snapshot",
            "--storage-dir",
            str(tmp_path),
            "--market-price",
            "105",
            "--now",
            (now + timedelta(hours=1)).isoformat(),
        ]
    )
    snapshot_payload = json.loads(capsys.readouterr().out)

    assert fill_exit == 0
    assert fill_payload["status"] == "filled"
    assert snapshot_exit == 0
    assert snapshot_payload["status"] == "created"
    assert snapshot_payload["portfolio_snapshot"]["positions"][0]["market_price"] == 105.0


def test_cli_paper_fill_skips_when_health_is_blocking(tmp_path, capsys):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _healthy_repository(tmp_path, now)
    (tmp_path / "paper_fills.jsonl").write_text("{bad json\n", encoding="utf-8")

    exit_code = main(
        [
            "paper-fill",
            "--storage-dir",
            str(tmp_path),
            "--order-id",
            "latest",
            "--now",
            now.isoformat(),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "skipped"
    assert payload["reason"] == "health_blocking"
    assert (tmp_path / "paper_fills.jsonl").read_text(encoding="utf-8") == "{bad json\n"
