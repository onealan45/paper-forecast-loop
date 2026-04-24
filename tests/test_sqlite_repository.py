from datetime import UTC, datetime, timedelta
import json

from forecast_loop.cli import main
from forecast_loop.models import (
    BaselineEvaluation,
    EvaluationSummary,
    Forecast,
    ForecastScore,
    PaperOrder,
    PaperOrderStatus,
    PaperOrderType,
    PaperPortfolioSnapshot,
    Proposal,
    RepairRequest,
    Review,
    StrategyDecision,
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
    snapshot = PaperPortfolioSnapshot.empty(created_at=now)
    repair_request = _repair_request(now)

    repository.save_forecast(forecast)
    repository.save_score(score)
    repository.save_review(review)
    repository.save_proposal(proposal)
    repository.save_evaluation_summary(summary)
    repository.save_baseline_evaluation(baseline)
    repository.save_strategy_decision(decision)
    repository.save_paper_order(order)
    repository.save_portfolio_snapshot(snapshot)
    repository.save_repair_request(repair_request)
    return {
        "forecast": forecast,
        "score": score,
        "review": review,
        "proposal": proposal,
        "summary": summary,
        "baseline": baseline,
        "decision": decision,
        "order": order,
        "snapshot": snapshot,
        "repair_request": repair_request,
    }


def test_sqlite_repository_round_trips_and_dedupes_m1_artifacts(tmp_path):
    repository = SQLiteRepository(tmp_path)
    artifacts = _seed_repository(repository)
    _seed_repository(repository)

    assert repository.schema_versions() == [1]
    assert repository.load_forecasts() == [artifacts["forecast"]]
    assert repository.load_scores() == [artifacts["score"]]
    assert repository.load_reviews() == [artifacts["review"]]
    assert repository.load_proposals() == [artifacts["proposal"]]
    assert repository.load_evaluation_summaries() == [artifacts["summary"]]
    assert repository.load_baseline_evaluations() == [artifacts["baseline"]]
    assert repository.load_strategy_decisions() == [artifacts["decision"]]
    assert repository.load_paper_orders() == [artifacts["order"]]
    assert repository.load_portfolio_snapshots() == [artifacts["snapshot"]]
    assert repository.load_repair_requests() == [artifacts["repair_request"]]
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
    assert sqlite_repository.load_scores() == [artifacts["score"]]
    assert sqlite_repository.load_strategy_decisions() == [artifacts["decision"]]
    assert sqlite_repository.load_paper_orders() == [artifacts["order"]]

    assert main(["db-health", "--storage-dir", str(tmp_path)]) == 0
    health_result = json.loads(capsys.readouterr().out)
    assert health_result["artifact_counts"]["forecasts"] == 1
    assert health_result["artifact_counts"]["strategy_decisions"] == 1
    assert health_result["artifact_counts"]["paper_orders"] == 1


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
    assert exported_repository.load_forecasts() == [artifacts["forecast"]]
    assert exported_repository.load_scores() == [artifacts["score"]]
    assert exported_repository.load_strategy_decisions() == [artifacts["decision"]]
    assert exported_repository.load_paper_orders() == [artifacts["order"]]
