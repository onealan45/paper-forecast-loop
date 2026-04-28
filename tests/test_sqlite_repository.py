from datetime import UTC, datetime, timedelta
import json
import sqlite3

from forecast_loop.cli import main
from forecast_loop.models import (
    AutomationRun,
    BaselineEvaluation,
    BacktestResult,
    BacktestRun,
    BrokerOrder,
    BrokerReconciliation,
    BrokerOrderStatus,
    ExecutionSafetyGate,
    EquityCurvePoint,
    ExperimentBudget,
    ExperimentTrial,
    EvaluationSummary,
    Forecast,
    ForecastScore,
    MacroEvent,
    MarketCandle,
    MarketCandleRecord,
    NotificationArtifact,
    PaperFill,
    PaperControlEvent,
    PaperOrder,
    PaperOrderStatus,
    PaperOrderType,
    PaperPortfolioSnapshot,
    Proposal,
    ProviderRun,
    RepairRequest,
    ResearchDataset,
    ResearchDatasetRow,
    Review,
    RiskSnapshot,
    StrategyCard,
    StrategyDecision,
    WalkForwardValidation,
    WalkForwardWindow,
)
from forecast_loop.sqlite_repository import DEFAULT_DB_FILENAME, SQLiteRepository
from forecast_loop.storage import JsonFileRepository


def _forecast(now: datetime) -> Forecast:
    return Forecast(
        forecast_id="forecast:sqlite",
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


def _market_candle(now: datetime) -> MarketCandleRecord:
    return MarketCandleRecord.from_candle(
        MarketCandle(
            timestamp=now,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1_000.0,
        ),
        symbol="BTC-USD",
        source="fixture",
        imported_at=now,
    )


def _macro_event(now: datetime) -> MacroEvent:
    return MacroEvent(
        event_id="macro-event:sqlite",
        event_type="CPI",
        name="US CPI",
        region="US",
        scheduled_at=now + timedelta(days=1),
        source="fixture",
        imported_at=now,
        actual_value=None,
        consensus_value=3.1,
        previous_value=3.0,
        unit="percent",
        importance="high",
        notes="test",
    )


def _score(forecast: Forecast) -> ForecastScore:
    return ForecastScore(
        score_id="score:sqlite",
        forecast_id=forecast.forecast_id,
        scored_at=forecast.target_window_end,
        predicted_regime="trend_up",
        actual_regime="trend_up",
        score=1.0,
        target_window_start=forecast.target_window_start,
        target_window_end=forecast.target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=25,
        observed_candle_count=25,
        provider_data_through=forecast.target_window_end,
        scoring_basis="test",
    )


def _review(score: ForecastScore) -> Review:
    return Review(
        review_id="review:sqlite",
        created_at=score.scored_at,
        score_ids=[score.score_id],
        forecast_ids=[score.forecast_id],
        average_score=1.0,
        threshold_used=0.6,
        decision_basis="test",
        summary="ok",
        proposal_recommended=False,
        proposal_reason="threshold_met",
    )


def _proposal(review: Review, score: ForecastScore) -> Proposal:
    return Proposal(
        proposal_id="proposal:sqlite",
        created_at=review.created_at,
        review_id=review.review_id,
        score_ids=[score.score_id],
        proposal_type="risk_adjustment",
        changes={"max_position_pct": 0.15, "new_entry_enabled": False},
        threshold_used=0.6,
        decision_basis="test",
        rationale="test",
    )


def _summary(now: datetime, forecast: Forecast, score: ForecastScore, review: Review, proposal: Proposal) -> EvaluationSummary:
    return EvaluationSummary.from_dict(
        {
            "replay_id": "replay:sqlite",
            "generated_at": now.isoformat(),
            "forecast_ids": [forecast.forecast_id],
            "scored_forecast_ids": [forecast.forecast_id],
            "replay_window_start": now.isoformat(),
            "replay_window_end": (now + timedelta(hours=1)).isoformat(),
            "anchor_time_start": forecast.anchor_time.isoformat(),
            "anchor_time_end": forecast.anchor_time.isoformat(),
            "forecast_count": 1,
            "resolved_count": 1,
            "waiting_for_data_count": 0,
            "unscorable_count": 0,
            "average_score": 1.0,
            "score_ids": [score.score_id],
            "review_ids": [review.review_id],
            "proposal_ids": [proposal.proposal_id],
        }
    )


def _baseline(now: datetime, forecast: Forecast, score: ForecastScore) -> BaselineEvaluation:
    return BaselineEvaluation(
        baseline_id="baseline:sqlite",
        created_at=now,
        symbol="BTC-USD",
        sample_size=1,
        directional_accuracy=1.0,
        baseline_accuracy=0.0,
        model_edge=1.0,
        recent_score=1.0,
        evidence_grade="D",
        forecast_ids=[forecast.forecast_id],
        score_ids=[score.score_id],
        decision_basis="test",
    )


def _decision(now: datetime, forecast: Forecast, score: ForecastScore, review: Review, baseline: BaselineEvaluation) -> StrategyDecision:
    return StrategyDecision(
        decision_id="decision:sqlite",
        created_at=now,
        symbol="BTC-USD",
        horizon_hours=24,
        action="HOLD",
        confidence=0.55,
        evidence_grade="D",
        risk_level="MEDIUM",
        tradeable=False,
        blocked_reason="model_not_beating_baseline",
        recommended_position_pct=0.0,
        current_position_pct=0.0,
        max_position_pct=0.15,
        invalidation_conditions=["test"],
        reason_summary="test",
        forecast_ids=[forecast.forecast_id],
        score_ids=[score.score_id],
        review_ids=[review.review_id],
        baseline_ids=[baseline.baseline_id],
        decision_basis="test",
    )


def _repair_request(now: datetime) -> RepairRequest:
    return RepairRequest(
        repair_request_id="repair:sqlite",
        created_at=now,
        status="pending",
        severity="blocking",
        observed_failure="test",
        reproduction_command="python .\\run_forecast_loop.py health-check --storage-dir test",
        expected_behavior="healthy",
        affected_artifacts=["forecasts.jsonl"],
        recommended_tests=["python -m pytest -q"],
        safety_boundary="paper-only; no live trading",
        acceptance_criteria=["db-health healthy"],
        finding_codes=["test"],
    )


def _control_event(now: datetime) -> PaperControlEvent:
    return PaperControlEvent(
        control_id="control:sqlite",
        created_at=now,
        action="STOP_NEW_ENTRIES",
        actor="operator",
        reason="test control",
        status="ACTIVE",
        symbol="BTC-USD",
        requires_confirmation=False,
        confirmed=False,
        decision_basis="test",
    )


def _automation_run(now: datetime, decision: StrategyDecision) -> AutomationRun:
    return AutomationRun(
        automation_run_id="automation-run:sqlite",
        started_at=now,
        completed_at=now,
        status="completed",
        symbol="BTC-USD",
        provider="sample",
        command="run-once",
        steps=[
            {"name": "forecast", "status": "created", "artifact_id": "forecast:sqlite"},
            {"name": "decide", "status": "completed", "artifact_id": decision.decision_id},
        ],
        health_check_id="health:sqlite",
        decision_id=decision.decision_id,
        repair_request_id=None,
        decision_basis="test",
    )


def _notification(now: datetime, decision: StrategyDecision) -> NotificationArtifact:
    return NotificationArtifact(
        notification_id="notification:sqlite",
        created_at=now,
        symbol="BTC-USD",
        notification_type="NEW_DECISION",
        severity="info",
        title="新策略決策",
        message="BTC-USD 最新 paper-only 決策。",
        status="pending",
        delivery_channel="local_artifact",
        action=decision.action,
        source_artifact_ids=[decision.decision_id],
        decision_id=decision.decision_id,
        health_check_id=None,
        repair_request_id=None,
        risk_id=None,
        decision_basis="test",
    )


def _research_dataset(now: datetime, forecast: Forecast, score: ForecastScore) -> ResearchDataset:
    row = ResearchDatasetRow(
        forecast_id=forecast.forecast_id,
        score_id=score.score_id,
        symbol=forecast.symbol,
        decision_timestamp=forecast.anchor_time,
        feature_timestamp=forecast.anchor_time,
        label_timestamp=score.target_window_end,
        features={"confidence": forecast.confidence},
        label={"score": score.score},
    )
    return ResearchDataset(
        dataset_id="research-dataset:sqlite",
        created_at=now,
        symbol=forecast.symbol,
        row_count=1,
        leakage_status="passed",
        leakage_findings=[],
        forecast_ids=[forecast.forecast_id],
        score_ids=[score.score_id],
        rows=[row],
        decision_basis="test",
    )


def _backtest_run(now: datetime, candle: MarketCandleRecord) -> BacktestRun:
    return BacktestRun(
        backtest_id="backtest-run:sqlite",
        created_at=now,
        symbol="BTC-USD",
        start=candle.timestamp,
        end=candle.timestamp + timedelta(days=1),
        strategy_name="moving_average_trend",
        initial_cash=10_000.0,
        fee_bps=5.0,
        slippage_bps=10.0,
        moving_average_window=3,
        candle_ids=[candle.candle_id],
        decision_basis="test",
    )


def _backtest_result(now: datetime, run: BacktestRun) -> BacktestResult:
    return BacktestResult(
        result_id="backtest-result:sqlite",
        backtest_id=run.backtest_id,
        created_at=now,
        symbol=run.symbol,
        start=run.start,
        end=run.end,
        initial_cash=run.initial_cash,
        final_equity=10_100.0,
        strategy_return=0.01,
        benchmark_return=0.02,
        max_drawdown=0.0,
        sharpe=None,
        turnover=1.0,
        win_rate=None,
        trade_count=1,
        equity_curve=[{"timestamp": now.isoformat(), "equity": 10_100.0}],
        decision_basis="test",
    )


def _walk_forward_validation(now: datetime, result: BacktestResult) -> WalkForwardValidation:
    window = WalkForwardWindow(
        window_id="walk-forward-window:sqlite",
        train_start=now,
        train_end=now + timedelta(days=1),
        validation_start=now + timedelta(days=2),
        validation_end=now + timedelta(days=3),
        test_start=now + timedelta(days=4),
        test_end=now + timedelta(days=5),
        train_candle_count=2,
        validation_candle_count=2,
        test_candle_count=2,
        validation_backtest_result_id=result.result_id,
        test_backtest_result_id=result.result_id,
        validation_return=0.01,
        test_return=0.02,
        benchmark_return=0.01,
        excess_return=0.01,
        overfit_flags=[],
        decision_basis="test",
    )
    return WalkForwardValidation(
        validation_id="walk-forward:sqlite",
        created_at=now,
        symbol="BTC-USD",
        start=now,
        end=now + timedelta(days=5),
        strategy_name="moving_average_trend",
        train_size=2,
        validation_size=2,
        test_size=2,
        step_size=1,
        initial_cash=10_000.0,
        fee_bps=5.0,
        slippage_bps=10.0,
        moving_average_window=3,
        window_count=1,
        average_validation_return=0.01,
        average_test_return=0.02,
        average_benchmark_return=0.01,
        average_excess_return=0.01,
        test_win_rate=1.0,
        overfit_window_count=0,
        overfit_risk_flags=[],
        backtest_result_ids=[result.result_id],
        windows=[window],
        decision_basis="test",
    )


def _strategy_card(now: datetime) -> StrategyCard:
    return StrategyCard(
        card_id="strategy-card:sqlite",
        created_at=now,
        strategy_name="MA trend BTC",
        strategy_family="trend_following",
        version="v1",
        status="ACTIVE",
        symbols=["BTC-USD"],
        hypothesis="BTC trend continuation after moving-average confirmation.",
        signal_description="Fast moving average above slow moving average.",
        entry_rules=["Enter long when fast_ma > slow_ma."],
        exit_rules=["Exit when fast_ma <= slow_ma."],
        risk_rules=["Max position 10% during research simulation."],
        parameters={"fast_window": 3, "slow_window": 7},
        data_requirements=["market_candles:BTC-USD:1h"],
        feature_snapshot_ids=[],
        backtest_result_ids=["backtest-result:sqlite"],
        walk_forward_validation_ids=["walk-forward:sqlite"],
        event_edge_evaluation_ids=[],
        parent_card_id=None,
        author="codex",
        decision_basis="test",
    )


def _experiment_budget(now: datetime, card: StrategyCard) -> ExperimentBudget:
    return ExperimentBudget(
        budget_id="experiment-budget:sqlite",
        created_at=now,
        strategy_card_id=card.card_id,
        max_trials=5,
        used_trials=1,
        remaining_trials=4,
        status="OPEN",
        budget_scope="strategy_card",
        decision_basis="test",
    )


def _experiment_trial(
    now: datetime,
    card: StrategyCard,
    dataset: ResearchDataset,
    result: BacktestResult,
) -> ExperimentTrial:
    return ExperimentTrial(
        trial_id="experiment-trial:sqlite",
        created_at=now,
        strategy_card_id=card.card_id,
        trial_index=1,
        status="FAILED",
        symbol="BTC-USD",
        seed=42,
        dataset_id=dataset.dataset_id,
        backtest_result_id=result.result_id,
        walk_forward_validation_id=None,
        event_edge_evaluation_id=None,
        prompt_hash="prompt-hash",
        code_hash="code-hash",
        parameters={"fast_window": 3, "slow_window": 7},
        metric_summary={"excess_return": -0.01},
        failure_reason="negative_after_cost_edge",
        started_at=now,
        completed_at=now,
        decision_basis="test",
    )


def _paper_order(now: datetime, decision: StrategyDecision) -> PaperOrder:
    return PaperOrder(
        order_id="paper-order:sqlite",
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


def _paper_fill(now: datetime, order: PaperOrder) -> PaperFill:
    return PaperFill(
        fill_id="paper-fill:sqlite",
        order_id=order.order_id,
        decision_id=order.decision_id,
        symbol=order.symbol,
        side=order.side,
        filled_at=now,
        quantity=1.0,
        market_price=100.0,
        fill_price=100.1,
        gross_value=100.1,
        fee=0.05,
        fee_bps=5.0,
        slippage_bps=10.0,
        net_cash_change=-100.15,
    )


def _broker_order(now: datetime, order: PaperOrder) -> BrokerOrder:
    return BrokerOrder(
        broker_order_id="broker-order:sqlite",
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
        status=BrokerOrderStatus.SUBMITTED.value,
        broker_status="SUBMITTED",
        broker_order_ref="testnet:sqlite",
        client_order_id=order.order_id,
        error_message=None,
        raw_response={"mock": True},
        decision_basis="test",
    )


def _broker_reconciliation(now: datetime, broker_order: BrokerOrder) -> BrokerReconciliation:
    return BrokerReconciliation(
        reconciliation_id="broker-reconciliation:sqlite",
        created_at=now,
        broker=broker_order.broker,
        broker_mode=broker_order.broker_mode,
        status="MATCHED",
        severity="none",
        repair_required=False,
        local_broker_order_ids=[broker_order.broker_order_id],
        external_order_refs=[broker_order.broker_order_ref],
        matched_order_refs=[broker_order.broker_order_ref],
        missing_external_order_ids=[],
        unknown_external_order_refs=[],
        duplicate_broker_order_refs=[],
        status_mismatches=[],
        position_mismatches=[],
        cash_mismatch=None,
        equity_mismatch=None,
        findings=[],
        decision_basis="test",
    )


def _execution_gate(
    now: datetime,
    decision: StrategyDecision,
    order: PaperOrder,
    reconciliation: BrokerReconciliation,
) -> ExecutionSafetyGate:
    return ExecutionSafetyGate(
        gate_id="execution-gate:sqlite",
        created_at=now,
        symbol=decision.symbol,
        decision_id=decision.decision_id,
        order_id=order.order_id,
        broker="binance_testnet",
        broker_mode="SANDBOX",
        status="PASS",
        severity="none",
        allowed=True,
        checks=[{"code": "test", "status": "pass"}],
        health_check_id="health:sqlite",
        risk_id="risk:sqlite",
        broker_reconciliation_id=reconciliation.reconciliation_id,
        decision_basis="test",
    )


def _equity_point(now: datetime) -> EquityCurvePoint:
    return EquityCurvePoint(
        point_id="equity:sqlite",
        created_at=now,
        equity=10_000.0,
        cash=9_000.0,
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        gross_exposure_pct=0.1,
        net_exposure_pct=0.1,
        max_drawdown_pct=None,
    )


def _risk_snapshot(now: datetime) -> RiskSnapshot:
    return RiskSnapshot(
        risk_id="risk:sqlite",
        created_at=now,
        symbol="BTC-USD",
        status="OK",
        severity="none",
        current_drawdown_pct=0.0,
        max_drawdown_pct=0.0,
        gross_exposure_pct=0.1,
        net_exposure_pct=0.1,
        position_pct=0.1,
        max_position_pct=0.15,
        max_gross_exposure_pct=0.20,
        reduce_risk_drawdown_pct=0.05,
        stop_new_entries_drawdown_pct=0.10,
        findings=[],
        recommended_action="HOLD",
        decision_basis="test",
    )


def _provider_run(now: datetime) -> ProviderRun:
    return ProviderRun(
        provider_run_id="provider-run:sqlite",
        created_at=now,
        provider="sample",
        symbol="BTC-USD",
        operation="get_recent_candles",
        status="success",
        started_at=now,
        completed_at=now,
        candle_count=3,
        data_start=now - timedelta(hours=2),
        data_end=now,
        schema_version="market_candles_v1",
    )


def _seed_repository(repository) -> dict:
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    forecast = _forecast(now)
    score = _score(forecast)
    review = _review(score)
    proposal = _proposal(review, score)
    summary = _summary(now, forecast, score, review, proposal)
    baseline = _baseline(now, forecast, score)
    decision = _decision(now, forecast, score, review, baseline)
    order = _paper_order(now, decision)
    broker_order = _broker_order(now, order)
    broker_reconciliation = _broker_reconciliation(now, broker_order)
    execution_gate = _execution_gate(now, decision, order, broker_reconciliation)
    fill = _paper_fill(now, order)
    snapshot = PaperPortfolioSnapshot.empty(created_at=now)
    equity_point = _equity_point(now)
    risk_snapshot = _risk_snapshot(now)
    provider_run = _provider_run(now)
    market_candle = _market_candle(now)
    macro_event = _macro_event(now)
    repair_request = _repair_request(now)
    control_event = _control_event(now)
    automation_run = _automation_run(now, decision)
    notification = _notification(now, decision)
    dataset = _research_dataset(now, forecast, score)
    backtest_run = _backtest_run(now, market_candle)
    backtest_result = _backtest_result(now, backtest_run)
    walk_forward_validation = _walk_forward_validation(now, backtest_result)
    strategy_card = _strategy_card(now)
    experiment_budget = _experiment_budget(now, strategy_card)
    experiment_trial = _experiment_trial(now, strategy_card, dataset, backtest_result)

    repository.save_market_candle(market_candle)
    repository.save_macro_event(macro_event)
    repository.save_forecast(forecast)
    repository.save_score(score)
    repository.save_review(review)
    repository.save_proposal(proposal)
    repository.save_evaluation_summary(summary)
    repository.save_baseline_evaluation(baseline)
    repository.save_strategy_decision(decision)
    repository.save_paper_order(order)
    repository.save_broker_order(broker_order)
    repository.save_broker_reconciliation(broker_reconciliation)
    repository.save_execution_safety_gate(execution_gate)
    repository.save_paper_fill(fill)
    repository.save_portfolio_snapshot(snapshot)
    repository.save_equity_curve_point(equity_point)
    repository.save_risk_snapshot(risk_snapshot)
    repository.save_provider_run(provider_run)
    repository.save_repair_request(repair_request)
    repository.save_control_event(control_event)
    repository.save_automation_run(automation_run)
    repository.save_notification_artifact(notification)
    repository.save_research_dataset(dataset)
    repository.save_backtest_run(backtest_run)
    repository.save_backtest_result(backtest_result)
    repository.save_walk_forward_validation(walk_forward_validation)
    repository.save_strategy_card(strategy_card)
    repository.save_experiment_budget(experiment_budget)
    repository.save_experiment_trial(experiment_trial)
    return {
        "forecast": forecast,
        "score": score,
        "review": review,
        "proposal": proposal,
        "summary": summary,
        "baseline": baseline,
        "decision": decision,
        "order": order,
        "broker_order": broker_order,
        "broker_reconciliation": broker_reconciliation,
        "execution_gate": execution_gate,
        "fill": fill,
        "snapshot": snapshot,
        "equity_point": equity_point,
        "risk_snapshot": risk_snapshot,
        "provider_run": provider_run,
        "market_candle": market_candle,
        "macro_event": macro_event,
        "repair_request": repair_request,
        "control_event": control_event,
        "automation_run": automation_run,
        "notification": notification,
        "dataset": dataset,
        "backtest_run": backtest_run,
        "backtest_result": backtest_result,
        "walk_forward_validation": walk_forward_validation,
        "strategy_card": strategy_card,
        "experiment_budget": experiment_budget,
        "experiment_trial": experiment_trial,
    }


def test_sqlite_repository_round_trips_and_dedupes_m1_artifacts(tmp_path):
    repository = SQLiteRepository(tmp_path)
    artifacts = _seed_repository(repository)
    _seed_repository(repository)

    assert repository.schema_versions() == [1]
    assert repository.load_market_candles() == [artifacts["market_candle"]]
    assert repository.load_macro_events() == [artifacts["macro_event"]]
    assert repository.load_forecasts() == [artifacts["forecast"]]
    assert repository.load_scores() == [artifacts["score"]]
    assert repository.load_reviews() == [artifacts["review"]]
    assert repository.load_proposals() == [artifacts["proposal"]]
    assert repository.load_evaluation_summaries() == [artifacts["summary"]]
    assert repository.load_baseline_evaluations() == [artifacts["baseline"]]
    assert repository.load_strategy_decisions() == [artifacts["decision"]]
    assert repository.load_paper_orders() == [artifacts["order"]]
    assert repository.load_broker_orders() == [artifacts["broker_order"]]
    assert repository.load_broker_reconciliations() == [artifacts["broker_reconciliation"]]
    assert repository.load_execution_safety_gates() == [artifacts["execution_gate"]]
    assert repository.load_paper_fills() == [artifacts["fill"]]
    assert repository.load_portfolio_snapshots() == [artifacts["snapshot"]]
    assert repository.load_equity_curve_points() == [artifacts["equity_point"]]
    assert repository.load_risk_snapshots() == [artifacts["risk_snapshot"]]
    assert repository.load_provider_runs() == [artifacts["provider_run"]]
    assert repository.load_repair_requests() == [artifacts["repair_request"]]
    assert repository.load_control_events() == [artifacts["control_event"]]
    assert repository.load_automation_runs() == [artifacts["automation_run"]]
    assert repository.load_notification_artifacts() == [artifacts["notification"]]
    assert repository.load_research_datasets() == [artifacts["dataset"]]
    assert repository.load_backtest_runs() == [artifacts["backtest_run"]]
    assert repository.load_backtest_results() == [artifacts["backtest_result"]]
    assert repository.load_walk_forward_validations() == [artifacts["walk_forward_validation"]]
    assert repository.load_strategy_cards() == [artifacts["strategy_card"]]
    assert repository.load_experiment_budgets() == [artifacts["experiment_budget"]]
    assert repository.load_experiment_trials() == [artifacts["experiment_trial"]]
    assert repository.artifact_counts()["forecasts"] == 1


def test_cli_init_db_and_db_health(tmp_path, capsys):
    assert main(["init-db", "--storage-dir", str(tmp_path)]) == 0
    init_result = json.loads(capsys.readouterr().out)
    assert init_result["schema_version"] == 1
    assert (tmp_path / DEFAULT_DB_FILENAME).exists()

    assert main(["db-health", "--storage-dir", str(tmp_path)]) == 0
    health_result = json.loads(capsys.readouterr().out)
    assert health_result["status"] == "healthy"
    assert health_result["schema_version"] == 1


def test_cli_db_health_missing_database_is_operator_friendly(tmp_path, capsys):
    assert main(["db-health", "--storage-dir", str(tmp_path)]) == 2
    result = json.loads(capsys.readouterr().out)

    assert result["status"] == "unhealthy"
    assert result["repair_required"] is True
    assert result["findings"][0]["code"] == "sqlite_db_missing"


def test_migrate_jsonl_to_sqlite_is_idempotent_and_preserves_parity(tmp_path, capsys):
    json_repository = JsonFileRepository(tmp_path)
    artifacts = _seed_repository(json_repository)

    assert main(["migrate-jsonl-to-sqlite", "--storage-dir", str(tmp_path)]) == 0
    first_result = json.loads(capsys.readouterr().out)
    assert first_result["inserted_counts"]["forecasts"] == 1

    assert main(["migrate-jsonl-to-sqlite", "--storage-dir", str(tmp_path)]) == 0
    second_result = json.loads(capsys.readouterr().out)
    assert all(count == 0 for count in second_result["inserted_counts"].values())

    sqlite_repository = SQLiteRepository(tmp_path, initialize=False)
    assert sqlite_repository.load_forecasts() == [artifacts["forecast"]]
    assert sqlite_repository.load_market_candles() == [artifacts["market_candle"]]
    assert sqlite_repository.load_macro_events() == [artifacts["macro_event"]]
    assert sqlite_repository.load_scores() == [artifacts["score"]]
    assert sqlite_repository.load_strategy_decisions() == [artifacts["decision"]]
    assert sqlite_repository.load_paper_orders() == [artifacts["order"]]
    assert sqlite_repository.load_broker_orders() == [artifacts["broker_order"]]
    assert sqlite_repository.load_broker_reconciliations() == [artifacts["broker_reconciliation"]]
    assert sqlite_repository.load_execution_safety_gates() == [artifacts["execution_gate"]]
    assert sqlite_repository.load_paper_fills() == [artifacts["fill"]]
    assert sqlite_repository.load_control_events() == [artifacts["control_event"]]
    assert sqlite_repository.load_automation_runs() == [artifacts["automation_run"]]
    assert sqlite_repository.load_notification_artifacts() == [artifacts["notification"]]
    assert sqlite_repository.load_research_datasets() == [artifacts["dataset"]]
    assert sqlite_repository.load_backtest_runs() == [artifacts["backtest_run"]]
    assert sqlite_repository.load_backtest_results() == [artifacts["backtest_result"]]
    assert sqlite_repository.load_walk_forward_validations() == [artifacts["walk_forward_validation"]]
    assert sqlite_repository.load_strategy_cards() == [artifacts["strategy_card"]]
    assert sqlite_repository.load_experiment_budgets() == [artifacts["experiment_budget"]]
    assert sqlite_repository.load_experiment_trials() == [artifacts["experiment_trial"]]

    assert main(["db-health", "--storage-dir", str(tmp_path)]) == 0
    health_result = json.loads(capsys.readouterr().out)
    assert health_result["artifact_counts"]["forecasts"] == 1
    assert health_result["artifact_counts"]["market_candles"] == 1
    assert health_result["artifact_counts"]["macro_events"] == 1
    assert health_result["artifact_counts"]["strategy_decisions"] == 1
    assert health_result["artifact_counts"]["paper_orders"] == 1
    assert health_result["artifact_counts"]["broker_orders"] == 1
    assert health_result["artifact_counts"]["broker_reconciliations"] == 1
    assert health_result["artifact_counts"]["execution_safety_gates"] == 1
    assert health_result["artifact_counts"]["paper_fills"] == 1
    assert health_result["artifact_counts"]["control_events"] == 1
    assert health_result["artifact_counts"]["automation_runs"] == 1
    assert health_result["artifact_counts"]["notification_artifacts"] == 1
    assert health_result["artifact_counts"]["equity_curve"] == 1
    assert health_result["artifact_counts"]["risk_snapshots"] == 1
    assert health_result["artifact_counts"]["provider_runs"] == 1
    assert health_result["artifact_counts"]["research_datasets"] == 1
    assert health_result["artifact_counts"]["backtest_runs"] == 1
    assert health_result["artifact_counts"]["backtest_results"] == 1
    assert health_result["artifact_counts"]["walk_forward_validations"] == 1
    assert health_result["artifact_counts"]["strategy_cards"] == 1
    assert health_result["artifact_counts"]["experiment_budgets"] == 1
    assert health_result["artifact_counts"]["experiment_trials"] == 1


def test_db_health_flags_malformed_provider_run_payload(tmp_path, capsys):
    repository = SQLiteRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    provider_run = _provider_run(now)
    repository.save_provider_run(provider_run)
    bad_payload = provider_run.to_dict()
    bad_payload.pop("schema_version")
    bad_payload.pop("completed_at")

    with sqlite3.connect(tmp_path / DEFAULT_DB_FILENAME) as connection:
        connection.execute(
            """
            UPDATE artifacts
            SET payload_json = ?
            WHERE artifact_type = 'provider_runs' AND artifact_id = ?
            """,
            (json.dumps(bad_payload, sort_keys=True), provider_run.provider_run_id),
        )

    assert main(["db-health", "--storage-dir", str(tmp_path)]) == 2
    health_result = json.loads(capsys.readouterr().out)

    assert health_result["status"] == "unhealthy"
    assert "sqlite_bad_payload" in {finding["code"] for finding in health_result["findings"]}


def test_export_jsonl_writes_compatibility_artifacts(tmp_path, capsys):
    json_repository = JsonFileRepository(tmp_path)
    artifacts = _seed_repository(json_repository)
    export_dir = tmp_path / "exported-jsonl"

    assert main(["migrate-jsonl-to-sqlite", "--storage-dir", str(tmp_path)]) == 0
    capsys.readouterr()
    assert main(["export-jsonl", "--storage-dir", str(tmp_path), "--output-dir", str(export_dir)]) == 0
    export_result = json.loads(capsys.readouterr().out)

    exported_repository = JsonFileRepository(export_dir)
    assert export_result["artifact_counts"]["forecasts"] == 1
    assert exported_repository.load_market_candles() == [artifacts["market_candle"]]
    assert exported_repository.load_macro_events() == [artifacts["macro_event"]]
    assert exported_repository.load_forecasts() == [artifacts["forecast"]]
    assert exported_repository.load_scores() == [artifacts["score"]]
    assert exported_repository.load_strategy_decisions() == [artifacts["decision"]]
    assert exported_repository.load_paper_orders() == [artifacts["order"]]
    assert exported_repository.load_broker_orders() == [artifacts["broker_order"]]
    assert exported_repository.load_broker_reconciliations() == [artifacts["broker_reconciliation"]]
    assert exported_repository.load_execution_safety_gates() == [artifacts["execution_gate"]]
    assert exported_repository.load_paper_fills() == [artifacts["fill"]]
    assert exported_repository.load_control_events() == [artifacts["control_event"]]
    assert exported_repository.load_automation_runs() == [artifacts["automation_run"]]
    assert exported_repository.load_notification_artifacts() == [artifacts["notification"]]
    assert exported_repository.load_equity_curve_points() == [artifacts["equity_point"]]
    assert exported_repository.load_risk_snapshots() == [artifacts["risk_snapshot"]]
    assert exported_repository.load_provider_runs() == [artifacts["provider_run"]]
    assert exported_repository.load_repair_requests() == [artifacts["repair_request"]]
    assert exported_repository.load_research_datasets() == [artifacts["dataset"]]
    assert exported_repository.load_backtest_runs() == [artifacts["backtest_run"]]
    assert exported_repository.load_backtest_results() == [artifacts["backtest_result"]]
    assert exported_repository.load_walk_forward_validations() == [artifacts["walk_forward_validation"]]
    assert exported_repository.load_strategy_cards() == [artifacts["strategy_card"]]
    assert exported_repository.load_experiment_budgets() == [artifacts["experiment_budget"]]
    assert exported_repository.load_experiment_trials() == [artifacts["experiment_trial"]]
