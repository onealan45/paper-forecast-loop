from datetime import UTC, datetime, timedelta

from forecast_loop.models import (
    BacktestRun,
    BacktestResult,
    EventEdgeEvaluation,
    StrategyResearchDigest,
    WalkForwardValidation,
)
from forecast_loop.strategy_digest_evidence import resolve_strategy_digest_evidence


def _digest(now: datetime, *, evidence_ids: list[str] | None = None) -> StrategyResearchDigest:
    return StrategyResearchDigest(
        digest_id="strategy-research-digest:evidence",
        created_at=now,
        symbol="BTC-USD",
        strategy_card_id=None,
        strategy_name="Evidence digest",
        strategy_status=None,
        hypothesis="Inspect evidence.",
        paper_shadow_outcome_id=None,
        outcome_grade=None,
        excess_return_after_costs=None,
        recommended_strategy_action=None,
        top_failure_attributions=[],
        lineage_root_card_id=None,
        lineage_revision_count=0,
        lineage_outcome_count=0,
        lineage_primary_failure_attribution=None,
        lineage_next_research_focus=None,
        next_research_action=None,
        autopilot_run_id=None,
        evidence_artifact_ids=evidence_ids or [],
        research_summary="test",
        next_step_rationale="test",
        decision_basis="test",
    )


def _event_edge(now: datetime, *, evaluation_id: str, symbol: str = "BTC-USD") -> EventEdgeEvaluation:
    return EventEdgeEvaluation(
        evaluation_id=evaluation_id,
        event_family="crypto_flow",
        event_type="CRYPTO_FLOW",
        symbol=symbol,
        created_at=now,
        split="historical_event_sample",
        horizon_hours=24,
        sample_n=2,
        average_forward_return=-0.02,
        average_benchmark_return=-0.008,
        average_excess_return_after_costs=-0.01,
        hit_rate=0.0,
        max_adverse_excursion_p50=None,
        max_adverse_excursion_p90=None,
        max_drawdown_if_traded=None,
        turnover=None,
        estimated_cost_bps=15.0,
        dsr=None,
        white_rc_p=None,
        stability_score=None,
        passed=False,
        blocked_reason="non_positive_after_cost_edge",
        flags=["non_positive_after_cost_edge"],
    )


def _backtest(now: datetime, *, result_id: str, symbol: str = "BTC-USD") -> BacktestResult:
    return BacktestResult(
        result_id=result_id,
        backtest_id=f"backtest-run:{result_id}",
        created_at=now,
        symbol=symbol,
        start=now - timedelta(days=10),
        end=now,
        initial_cash=10_000,
        final_equity=9_900,
        strategy_return=-0.01,
        benchmark_return=0.01,
        max_drawdown=0.02,
        sharpe=None,
        turnover=0.5,
        win_rate=0.25,
        trade_count=4,
        equity_curve=[],
        decision_basis="test",
    )


def _backtest_run(backtest: BacktestResult, *, decision_basis: str) -> BacktestRun:
    return BacktestRun(
        backtest_id=backtest.backtest_id,
        created_at=backtest.created_at,
        symbol=backtest.symbol,
        start=backtest.start,
        end=backtest.end,
        strategy_name="moving_average_trend",
        initial_cash=backtest.initial_cash,
        fee_bps=5,
        slippage_bps=10,
        moving_average_window=24,
        candle_ids=[f"candle:{backtest.result_id}"],
        decision_basis=decision_basis,
    )


def _walk_forward(now: datetime, *, validation_id: str, symbol: str = "BTC-USD") -> WalkForwardValidation:
    return WalkForwardValidation(
        validation_id=validation_id,
        created_at=now,
        symbol=symbol,
        start=now - timedelta(days=10),
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
        window_count=3,
        average_validation_return=0.0,
        average_test_return=-0.001,
        average_benchmark_return=0.001,
        average_excess_return=-0.002,
        test_win_rate=0.0,
        overfit_window_count=2,
        overfit_risk_flags=["aggregate_underperforms_benchmark"],
        backtest_result_ids=[],
        windows=[],
        decision_basis="test",
    )


def test_resolve_strategy_digest_evidence_prefers_digest_evidence_ids() -> None:
    now = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)

    evidence = resolve_strategy_digest_evidence(
        digest=_digest(
            now,
            evidence_ids=[
                "event-edge:chosen",
                "backtest-result:chosen",
                "walk-forward:chosen",
            ],
        ),
        event_edges=[
            _event_edge(now + timedelta(minutes=1), evaluation_id="event-edge:future"),
            _event_edge(now - timedelta(minutes=1), evaluation_id="event-edge:chosen"),
        ],
        backtests=[
            _backtest(now + timedelta(minutes=1), result_id="backtest-result:future"),
            _backtest(now - timedelta(minutes=1), result_id="backtest-result:chosen"),
        ],
        walk_forwards=[
            _walk_forward(now + timedelta(minutes=1), validation_id="walk-forward:future"),
            _walk_forward(now - timedelta(minutes=1), validation_id="walk-forward:chosen"),
        ],
    )

    assert evidence.event_edge is not None
    assert evidence.event_edge.evaluation_id == "event-edge:chosen"
    assert evidence.backtest is not None
    assert evidence.backtest.result_id == "backtest-result:chosen"
    assert evidence.walk_forward is not None
    assert evidence.walk_forward.validation_id == "walk-forward:chosen"


def test_resolve_strategy_digest_evidence_falls_back_to_latest_same_symbol_as_of() -> None:
    now = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)

    evidence = resolve_strategy_digest_evidence(
        digest=_digest(now),
        event_edges=[
            _event_edge(now + timedelta(minutes=1), evaluation_id="event-edge:future"),
            _event_edge(now - timedelta(minutes=2), evaluation_id="event-edge:old"),
            _event_edge(now - timedelta(minutes=1), evaluation_id="event-edge:latest"),
            _event_edge(now, evaluation_id="event-edge:eth", symbol="ETH-USD"),
        ],
        backtests=[
            _backtest(now - timedelta(minutes=2), result_id="backtest-result:old"),
            _backtest(now - timedelta(minutes=1), result_id="backtest-result:latest"),
        ],
        walk_forwards=[
            _walk_forward(now - timedelta(minutes=2), validation_id="walk-forward:old"),
            _walk_forward(now - timedelta(minutes=1), validation_id="walk-forward:latest"),
        ],
    )

    assert evidence.event_edge is not None
    assert evidence.event_edge.evaluation_id == "event-edge:latest"
    assert evidence.backtest is not None
    assert evidence.backtest.result_id == "backtest-result:latest"
    assert evidence.walk_forward is not None
    assert evidence.walk_forward.validation_id == "walk-forward:latest"


def test_resolve_strategy_digest_evidence_does_not_fallback_when_digest_ids_are_unresolved() -> None:
    now = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)

    evidence = resolve_strategy_digest_evidence(
        digest=_digest(
            now,
            evidence_ids=[
                "event-edge:missing",
                "backtest-result:missing",
                "walk-forward:missing",
            ],
        ),
        event_edges=[
            _event_edge(now - timedelta(minutes=1), evaluation_id="event-edge:latest"),
        ],
        backtests=[
            _backtest(now - timedelta(minutes=1), result_id="backtest-result:latest"),
        ],
        walk_forwards=[
            _walk_forward(now - timedelta(minutes=1), validation_id="walk-forward:latest"),
        ],
    )

    assert evidence.event_edge is None
    assert evidence.backtest is None
    assert evidence.walk_forward is None


def test_resolve_strategy_digest_evidence_fallback_prefers_decision_blocker_backtest() -> None:
    now = datetime(2026, 5, 6, 8, 0, tzinfo=UTC)
    standalone = _backtest(now - timedelta(minutes=5), result_id="backtest-result:blocker")
    internal = _backtest(now - timedelta(minutes=1), result_id="backtest-result:internal")

    evidence = resolve_strategy_digest_evidence(
        digest=_digest(now),
        event_edges=[],
        backtests=[standalone, internal],
        backtest_runs=[
            _backtest_run(
                standalone,
                decision_basis="id_context=decision_blocker_research:run_backtest:backtest_result",
            ),
            _backtest_run(internal, decision_basis="walk_forward_internal_backtest"),
        ],
        walk_forwards=[],
    )

    assert evidence.backtest is not None
    assert evidence.backtest.result_id == "backtest-result:blocker"
