from datetime import UTC, datetime, timedelta
import json

import pytest

from forecast_loop.baselines import build_baseline_evaluation
from forecast_loop.broker import BrokerMode, PaperBrokerAdapter, build_broker_adapter
from forecast_loop.cli import main
from forecast_loop.decision import generate_strategy_decision
from forecast_loop.health import run_health_check
from forecast_loop.models import (
    BaselineEvaluation,
    BacktestResult,
    EventEdgeEvaluation,
    EvaluationSummary,
    ExperimentTrial,
    Forecast,
    ForecastScore,
    LeaderboardEntry,
    PaperPosition,
    PaperPortfolioSnapshot,
    PaperShadowOutcome,
    ResearchAgenda,
    ResearchAutopilotRun,
    Review,
    RiskSnapshot,
    StrategyCard,
    StrategyDecision,
    StrategyResearchDigest,
    WalkForwardValidation,
    WalkForwardWindow,
)
from forecast_loop.storage import JsonFileRepository


def _forecast(
    forecast_id: str,
    *,
    anchor_time: datetime,
    predicted_regime: str = "trend_up",
    status: str = "resolved",
) -> Forecast:
    return Forecast(
        forecast_id=forecast_id,
        symbol="BTC-USD",
        created_at=anchor_time,
        anchor_time=anchor_time,
        target_window_start=anchor_time,
        target_window_end=anchor_time + timedelta(hours=2),
        candle_interval_minutes=60,
        expected_candle_count=3,
        status=status,
        status_reason="scored" if status == "resolved" else "awaiting_horizon_end",
        predicted_regime=predicted_regime,
        confidence=0.72,
        provider_data_through=anchor_time + timedelta(hours=2),
        observed_candle_count=3,
    )


def _score(score_id: str, forecast: Forecast, *, actual_regime: str, hit: bool, scored_at: datetime) -> ForecastScore:
    return ForecastScore(
        score_id=score_id,
        forecast_id=forecast.forecast_id,
        scored_at=scored_at,
        predicted_regime=forecast.predicted_regime or "unknown",
        actual_regime=actual_regime,
        score=1.0 if hit else 0.0,
        target_window_start=forecast.target_window_start,
        target_window_end=forecast.target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=3,
        observed_candle_count=3,
        provider_data_through=forecast.target_window_end,
        scoring_basis="test",
    )


def _decision(decision_id: str, *, now: datetime, forecast_id: str, decision_basis: str) -> StrategyDecision:
    return StrategyDecision(
        decision_id=decision_id,
        created_at=now,
        symbol="BTC-USD",
        horizon_hours=24,
        action="HOLD",
        confidence=0.5,
        evidence_grade="D",
        risk_level="MEDIUM",
        tradeable=False,
        blocked_reason="test",
        recommended_position_pct=0.0,
        current_position_pct=0.0,
        max_position_pct=0.15,
        invalidation_conditions=["test invalidation"],
        reason_summary="test decision",
        forecast_ids=[forecast_id],
        score_ids=[],
        review_ids=[],
        baseline_ids=[],
        decision_basis=decision_basis,
    )


def _backtest_result(now: datetime, result_id: str = "backtest-result:valid") -> BacktestResult:
    return BacktestResult(
        result_id=result_id,
        backtest_id="backtest-run:valid",
        created_at=now,
        symbol="BTC-USD",
        start=now - timedelta(days=5),
        end=now,
        initial_cash=10_000,
        final_equity=10_100,
        strategy_return=0.01,
        benchmark_return=0.005,
        max_drawdown=0.02,
        sharpe=1.0,
        turnover=0.4,
        win_rate=0.6,
        trade_count=2,
        equity_curve=[],
        decision_basis="test",
    )


def _walk_forward_validation(now: datetime, validation_id: str = "walk-forward:valid") -> WalkForwardValidation:
    window = WalkForwardWindow(
        window_id=f"{validation_id}:window",
        train_start=now - timedelta(days=5),
        train_end=now - timedelta(days=4),
        validation_start=now - timedelta(days=3),
        validation_end=now - timedelta(days=2),
        test_start=now - timedelta(days=1),
        test_end=now,
        train_candle_count=2,
        validation_candle_count=2,
        test_candle_count=2,
        validation_backtest_result_id="backtest-result:valid",
        test_backtest_result_id="backtest-result:valid",
        validation_return=0.01,
        test_return=0.01,
        benchmark_return=0.005,
        excess_return=0.005,
        overfit_flags=[],
        decision_basis="test",
    )
    return WalkForwardValidation(
        validation_id=validation_id,
        created_at=now,
        symbol="BTC-USD",
        start=now - timedelta(days=5),
        end=now,
        strategy_name="moving_average_trend",
        train_size=2,
        validation_size=2,
        test_size=2,
        step_size=1,
        initial_cash=10_000,
        fee_bps=5,
        slippage_bps=10,
        moving_average_window=2,
        window_count=1,
        average_validation_return=0.01,
        average_test_return=0.01,
        average_benchmark_return=0.005,
        average_excess_return=0.005,
        test_win_rate=1.0,
        overfit_window_count=0,
        overfit_risk_flags=[],
        backtest_result_ids=["backtest-result:valid"],
        windows=[window],
        decision_basis="test",
    )


def _event_edge_evaluation(now: datetime, evaluation_id: str = "event-edge:valid") -> EventEdgeEvaluation:
    return EventEdgeEvaluation(
        evaluation_id=evaluation_id,
        event_family="crypto_flow",
        event_type="CRYPTO_FLOW",
        symbol="BTC-USD",
        created_at=now,
        split="historical_event_sample",
        horizon_hours=24,
        sample_n=5,
        average_forward_return=0.02,
        average_benchmark_return=0.01,
        average_excess_return_after_costs=0.008,
        hit_rate=0.6,
        max_adverse_excursion_p50=-0.01,
        max_adverse_excursion_p90=-0.03,
        max_drawdown_if_traded=-0.04,
        turnover=1.0,
        estimated_cost_bps=10,
        dsr=None,
        white_rc_p=None,
        stability_score=0.7,
        passed=True,
        blocked_reason=None,
        flags=[],
    )


def _strategy_research_digest(
    now: datetime,
    *,
    digest_id: str = "strategy-research-digest:test",
    strategy_card_id: str | None = None,
    paper_shadow_outcome_id: str | None = None,
    autopilot_run_id: str | None = None,
    evidence_artifact_ids: list[str] | None = None,
    decision_id: str | None = None,
    decision_research_artifact_ids: list[str] | None = None,
) -> StrategyResearchDigest:
    return StrategyResearchDigest(
        digest_id=digest_id,
        created_at=now,
        symbol="BTC-USD",
        strategy_card_id=strategy_card_id,
        strategy_name="test digest strategy",
        strategy_status="DRAFT",
        hypothesis="test hypothesis",
        paper_shadow_outcome_id=paper_shadow_outcome_id,
        outcome_grade=None,
        excess_return_after_costs=None,
        recommended_strategy_action=None,
        top_failure_attributions=[],
        lineage_root_card_id=None,
        lineage_revision_count=0,
        lineage_outcome_count=0,
        lineage_primary_failure_attribution=None,
        lineage_next_research_focus=None,
        next_research_action="REPAIR_EVIDENCE_CHAIN",
        autopilot_run_id=autopilot_run_id,
        evidence_artifact_ids=evidence_artifact_ids or [],
        research_summary="test digest summary",
        next_step_rationale="test next step",
        decision_basis="test",
        decision_id=decision_id,
        decision_action="HOLD" if decision_id else None,
        decision_blocked_reason="model_not_beating_baseline" if decision_id else None,
        decision_research_blockers=["missing research evidence"] if decision_research_artifact_ids else [],
        decision_research_artifact_ids=decision_research_artifact_ids or [],
        decision_reason_summary="test decision reason" if decision_id else None,
    )


def _strategy_card(card_id: str, *, now: datetime, symbols: list[str]) -> StrategyCard:
    return StrategyCard(
        card_id=card_id,
        created_at=now,
        strategy_name="test strategy",
        strategy_family="test",
        version="v1",
        status="DRAFT",
        symbols=symbols,
        hypothesis="test hypothesis",
        signal_description="test signal",
        entry_rules=[],
        exit_rules=[],
        risk_rules=[],
        parameters={},
        data_requirements=[],
        feature_snapshot_ids=[],
        backtest_result_ids=[],
        walk_forward_validation_ids=[],
        event_edge_evaluation_ids=[],
        parent_card_id=None,
        author="codex",
        decision_basis="test",
    )


def _experiment_trial(trial_id: str, *, now: datetime, symbol: str, strategy_card_id: str) -> ExperimentTrial:
    return ExperimentTrial(
        trial_id=trial_id,
        created_at=now,
        strategy_card_id=strategy_card_id,
        trial_index=1,
        status="PENDING",
        symbol=symbol,
        seed=None,
        dataset_id=None,
        backtest_result_id=None,
        walk_forward_validation_id=None,
        event_edge_evaluation_id=None,
        prompt_hash=None,
        code_hash=None,
        parameters={},
        metric_summary={},
        failure_reason=None,
        started_at=now,
        completed_at=None,
        decision_basis="test",
    )


def _leaderboard_entry(
    entry_id: str,
    *,
    now: datetime,
    symbol: str,
    strategy_card_id: str,
    trial_id: str,
    evaluation_id: str = "locked-evaluation:missing",
) -> LeaderboardEntry:
    return LeaderboardEntry(
        entry_id=entry_id,
        created_at=now,
        strategy_card_id=strategy_card_id,
        evaluation_id=evaluation_id,
        trial_id=trial_id,
        symbol=symbol,
        rankable=False,
        alpha_score=None,
        promotion_stage="BLOCKED",
        blocked_reasons=[],
        leaderboard_rules_version="test",
        decision_basis="test",
    )


def _paper_shadow_outcome(
    outcome_id: str,
    *,
    now: datetime,
    symbol: str,
    strategy_card_id: str,
    trial_id: str,
    leaderboard_entry_id: str,
    evaluation_id: str = "locked-evaluation:missing",
) -> PaperShadowOutcome:
    return PaperShadowOutcome(
        outcome_id=outcome_id,
        created_at=now,
        leaderboard_entry_id=leaderboard_entry_id,
        evaluation_id=evaluation_id,
        strategy_card_id=strategy_card_id,
        trial_id=trial_id,
        symbol=symbol,
        window_start=now,
        window_end=now + timedelta(hours=1),
        observed_return=None,
        benchmark_return=None,
        excess_return_after_costs=None,
        max_adverse_excursion=None,
        turnover=None,
        outcome_grade="INSUFFICIENT",
        failure_attributions=[],
        recommended_promotion_stage="PAPER_SHADOW_PENDING",
        recommended_strategy_action="CONTINUE_SHADOW",
        blocked_reasons=[],
        notes=[],
        decision_basis="test",
    )


def _research_agenda(agenda_id: str, *, now: datetime, symbol: str) -> ResearchAgenda:
    return ResearchAgenda(
        agenda_id=agenda_id,
        created_at=now,
        symbol=symbol,
        title="test agenda",
        hypothesis="test hypothesis",
        priority="MEDIUM",
        status="OPEN",
        target_strategy_family="test",
        strategy_card_ids=[],
        expected_artifacts=[],
        acceptance_criteria=[],
        blocked_actions=[],
        decision_basis="test",
    )


def _research_autopilot_run(
    run_id: str,
    *,
    now: datetime,
    symbol: str,
    agenda_id: str,
    strategy_card_id: str,
    trial_id: str,
    leaderboard_entry_id: str,
    paper_shadow_outcome_id: str,
    locked_evaluation_id: str = "locked-evaluation:missing",
) -> ResearchAutopilotRun:
    return ResearchAutopilotRun(
        run_id=run_id,
        created_at=now,
        symbol=symbol,
        agenda_id=agenda_id,
        strategy_card_id=strategy_card_id,
        experiment_trial_id=trial_id,
        locked_evaluation_id=locked_evaluation_id,
        leaderboard_entry_id=leaderboard_entry_id,
        strategy_decision_id=None,
        paper_shadow_outcome_id=paper_shadow_outcome_id,
        steps=[],
        loop_status="BLOCKED",
        next_research_action="REPAIR_EVIDENCE_CHAIN",
        blocked_reasons=[],
        decision_basis="test",
    )


def _seed_scores(repository: JsonFileRepository, *, actuals: list[str], hits: list[bool]) -> list[ForecastScore]:
    scores = []
    start = datetime(2026, 4, 21, 0, 0, tzinfo=UTC)
    for index, (actual, hit) in enumerate(zip(actuals, hits, strict=True)):
        forecast = _forecast(
            f"forecast:{index}",
            anchor_time=start + timedelta(hours=index),
            predicted_regime=actual if hit else ("trend_down" if actual == "trend_up" else "trend_up"),
        )
        score = _score(
            f"score:{index}",
            forecast,
            actual_regime=actual,
            hit=hit,
            scored_at=forecast.target_window_end,
        )
        repository.save_forecast(forecast)
        repository.save_score(score)
        scores.append(score)
    return scores


def _ok_risk(now: datetime, *, created_at: datetime | None = None) -> RiskSnapshot:
    return RiskSnapshot(
        risk_id=f"risk:{(created_at or now).isoformat()}",
        created_at=created_at or now,
        symbol="BTC-USD",
        status="OK",
        severity="none",
        current_drawdown_pct=0.0,
        max_drawdown_pct=0.0,
        gross_exposure_pct=0.0,
        net_exposure_pct=0.0,
        position_pct=0.0,
        max_position_pct=0.15,
        max_gross_exposure_pct=0.20,
        reduce_risk_drawdown_pct=0.05,
        stop_new_entries_drawdown_pct=0.10,
        findings=[],
        recommended_action="HOLD",
        decision_basis="test",
    )


def test_repository_round_trips_m1_artifacts(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    forecast = _forecast("forecast:latest", anchor_time=now)
    score = _score("score:latest", forecast, actual_regime="trend_up", hit=True, scored_at=now)
    repository.save_forecast(forecast)
    repository.save_score(score)
    baseline = build_baseline_evaluation(
        symbol="BTC-USD",
        generated_at=now,
        forecasts=repository.load_forecasts(),
        scores=repository.load_scores(),
    )
    snapshot = PaperPortfolioSnapshot(
        snapshot_id="portfolio:test",
        created_at=now,
        equity=10_000,
        cash=8_000,
        gross_exposure_pct=0.2,
        net_exposure_pct=0.2,
        max_drawdown_pct=None,
        positions=[
            PaperPosition(
                symbol="BTC-USD",
                quantity=0.1,
                avg_price=100,
                market_price=120,
                market_value=12,
                unrealized_pnl=2,
                position_pct=0.2,
            )
        ],
    )
    repository.save_baseline_evaluation(baseline)
    repository.save_baseline_evaluation(baseline)
    repository.save_portfolio_snapshot(snapshot)

    assert repository.load_baseline_evaluations() == [baseline]
    assert repository.load_portfolio_snapshots() == [snapshot]


def test_strategy_decision_holds_when_evidence_is_insufficient(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    forecast = _forecast("forecast:latest", anchor_time=now, status="pending")
    repository.save_forecast(forecast)

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
        risk_snapshot=_ok_risk(now),
    )

    assert decision.action == "HOLD"
    assert decision.evidence_grade == "INSUFFICIENT"
    assert decision.tradeable is False
    assert decision.blocked_reason == "insufficient_evidence"
    assert decision.forecast_ids == [forecast.forecast_id]
    assert repository.load_strategy_decisions() == [decision]


def test_strategy_decision_blocks_buy_sell_when_model_does_not_beat_baseline(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_scores(repository, actuals=["trend_up"] * 5, hits=[True] * 5)
    latest = _forecast("forecast:latest", anchor_time=now, predicted_regime="trend_up", status="pending")
    repository.save_forecast(latest)

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
    )

    assert decision.action == "HOLD"
    assert decision.blocked_reason == "model_not_beating_baseline"
    assert decision.tradeable is False
    assert "主要研究阻擋" in decision.reason_summary
    assert "event edge 缺失" in decision.reason_summary
    assert "backtest 缺失" in decision.reason_summary


def test_strategy_decision_reduces_risk_when_recent_score_is_poor(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_scores(
        repository,
        actuals=["trend_up", "trend_down", "trend_up", "trend_down", "trend_up"],
        hits=[True, False, False, False, False],
    )
    repository.save_portfolio_snapshot(
        PaperPortfolioSnapshot(
            snapshot_id="portfolio:risk",
            created_at=now,
            equity=10_000,
            cash=9_000,
            gross_exposure_pct=0.10,
            net_exposure_pct=0.10,
            max_drawdown_pct=None,
            positions=[
                PaperPosition(
                    symbol="BTC-USD",
                    quantity=1,
                    avg_price=100,
                    market_price=100,
                    market_value=1_000,
                    unrealized_pnl=0,
                    position_pct=0.10,
                )
            ],
        )
    )
    latest = _forecast("forecast:latest", anchor_time=now, predicted_regime="trend_up", status="pending")
    repository.save_forecast(latest)

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
    )

    assert decision.action == "REDUCE_RISK"
    assert decision.risk_level == "HIGH"
    assert decision.recommended_position_pct == 0.05


def test_strategy_decision_buys_only_when_evidence_beats_baseline(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_scores(
        repository,
        actuals=["trend_up", "trend_up", "trend_down", "trend_up", "trend_down", "trend_down"],
        hits=[True, True, True, True, True, True],
    )
    latest = _forecast("forecast:latest", anchor_time=now, predicted_regime="trend_up", status="pending")
    repository.save_forecast(latest)

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
        risk_snapshot=_ok_risk(now),
    )

    assert decision.action == "HOLD"
    assert decision.evidence_grade == "B"
    assert decision.tradeable is False
    assert decision.blocked_reason == "research_backtest_missing"
    assert decision.baseline_ids
    assert decision.score_ids


def test_strategy_decision_blocks_directional_buy_without_risk_snapshot(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_scores(
        repository,
        actuals=["trend_up", "trend_up", "trend_down", "trend_up", "trend_down", "trend_down"],
        hits=[True, True, True, True, True, True],
    )
    latest = _forecast("forecast:latest", anchor_time=now, predicted_regime="trend_up", status="pending")
    repository.save_forecast(latest)

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
    )

    assert decision.action == "HOLD"
    assert decision.tradeable is False
    assert decision.blocked_reason == "research_backtest_missing"
    assert "risk=none" in decision.decision_basis


def test_strategy_decision_blocks_directional_buy_with_stale_risk_snapshot(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_scores(
        repository,
        actuals=["trend_up", "trend_up", "trend_down", "trend_up", "trend_down", "trend_down"],
        hits=[True, True, True, True, True, True],
    )
    latest = _forecast("forecast:latest", anchor_time=now, predicted_regime="trend_up", status="pending")
    repository.save_forecast(latest)
    repository.save_risk_snapshot(_ok_risk(now, created_at=now - timedelta(hours=3)))

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
    )

    assert decision.action == "HOLD"
    assert decision.tradeable is False
    assert decision.blocked_reason == "research_backtest_missing"


def test_strategy_decision_stops_new_entries_when_health_requires_repair(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    health = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now)

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
        health_result=health,
    )

    assert health.repair_required is True
    assert decision.action == "STOP_NEW_ENTRIES"
    assert decision.blocked_reason == "health_check_repair_required"
    assert (tmp_path / ".codex" / "repair_requests" / "pending").exists()


def test_strategy_decision_fail_closed_does_not_read_corrupt_storage_after_blocking_health(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    storage.mkdir()
    (storage / "forecasts.jsonl").write_text("{bad json\n", encoding="utf-8")
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    health = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now)

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
        health_result=health,
    )

    assert decision.action == "STOP_NEW_ENTRIES"
    assert decision.blocked_reason == "health_check_repair_required"
    assert repository.load_strategy_decisions() == [decision]


def test_paper_broker_is_only_available_mode():
    broker = build_broker_adapter("paper")
    snapshot = broker.get_account_snapshot(now=datetime(2026, 4, 24, 12, 0, tzinfo=UTC))
    order = broker.submit_order(symbol="BTC-USD", side="BUY", quantity=1)
    health = broker.health_check(now=datetime(2026, 4, 24, 12, 0, tzinfo=UTC))

    assert isinstance(broker, PaperBrokerAdapter)
    assert broker.mode == BrokerMode.INTERNAL_PAPER
    assert snapshot.equity == 10_000
    assert broker.get_positions(now=datetime(2026, 4, 24, 12, 0, tzinfo=UTC)) == []
    assert broker.get_fills() == []
    assert broker.get_order_status(order_id="paper-order:test")["status"] == "unavailable"
    assert broker.cancel_order(order_id="paper-order:test")["status"] == "blocked"
    assert order["status"] == "blocked"
    assert order["mode"] == "INTERNAL_PAPER"
    assert health["live_trading_available"] is False
    assert health["external_submit_available"] is False
    assert build_broker_adapter("INTERNAL_PAPER").mode == BrokerMode.INTERNAL_PAPER
    with pytest.raises(TypeError):
        PaperBrokerAdapter(mode=BrokerMode.SANDBOX)
    with pytest.raises(TypeError):
        PaperBrokerAdapter(mode=BrokerMode.EXTERNAL_PAPER)
    with pytest.raises(ValueError, match="available sandbox broker"):
        build_broker_adapter("EXTERNAL_PAPER")
    with pytest.raises(ValueError, match="available sandbox broker"):
        build_broker_adapter("SANDBOX")
    with pytest.raises(ValueError, match="live mode is unsupported"):
        build_broker_adapter("live")


def test_health_check_detects_bad_json_and_writes_repair_request(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    storage.mkdir()
    (storage / "forecasts.jsonl").write_text("{bad json\n", encoding="utf-8")

    result = run_health_check(
        storage_dir=storage,
        symbol="BTC-USD",
        now=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
    )

    assert result.status == "unhealthy"
    assert result.severity == "blocking"
    assert result.repair_required is True
    assert result.repair_request_id is not None
    assert (storage / "repair_requests.jsonl").exists()
    assert next(iter((tmp_path / ".codex" / "repair_requests" / "pending").glob("*.md"))).exists()


def test_health_check_detects_duplicate_forecast_and_meta_mismatch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    forecast = _forecast("forecast:dup", anchor_time=now, status="pending")
    with (storage / "forecasts.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(forecast.to_dict()) + "\n")
        handle.write(json.dumps(forecast.to_dict()) + "\n")
    (storage / "last_run_meta.json").write_text(
        json.dumps({"new_forecast": {"forecast_id": "forecast:other"}}),
        encoding="utf-8",
    )

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now)
    codes = {finding.code for finding in result.findings}

    assert repository.root.exists()
    assert "duplicate_forecast_id" in codes
    assert "last_run_meta_mismatch" in codes
    assert result.repair_required is True


def test_health_check_detects_score_pointing_to_missing_forecast(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    storage.mkdir()
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    valid_forecast = _forecast("forecast:valid", anchor_time=now, status="pending")
    missing_forecast = _forecast("forecast:missing", anchor_time=now)
    bad_score = _score(
        "score:bad",
        missing_forecast,
        actual_regime="trend_up",
        hit=True,
        scored_at=now,
    )
    (storage / "forecasts.jsonl").write_text(json.dumps(valid_forecast.to_dict()) + "\n", encoding="utf-8")
    (storage / "scores.jsonl").write_text(json.dumps(bad_score.to_dict()) + "\n", encoding="utf-8")

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now)

    assert "score_missing_forecast" in {finding.code for finding in result.findings}
    assert result.repair_required is True


def test_health_check_detects_baseline_pointing_to_missing_artifacts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    valid_forecast = _forecast("forecast:valid", anchor_time=now, status="pending")
    repository.save_forecast(valid_forecast)
    repository.save_baseline_evaluation(
        BaselineEvaluation(
            baseline_id="baseline:broken",
            created_at=now,
            symbol="BTC-USD",
            sample_size=1,
            directional_accuracy=None,
            baseline_accuracy=None,
            model_edge=None,
            recent_score=None,
            evidence_grade="INSUFFICIENT",
            forecast_ids=["forecast:missing"],
            score_ids=["score:missing"],
            decision_basis="test broken links",
        )
    )

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now)
    codes = {finding.code for finding in result.findings}

    assert "baseline_missing_forecast" in codes
    assert "baseline_missing_score" in codes
    assert result.repair_required is True


def test_health_check_detects_strategy_decision_basis_missing_research_evidence(tmp_path):
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    forecast = _forecast("forecast:valid", anchor_time=now, status="pending")
    repository.save_forecast(forecast)
    repository.save_strategy_decision(
        _decision(
            "decision:broken-basis",
            now=now,
            forecast_id=forecast.forecast_id,
            decision_basis=(
                "research_gate=sample_size=6; "
                "backtest_result=backtest-result:missing; "
                "walk_forward=walk-forward:missing; "
                "event_edge=event-edge:missing"
            ),
        )
    )

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now, create_repair_request=False)
    codes = {finding.code for finding in result.findings}

    assert "decision_basis_missing_backtest_result" in codes
    assert "decision_basis_missing_walk_forward" in codes
    assert "decision_basis_missing_event_edge" in codes
    assert result.repair_required is True


def test_health_check_ignores_strategy_decision_basis_missing_placeholders(tmp_path):
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    forecast = _forecast("forecast:valid", anchor_time=now, status="pending")
    repository.save_forecast(forecast)
    repository.save_strategy_decision(
        _decision(
            "decision:placeholder-basis",
            now=now,
            forecast_id=forecast.forecast_id,
            decision_basis=(
                "research_gate=sample_size=6; "
                "backtest_result=missing; "
                "walk_forward=missing; "
                "event_edge=missing"
            ),
        )
    )

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now, create_repair_request=False)

    assert not {finding.code for finding in result.findings} & {
        "decision_basis_missing_backtest_result",
        "decision_basis_missing_walk_forward",
        "decision_basis_missing_event_edge",
    }
    assert result.repair_required is False


def test_health_check_allows_strategy_decision_basis_persisted_research_evidence(tmp_path):
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    forecast = _forecast("forecast:valid", anchor_time=now, status="pending")
    repository.save_forecast(forecast)
    repository.save_backtest_result(_backtest_result(now))
    repository.save_walk_forward_validation(_walk_forward_validation(now))
    repository.save_event_edge_evaluation(_event_edge_evaluation(now))
    repository.save_strategy_decision(
        _decision(
            "decision:valid-basis",
            now=now,
            forecast_id=forecast.forecast_id,
            decision_basis=(
                "research_gate=sample_size=6; "
                "backtest_result=backtest-result:valid; "
                "walk_forward=walk-forward:valid; "
                "event_edge=event-edge:valid"
            ),
        )
    )

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now, create_repair_request=False)

    assert not {finding.code for finding in result.findings} & {
        "decision_basis_missing_backtest_result",
        "decision_basis_missing_walk_forward",
        "decision_basis_missing_event_edge",
    }


def test_health_check_detects_strategy_research_digest_missing_artifact_links(tmp_path):
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_forecast(_forecast("forecast:valid", anchor_time=now, status="pending"))
    repository.save_strategy_research_digest(
        _strategy_research_digest(
            now,
            digest_id="strategy-research-digest:broken",
            strategy_card_id="strategy-card:missing",
            paper_shadow_outcome_id="paper-shadow-outcome:missing",
            autopilot_run_id="research-autopilot-run:missing",
            evidence_artifact_ids=[
                "decision:missing-evidence",
                "backtest-result:missing-evidence",
                "walk-forward:missing-evidence",
                "event-edge:missing-evidence",
            ],
            decision_id="decision:missing",
            decision_research_artifact_ids=[
                "backtest-result:missing-blocker",
                "walk-forward:missing-blocker",
                "event-edge:missing-blocker",
            ],
        )
    )

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now, create_repair_request=False)
    codes = {finding.code for finding in result.findings}

    assert "strategy_research_digest_missing_strategy_card" in codes
    assert "strategy_research_digest_missing_paper_shadow_outcome" in codes
    assert "strategy_research_digest_missing_research_autopilot_run" in codes
    assert "strategy_research_digest_missing_decision" in codes
    assert "strategy_research_digest_missing_backtest_result" in codes
    assert "strategy_research_digest_missing_walk_forward" in codes
    assert "strategy_research_digest_missing_event_edge" in codes
    assert result.repair_required is True


def test_health_check_allows_strategy_research_digest_placeholder_evidence_ids(tmp_path):
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_forecast(_forecast("forecast:valid", anchor_time=now, status="pending"))
    repository.save_strategy_research_digest(
        _strategy_research_digest(
            now,
            digest_id="strategy-research-digest:placeholder",
            evidence_artifact_ids=["missing", "none", "null"],
            decision_research_artifact_ids=["missing", "none", "null"],
        )
    )

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now, create_repair_request=False)

    assert not {finding.code for finding in result.findings} & {
        "strategy_research_digest_missing_strategy_card",
        "strategy_research_digest_missing_paper_shadow_outcome",
        "strategy_research_digest_missing_research_autopilot_run",
        "strategy_research_digest_missing_decision",
        "strategy_research_digest_missing_backtest_result",
        "strategy_research_digest_missing_walk_forward",
        "strategy_research_digest_missing_event_edge",
    }


def test_health_check_allows_strategy_research_digest_persisted_research_evidence(tmp_path):
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    forecast = _forecast("forecast:valid", anchor_time=now, status="pending")
    repository.save_forecast(forecast)
    repository.save_strategy_decision(
        _decision("decision:valid-digest", now=now, forecast_id=forecast.forecast_id, decision_basis="test")
    )
    repository.save_backtest_result(_backtest_result(now))
    repository.save_walk_forward_validation(_walk_forward_validation(now))
    repository.save_event_edge_evaluation(_event_edge_evaluation(now))
    repository.save_strategy_research_digest(
        _strategy_research_digest(
            now,
            digest_id="strategy-research-digest:valid",
            evidence_artifact_ids=[
                "decision:valid-digest",
                "backtest-result:valid",
                "walk-forward:valid",
                "event-edge:valid",
            ],
            decision_id="decision:valid-digest",
            decision_research_artifact_ids=[
                "backtest-result:valid",
                "walk-forward:valid",
                "event-edge:valid",
            ],
        )
    )

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now, create_repair_request=False)

    assert not {finding.code for finding in result.findings} & {
        "strategy_research_digest_missing_decision",
        "strategy_research_digest_missing_backtest_result",
        "strategy_research_digest_missing_walk_forward",
        "strategy_research_digest_missing_event_edge",
        "strategy_research_digest_symbol_mismatch_decision",
        "strategy_research_digest_symbol_mismatch_backtest_result",
        "strategy_research_digest_symbol_mismatch_walk_forward",
        "strategy_research_digest_symbol_mismatch_event_edge",
    }


def test_health_check_scopes_strategy_research_digest_link_gate_to_latest_symbol_digest(tmp_path):
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_forecast(_forecast("forecast:valid", anchor_time=now, status="pending"))
    repository.save_strategy_research_digest(
        _strategy_research_digest(
            now - timedelta(hours=1),
            digest_id="strategy-research-digest:old-broken",
            evidence_artifact_ids=[
                "paper-shadow-outcome:missing-old",
                "experiment-trial:missing-old",
                "research-autopilot-run:missing-old",
            ],
        )
    )
    repository.save_strategy_research_digest(
        _strategy_research_digest(
            now,
            digest_id="strategy-research-digest:latest-current",
            evidence_artifact_ids=["missing"],
            decision_research_artifact_ids=["missing"],
        )
    )

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now, create_repair_request=False)

    assert not {finding.code for finding in result.findings} & {
        "strategy_research_digest_missing_paper_shadow_outcome",
        "strategy_research_digest_missing_experiment_trial",
        "strategy_research_digest_missing_research_autopilot_run",
    }


def test_health_check_detects_latest_strategy_research_digest_symbol_mismatches(tmp_path):
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    forecast = _forecast("forecast:valid", anchor_time=now, status="pending")
    repository.save_forecast(forecast)

    eth_decision = _decision("decision:eth", now=now, forecast_id=forecast.forecast_id, decision_basis="test")
    eth_decision.symbol = "ETH-USD"
    eth_backtest = _backtest_result(now, result_id="backtest-result:eth")
    eth_backtest.symbol = "ETH-USD"
    eth_walk_forward = _walk_forward_validation(now, validation_id="walk-forward:eth")
    eth_walk_forward.symbol = "ETH-USD"
    eth_event_edge = _event_edge_evaluation(now, evaluation_id="event-edge:eth")
    eth_event_edge.symbol = "ETH-USD"

    repository.save_strategy_decision(eth_decision)
    repository.save_backtest_result(eth_backtest)
    repository.save_walk_forward_validation(eth_walk_forward)
    repository.save_event_edge_evaluation(eth_event_edge)
    repository.save_strategy_card(_strategy_card("strategy-card:eth", now=now, symbols=["ETH-USD"]))
    repository.save_experiment_trial(
        _experiment_trial("experiment-trial:eth", now=now, symbol="ETH-USD", strategy_card_id="strategy-card:eth")
    )
    repository.save_leaderboard_entry(
        _leaderboard_entry(
            "leaderboard-entry:eth",
            now=now,
            symbol="ETH-USD",
            strategy_card_id="strategy-card:eth",
            trial_id="experiment-trial:eth",
        )
    )
    repository.save_paper_shadow_outcome(
        _paper_shadow_outcome(
            "paper-shadow-outcome:eth",
            now=now,
            symbol="ETH-USD",
            strategy_card_id="strategy-card:eth",
            trial_id="experiment-trial:eth",
            leaderboard_entry_id="leaderboard-entry:eth",
        )
    )
    repository.save_research_agenda(_research_agenda("research-agenda:eth", now=now, symbol="ETH-USD"))
    repository.save_research_autopilot_run(
        _research_autopilot_run(
            "research-autopilot-run:eth",
            now=now,
            symbol="ETH-USD",
            agenda_id="research-agenda:eth",
            strategy_card_id="strategy-card:eth",
            trial_id="experiment-trial:eth",
            leaderboard_entry_id="leaderboard-entry:eth",
            paper_shadow_outcome_id="paper-shadow-outcome:eth",
        )
    )
    repository.save_strategy_research_digest(
        _strategy_research_digest(
            now,
            digest_id="strategy-research-digest:btc-links-eth",
            strategy_card_id="strategy-card:eth",
            paper_shadow_outcome_id="paper-shadow-outcome:eth",
            autopilot_run_id="research-autopilot-run:eth",
            evidence_artifact_ids=[
                "decision:eth",
                "strategy-card:eth",
                "paper-shadow-outcome:eth",
                "research-autopilot-run:eth",
                "backtest-result:eth",
                "walk-forward:eth",
                "event-edge:eth",
                "leaderboard-entry:eth",
                "experiment-trial:eth",
                "research-agenda:eth",
            ],
            decision_id="decision:eth",
            decision_research_artifact_ids=[
                "backtest-result:eth",
                "walk-forward:eth",
                "event-edge:eth",
            ],
        )
    )

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now, create_repair_request=False)
    codes = {finding.code for finding in result.findings}

    assert "strategy_research_digest_symbol_mismatch_strategy_card" in codes
    assert "strategy_research_digest_symbol_mismatch_paper_shadow_outcome" in codes
    assert "strategy_research_digest_symbol_mismatch_research_autopilot_run" in codes
    assert "strategy_research_digest_symbol_mismatch_decision" in codes
    assert "strategy_research_digest_symbol_mismatch_backtest_result" in codes
    assert "strategy_research_digest_symbol_mismatch_walk_forward" in codes
    assert "strategy_research_digest_symbol_mismatch_event_edge" in codes
    assert "strategy_research_digest_symbol_mismatch_leaderboard_entry" in codes
    assert "strategy_research_digest_symbol_mismatch_experiment_trial" in codes
    assert "strategy_research_digest_symbol_mismatch_research_agenda" in codes
    assert result.repair_required is True


def test_health_check_detects_non_replay_evaluation_summary_broken_links(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_forecast(_forecast("forecast:valid", anchor_time=now, status="pending"))
    repository.save_evaluation_summary(
        EvaluationSummary(
            summary_id="summary:ignored-by-from-dict",
            replay_id="current-summary",
            generated_at=now,
            forecast_ids=["forecast:missing"],
            scored_forecast_ids=["forecast:missing-scored"],
            replay_window_start=None,
            replay_window_end=None,
            anchor_time_start=None,
            anchor_time_end=None,
            forecast_count=1,
            resolved_count=0,
            waiting_for_data_count=0,
            unscorable_count=0,
            average_score=None,
            score_ids=["score:missing"],
            review_ids=["review:missing"],
            proposal_ids=["proposal:missing"],
        )
    )

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now)
    codes = {finding.code for finding in result.findings}

    assert "evaluation_summary_missing_forecast" in codes
    assert "evaluation_summary_missing_score" in codes
    assert "evaluation_summary_missing_review" in codes
    assert "evaluation_summary_missing_proposal" in codes
    assert result.repair_required is True


def test_health_check_allows_replay_scoped_evaluation_summary_links(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_forecast(_forecast("forecast:valid", anchor_time=now, status="pending"))
    repository.save_evaluation_summary(
        EvaluationSummary(
            summary_id="summary:replay",
            replay_id="replay:sample:BTC-USD",
            generated_at=now,
            forecast_ids=["forecast:replay-only"],
            scored_forecast_ids=["forecast:replay-only"],
            replay_window_start=now,
            replay_window_end=now,
            anchor_time_start=now,
            anchor_time_end=now,
            forecast_count=1,
            resolved_count=1,
            waiting_for_data_count=0,
            unscorable_count=0,
            average_score=1.0,
            score_ids=["score:replay-only"],
            review_ids=[],
            proposal_ids=[],
        )
    )

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now)

    assert result.repair_required is False


def test_cli_decide_fail_closed_on_corrupt_portfolio_snapshot(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_forecast(_forecast("forecast:latest", anchor_time=now, status="pending"))
    (storage / "portfolio_snapshots.jsonl").write_text("{bad json\n", encoding="utf-8")

    exit_code = main(
        [
            "decide",
            "--storage-dir",
            str(storage),
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-24T12:00:00+00:00",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    health = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now)

    assert exit_code == 0
    assert payload["action"] == "STOP_NEW_ENTRIES"
    assert payload["blocked_reason"] == "health_check_repair_required"
    assert "bad_json_row" in {finding.code for finding in health.findings}
    assert health.repair_required is True


def test_health_check_can_create_repair_request_when_repair_log_is_corrupt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_forecast(_forecast("forecast:latest", anchor_time=now, status="pending"))
    (storage / "repair_requests.jsonl").write_text("{bad json\n", encoding="utf-8")

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now)
    lines = (storage / "repair_requests.jsonl").read_text(encoding="utf-8").splitlines()

    assert result.repair_required is True
    assert result.repair_request_id is not None
    assert "bad_json_row" in {finding.code for finding in result.findings}
    assert len(lines) == 2
    assert json.loads(lines[-1])["repair_request_id"] == result.repair_request_id


def test_missing_storage_health_check_can_use_corrupt_global_repair_log(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    global_log = tmp_path / ".codex" / "repair_requests" / "repair_requests.jsonl"
    global_log.parent.mkdir(parents=True)
    global_log.write_text("{bad json\n", encoding="utf-8")
    missing = tmp_path / "missing-storage"

    result = run_health_check(
        storage_dir=missing,
        symbol="BTC-USD",
        now=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
    )
    lines = global_log.read_text(encoding="utf-8").splitlines()

    assert result.repair_required is True
    assert result.repair_request_id is not None
    assert not missing.exists()
    assert len(lines) == 2
    assert json.loads(lines[-1])["repair_request_id"] == result.repair_request_id


def test_health_check_existing_file_storage_path_uses_global_repair_request(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage_file = tmp_path / "storage-is-file"
    storage_file.write_text("not a directory", encoding="utf-8")

    result = run_health_check(
        storage_dir=storage_file,
        symbol="BTC-USD",
        now=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
    )

    assert result.repair_required is True
    assert "storage_path_not_directory" in {finding.code for finding in result.findings}
    assert storage_file.is_file()
    assert (tmp_path / ".codex" / "repair_requests" / "repair_requests.jsonl").exists()


def test_cli_decide_writes_strategy_decision(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    forecast = _forecast("forecast:latest", anchor_time=now, status="pending")
    repository.save_forecast(forecast)

    exit_code = main(
        [
            "decide",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-24T12:00:00+00:00",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["action"] == "HOLD"
    assert (tmp_path / "strategy_decisions.jsonl").exists()


def test_cli_decide_fail_closed_on_corrupt_storage(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    storage.mkdir()
    (storage / "forecasts.jsonl").write_text("{bad json\n", encoding="utf-8")

    exit_code = main(
        [
            "decide",
            "--storage-dir",
            str(storage),
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-24T12:00:00+00:00",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["action"] == "STOP_NEW_ENTRIES"
    assert payload["blocked_reason"] == "health_check_repair_required"
    assert (storage / "strategy_decisions.jsonl").exists()
    assert (storage / "repair_requests.jsonl").exists()


def test_cli_decide_missing_storage_does_not_create_typo_path(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    missing = tmp_path / "missing-decide-storage"

    exit_code = main(
        [
            "decide",
            "--storage-dir",
            str(missing),
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-24T12:00:00+00:00",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["action"] == "STOP_NEW_ENTRIES"
    assert payload["blocked_reason"] == "health_check_repair_required"
    assert not missing.exists()
    assert (tmp_path / ".codex" / "repair_requests" / "repair_requests.jsonl").exists()


def test_cli_decide_file_storage_path_fails_closed_without_traceback(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    storage_file = tmp_path / "storage-is-file"
    storage_file.write_text("not a directory", encoding="utf-8")

    exit_code = main(
        [
            "decide",
            "--storage-dir",
            str(storage_file),
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-24T12:00:00+00:00",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["action"] == "STOP_NEW_ENTRIES"
    assert payload["blocked_reason"] == "health_check_repair_required"
    assert storage_file.is_file()
    assert (tmp_path / ".codex" / "repair_requests" / "repair_requests.jsonl").exists()


def test_cli_run_once_also_decide_writes_one_command_strategy_decision(tmp_path, capsys):
    exit_code = main(
        [
            "run-once",
            "--provider",
            "sample",
            "--symbol",
            "BTC-USD",
            "--storage-dir",
            str(tmp_path),
            "--now",
            "2026-04-24T12:00:00+00:00",
            "--also-decide",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["decision_action"] == "HOLD"
    assert payload["strategy_research_digest_id"] is None
    assert payload["decision_blocker_research_agenda_id"] is None
    assert payload["automation_run_id"].startswith("automation-run:")
    assert payload["notification_count"] >= 1
    assert (tmp_path / "forecasts.jsonl").exists()
    assert (tmp_path / "strategy_decisions.jsonl").exists()
    assert (tmp_path / "notification_artifacts.jsonl").exists()
    notifications = JsonFileRepository(tmp_path).load_notification_artifacts()
    notification_types = {notification.notification_type for notification in notifications}
    assert "NEW_DECISION" in notification_types
    assert "BUY_SELL_BLOCKED" in notification_types
    automation_runs = JsonFileRepository(tmp_path).load_automation_runs()
    assert len(automation_runs) == 1
    run = automation_runs[0]
    assert run.status == "completed"
    assert run.symbol == "BTC-USD"
    assert run.provider == "sample"
    assert run.command == "run-once"
    assert run.health_check_id is not None
    assert run.decision_id == payload["decision_id"]
    assert run.repair_request_id is None
    step_names = [step["name"] for step in run.steps]
    assert step_names == [
        "forecast",
        "score",
        "review",
        "proposal",
        "health_check",
        "risk_check",
        "decide",
        "notifications",
        "strategy_research_digest",
        "decision_blocker_research_agenda",
    ]


def test_health_check_audits_bad_and_duplicate_automation_runs(tmp_path):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_forecast(_forecast("forecast:latest", anchor_time=now, status="pending"))
    main(
        [
            "run-once",
            "--provider",
            "sample",
            "--symbol",
            "BTC-USD",
            "--storage-dir",
            str(tmp_path),
            "--now",
            now.isoformat(),
            "--also-decide",
        ]
    )
    run_payload = JsonFileRepository(tmp_path).load_automation_runs()[0].to_dict()
    (tmp_path / "automation_runs.jsonl").write_text(
        "\n".join([json.dumps(run_payload), json.dumps(run_payload), "{bad json"]) + "\n",
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
    assert "duplicate_automation_run_id" in codes


def test_health_check_audits_bad_and_duplicate_notification_artifacts(tmp_path):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_forecast(_forecast("forecast:latest", anchor_time=now, status="pending"))
    main(
        [
            "run-once",
            "--provider",
            "sample",
            "--symbol",
            "BTC-USD",
            "--storage-dir",
            str(tmp_path),
            "--now",
            now.isoformat(),
            "--also-decide",
        ]
    )
    notification_payload = JsonFileRepository(tmp_path).load_notification_artifacts()[0].to_dict()
    (tmp_path / "notification_artifacts.jsonl").write_text(
        "\n".join([json.dumps(notification_payload), json.dumps(notification_payload), "{bad json"]) + "\n",
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
    assert "duplicate_notification_id" in codes


def test_health_check_flags_secret_leak_without_echoing_secret_value(tmp_path, monkeypatch):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    repository.save_forecast(_forecast("forecast:latest", anchor_time=now, status="pending"))
    leaked = "sk_live_this_should_not_be_reported"
    (storage / "provider_runs.jsonl").write_text(
        json.dumps({"api_key": leaked, "provider_run_id": "provider-run:bad"}) + "\n",
        encoding="utf-8",
    )

    result = run_health_check(
        storage_dir=storage,
        symbol="BTC-USD",
        now=now,
        create_repair_request=False,
    )
    messages = "\n".join(finding.message for finding in result.findings)

    assert result.repair_required is True
    assert "secret_leak_detected" in {finding.code for finding in result.findings}
    assert leaked not in messages


def test_health_check_flags_prefixed_env_secret_names(tmp_path, monkeypatch):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    repository.save_forecast(_forecast("forecast:latest", anchor_time=now, status="pending"))
    leaked = "test_secret_value_should_not_echo"
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                f"ALPACA_PAPER_API_KEY={leaked}",
                f"BINANCE_TESTNET_API_SECRET={leaked}",
                f"TELEGRAM_BOT_TOKEN={leaked}",
            ]
        ),
        encoding="utf-8",
    )

    result = run_health_check(
        storage_dir=storage,
        symbol="BTC-USD",
        now=now,
        create_repair_request=False,
    )
    messages = "\n".join(finding.message for finding in result.findings)

    assert "secret_leak_detected" in {finding.code for finding in result.findings}
    assert leaked not in messages


def test_health_check_allows_non_secret_local_env(tmp_path, monkeypatch):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "FORECAST_LOOP_ENV=local\nFORECAST_LOOP_BROKER_MODE=INTERNAL_PAPER\n",
        encoding="utf-8",
    )
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    repository.save_forecast(_forecast("forecast:latest", anchor_time=now, status="pending"))

    result = run_health_check(
        storage_dir=storage,
        symbol="BTC-USD",
        now=now,
        create_repair_request=False,
    )

    assert "secret_leak_detected" not in {finding.code for finding in result.findings}


def test_health_check_allows_blank_example_secret_placeholders(tmp_path, monkeypatch):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.example").write_text(
        "ALPACA_PAPER_API_KEY=\nALPACA_PAPER_API_SECRET=\nTELEGRAM_BOT_TOKEN=\n",
        encoding="utf-8",
    )
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    repository.save_forecast(_forecast("forecast:latest", anchor_time=now, status="pending"))

    result = run_health_check(
        storage_dir=storage,
        symbol="BTC-USD",
        now=now,
        create_repair_request=False,
    )

    assert "secret_leak_detected" not in {finding.code for finding in result.findings}


def test_health_check_allows_example_config_env_variable_names(tmp_path, monkeypatch):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "brokers.example.yml").write_text(
        "\n".join(
            [
                "brokers:",
                "  alpaca_paper:",
                "    api_key_env: ALPACA_PAPER_API_KEY",
                "    api_secret_env: ALPACA_PAPER_API_SECRET",
                "  telegram:",
                "    token_env: TELEGRAM_BOT_TOKEN",
            ]
        ),
        encoding="utf-8",
    )
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    repository.save_forecast(_forecast("forecast:latest", anchor_time=now, status="pending"))

    result = run_health_check(
        storage_dir=storage,
        symbol="BTC-USD",
        now=now,
        create_repair_request=False,
    )

    assert "secret_leak_detected" not in {finding.code for finding in result.findings}


def test_cli_health_check_reports_missing_storage_without_creating_it(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    missing = tmp_path / "missing-storage"

    exit_code = main(
        [
            "health-check",
            "--storage-dir",
            str(missing),
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-24T12:00:00+00:00",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["repair_required"] is True
    assert payload["repair_request_id"] is not None
    assert not missing.exists()
