from datetime import UTC, datetime, timedelta

from forecast_loop.decision import generate_strategy_decision
from forecast_loop.models import BacktestResult, WalkForwardValidation, WalkForwardWindow
from forecast_loop.storage import JsonFileRepository
from tests.test_m1_strategy import _forecast, _ok_risk, _seed_scores


def _backtest(now: datetime, *, result_id: str = "backtest-result:gate", drawdown: float = 0.05) -> BacktestResult:
    return BacktestResult(
        result_id=result_id,
        backtest_id=f"backtest-run:{result_id}",
        created_at=now,
        symbol="BTC-USD",
        start=now - timedelta(days=10),
        end=now,
        initial_cash=10_000,
        final_equity=10_200,
        strategy_return=0.02,
        benchmark_return=0.01,
        max_drawdown=drawdown,
        sharpe=1.0,
        turnover=0.5,
        win_rate=0.6,
        trade_count=3,
        equity_curve=[],
        decision_basis="test",
    )


def _walk_forward(
    now: datetime,
    *,
    validation_id: str = "walk-forward:gate",
    average_excess_return: float = 0.01,
    overfit_flags: list[str] | None = None,
) -> WalkForwardValidation:
    window = WalkForwardWindow(
        window_id=f"{validation_id}:window",
        train_start=now - timedelta(days=9),
        train_end=now - timedelta(days=7),
        validation_start=now - timedelta(days=6),
        validation_end=now - timedelta(days=4),
        test_start=now - timedelta(days=3),
        test_end=now,
        train_candle_count=3,
        validation_candle_count=3,
        test_candle_count=3,
        validation_backtest_result_id="backtest-result:gate",
        test_backtest_result_id="backtest-result:gate",
        validation_return=0.02,
        test_return=0.02,
        benchmark_return=0.01,
        excess_return=average_excess_return,
        overfit_flags=overfit_flags or [],
        decision_basis="test",
    )
    return WalkForwardValidation(
        validation_id=validation_id,
        created_at=now,
        symbol="BTC-USD",
        start=now - timedelta(days=9),
        end=now,
        strategy_name="moving_average_trend",
        train_size=3,
        validation_size=3,
        test_size=3,
        step_size=1,
        initial_cash=10_000,
        fee_bps=5,
        slippage_bps=10,
        moving_average_window=2,
        window_count=1,
        average_validation_return=0.02,
        average_test_return=0.02,
        average_benchmark_return=0.01,
        average_excess_return=average_excess_return,
        test_win_rate=1.0,
        overfit_window_count=1 if overfit_flags else 0,
        overfit_risk_flags=overfit_flags or [],
        backtest_result_ids=["backtest-result:gate"],
        windows=[window],
        decision_basis="test",
    )


def _seed_strong_directional_context(repository: JsonFileRepository, now: datetime, *, predicted_regime: str = "trend_up") -> None:
    _seed_scores(
        repository,
        actuals=["trend_up", "trend_up", "trend_down", "trend_up", "trend_down", "trend_down"],
        hits=[True, True, True, True, True, True],
    )
    latest = _forecast(
        "forecast:latest",
        anchor_time=now,
        predicted_regime=predicted_regime,
        status="pending",
    )
    repository.save_forecast(latest)


def test_research_gate_allows_buy_when_quality_artifacts_pass(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_strong_directional_context(repository, now)
    repository.save_backtest_result(_backtest(now))
    repository.save_walk_forward_validation(_walk_forward(now))

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
        risk_snapshot=_ok_risk(now),
    )

    assert decision.action == "BUY"
    assert decision.tradeable is True
    assert decision.blocked_reason is None
    assert "research_gate=" in decision.decision_basis
    assert "flags=none" in decision.decision_basis


def test_research_gate_blocks_buy_when_backtest_missing(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_strong_directional_context(repository, now)
    repository.save_walk_forward_validation(_walk_forward(now))

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
        risk_snapshot=_ok_risk(now),
    )

    assert decision.action == "HOLD"
    assert decision.tradeable is False
    assert decision.blocked_reason == "research_backtest_missing"


def test_research_gate_reduces_risk_when_walk_forward_overfit_flags_exist(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_strong_directional_context(repository, now)
    repository.save_backtest_result(_backtest(now))
    repository.save_walk_forward_validation(
        _walk_forward(now, overfit_flags=["aggregate_underperforms_benchmark"])
    )

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
        risk_snapshot=_ok_risk(now),
    )

    assert decision.action == "REDUCE_RISK"
    assert decision.tradeable is False
    assert decision.blocked_reason == "research_reduce_required_but_no_position"
    assert decision.risk_level == "HIGH"
    assert "research_walk_forward_overfit_risk" in decision.decision_basis


def test_research_gate_uses_latest_research_artifacts_by_created_at(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_strong_directional_context(repository, now)
    newer = _backtest(now, result_id="backtest-result:newer", drawdown=0.05)
    older = _backtest(now - timedelta(days=1), result_id="backtest-result:older", drawdown=0.50)
    repository.save_backtest_result(newer)
    repository.save_backtest_result(older)
    repository.save_walk_forward_validation(_walk_forward(now))

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
        risk_snapshot=_ok_risk(now),
    )

    assert decision.action == "BUY"
    assert "backtest_result=backtest-result:newer" in decision.decision_basis
