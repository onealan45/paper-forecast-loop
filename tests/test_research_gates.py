from datetime import UTC, datetime, timedelta

from forecast_loop.decision import generate_strategy_decision
from forecast_loop.models import BacktestResult, BacktestRun, EventEdgeEvaluation, WalkForwardValidation, WalkForwardWindow
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


def _backtest_run(
    now: datetime,
    *,
    backtest_id: str,
    id_context: str,
) -> BacktestRun:
    return BacktestRun(
        backtest_id=backtest_id,
        created_at=now,
        symbol="BTC-USD",
        start=now - timedelta(days=10),
        end=now,
        strategy_name="moving_average_trend",
        initial_cash=10_000,
        fee_bps=5,
        slippage_bps=10,
        moving_average_window=3,
        candle_ids=["market-candle:gate"],
        decision_basis=(
            "paper-only moving-average trend backtest using stored candles; "
            f"id_context={id_context}"
        ),
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


def _event_edge(
    now: datetime,
    *,
    evaluation_id: str = "event-edge:gate",
    passed: bool = True,
    average_excess_return_after_costs: float = 0.02,
) -> EventEdgeEvaluation:
    return EventEdgeEvaluation(
        evaluation_id=evaluation_id,
        event_family="crypto_flow",
        event_type="CRYPTO_FLOW",
        symbol="BTC-USD",
        created_at=now,
        split="historical_event_sample",
        horizon_hours=24,
        sample_n=5,
        average_forward_return=0.03,
        average_benchmark_return=0.0,
        average_excess_return_after_costs=average_excess_return_after_costs,
        hit_rate=0.6,
        max_adverse_excursion_p50=-0.01,
        max_adverse_excursion_p90=-0.03,
        max_drawdown_if_traded=-0.05,
        turnover=5.0,
        estimated_cost_bps=10.0,
        dsr=None,
        white_rc_p=None,
        stability_score=None,
        passed=passed,
        blocked_reason=None if passed else "non_positive_after_cost_edge",
        flags=[] if passed else ["non_positive_after_cost_edge"],
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
    repository.save_event_edge_evaluation(_event_edge(now))

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
    assert "event_edge=event-edge:gate" in decision.decision_basis


def test_research_gate_blocks_buy_when_event_edge_missing(tmp_path):
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

    assert decision.action == "HOLD"
    assert decision.tradeable is False
    assert decision.blocked_reason == "research_event_edge_missing"
    assert "event_edge=missing" in decision.decision_basis


def test_research_gate_blocks_buy_when_event_edge_fails(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_strong_directional_context(repository, now)
    repository.save_backtest_result(_backtest(now))
    repository.save_walk_forward_validation(_walk_forward(now))
    repository.save_event_edge_evaluation(
        _event_edge(
            now,
            evaluation_id="event-edge:failed",
            passed=False,
            average_excess_return_after_costs=-0.01,
        )
    )

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
        risk_snapshot=_ok_risk(now),
    )

    assert decision.action == "HOLD"
    assert decision.tradeable is False
    assert decision.blocked_reason == "research_event_edge_not_passed"
    assert "event_edge=event-edge:failed" in decision.decision_basis
    assert "research_event_edge_not_positive" in decision.decision_basis


def test_research_gate_blocks_buy_when_backtest_missing(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_strong_directional_context(repository, now)
    repository.save_walk_forward_validation(_walk_forward(now))
    repository.save_event_edge_evaluation(_event_edge(now))

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
    repository.save_event_edge_evaluation(_event_edge(now))

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
    repository.save_event_edge_evaluation(_event_edge(now))

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
        risk_snapshot=_ok_risk(now),
    )

    assert decision.action == "BUY"
    assert "backtest_result=backtest-result:newer" in decision.decision_basis


def test_research_gate_prefers_decision_blocker_backtest_over_newer_walk_forward_internal_backtest(
    tmp_path,
):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_strong_directional_context(repository, now)
    standalone = _backtest(
        now,
        result_id="backtest-result:blocker-standalone",
        drawdown=0.05,
    )
    internal = _backtest(
        now + timedelta(minutes=1),
        result_id="backtest-result:walk-forward-internal",
        drawdown=0.05,
    )
    repository.save_backtest_run(
        _backtest_run(
            now,
            backtest_id=standalone.backtest_id,
            id_context="decision_blocker_research:run_backtest:backtest_result",
        )
    )
    repository.save_backtest_run(
        _backtest_run(
            now + timedelta(minutes=1),
            backtest_id=internal.backtest_id,
            id_context="decision_blocker_research:run_walk_forward_validation:walk_forward_validation",
        )
    )
    repository.save_backtest_result(standalone)
    repository.save_backtest_result(internal)
    repository.save_walk_forward_validation(_walk_forward(now + timedelta(minutes=1)))
    repository.save_event_edge_evaluation(_event_edge(now))

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now + timedelta(minutes=2),
        risk_snapshot=_ok_risk(now + timedelta(minutes=2)),
    )

    assert "backtest_result=backtest-result:blocker-standalone" in decision.decision_basis
    assert "backtest_result=backtest-result:walk-forward-internal" not in decision.decision_basis
