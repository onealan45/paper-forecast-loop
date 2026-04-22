import json
from datetime import UTC, datetime, timedelta

from forecast_loop.evaluation import build_evaluation_summary
from forecast_loop.config import LoopConfig
from forecast_loop.models import Forecast, ForecastScore, Proposal, Review
from forecast_loop.providers import InMemoryMarketDataProvider
from forecast_loop.replay import ReplayRunner
from forecast_loop.storage import JsonFileRepository


def make_hourly_candles(start: datetime, count: int, *, start_price: float = 100.0, step: float = 1.0):
    from forecast_loop.models import MarketCandle

    return [
        MarketCandle(
            timestamp=start + timedelta(hours=index),
            open=start_price + (index * step),
            high=start_price + (index * step) + 0.5,
            low=start_price + (index * step) - 0.5,
            close=start_price + (index * step),
            volume=1_000 + index,
        )
        for index in range(count)
    ]


def test_build_evaluation_summary_uses_existing_artifacts_only(tmp_path):
    repository = JsonFileRepository(tmp_path)
    forecast = Forecast(
        forecast_id="forecast:a",
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        anchor_time=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        target_window_start=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        candle_interval_minutes=60,
        expected_candle_count=2,
        status="resolved",
        status_reason="scored",
        predicted_regime="trend_up",
        confidence=0.55,
        provider_data_through=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        observed_candle_count=2,
    )
    score = ForecastScore(
        score_id="score:a",
        forecast_id=forecast.forecast_id,
        scored_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        predicted_regime="trend_up",
        actual_regime="trend_up",
        score=1.0,
        target_window_start=forecast.target_window_start,
        target_window_end=forecast.target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=2,
        observed_candle_count=2,
        provider_data_through=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        scoring_basis="regime_direction_over_fully_covered_hourly_window",
    )

    summary = build_evaluation_summary(
        replay_id="replay:demo",
        generated_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        forecasts=[forecast],
        scores=[score],
        reviews=[],
        proposals=[],
    )

    assert summary.replay_id == "replay:demo"
    assert summary.forecast_count == 1
    assert summary.resolved_count == 1
    assert summary.waiting_for_data_count == 0
    assert summary.unscorable_count == 0
    assert summary.average_score == 1.0
    assert summary.score_ids == ["score:a"]

    repository.save_evaluation_summary(summary)
    assert repository.load_evaluation_summaries() == [summary]


def test_build_evaluation_summary_uses_none_when_no_scores(tmp_path):
    repository = JsonFileRepository(tmp_path)
    forecast = Forecast(
        forecast_id="forecast:a",
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        anchor_time=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        target_window_start=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        candle_interval_minutes=60,
        expected_candle_count=2,
        status="waiting_for_data",
        status_reason="awaiting_provider_coverage",
        predicted_regime="trend_up",
        confidence=0.55,
        provider_data_through=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        observed_candle_count=1,
    )

    summary = build_evaluation_summary(
        replay_id="replay:demo",
        generated_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        forecasts=[forecast],
        scores=[],
        reviews=[],
        proposals=[],
    )

    assert summary.average_score is None
    assert summary.scored_forecast_ids == []
    repository.save_evaluation_summary(summary)
    assert repository.load_evaluation_summaries()[0].average_score is None


def test_replay_evaluation_summary_persists_stronger_provenance_and_idempotency(tmp_path):
    provider = InMemoryMarketDataProvider(
        {
            "BTC-USD": make_hourly_candles(
                datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
                12,
                start_price=100,
                step=2,
            )
        }
    )
    repository = JsonFileRepository(tmp_path)
    runner = ReplayRunner(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=2, lookback_candles=3),
        data_provider=provider,
        repository=repository,
    )

    runner.run_range(
        start=datetime(2026, 4, 21, 4, 0, tzinfo=UTC),
        end=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
    )

    forecasts = repository.load_forecasts()
    scores = repository.load_scores()
    reviews = repository.load_reviews()
    proposals = repository.load_proposals()

    summary_one = build_evaluation_summary(
        replay_id="replay:demo",
        generated_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        forecasts=forecasts,
        scores=scores,
        reviews=reviews,
        proposals=proposals,
    )
    summary_two = build_evaluation_summary(
        replay_id="replay:demo",
        generated_at=datetime(2026, 4, 21, 9, 5, tzinfo=UTC),
        forecasts=forecasts,
        scores=scores,
        reviews=reviews,
        proposals=proposals,
    )

    assert summary_one.summary_id == summary_two.summary_id
    assert summary_one.forecast_ids == sorted(forecast.forecast_id for forecast in forecasts)
    assert summary_one.scored_forecast_ids == sorted(score.forecast_id for score in scores)
    assert summary_one.score_ids == sorted(score.score_id for score in scores)
    assert summary_one.replay_window_start == datetime(2026, 4, 21, 4, 0, tzinfo=UTC)
    assert summary_one.replay_window_end == datetime(2026, 4, 21, 10, 0, tzinfo=UTC)
    assert summary_one.anchor_time_start == datetime(2026, 4, 21, 4, 0, tzinfo=UTC)
    assert summary_one.anchor_time_end == datetime(2026, 4, 21, 8, 0, tzinfo=UTC)
    assert summary_one.average_score is not None

    repository.save_evaluation_summary(summary_one)
    repository.save_evaluation_summary(summary_two)

    persisted = repository.load_evaluation_summaries()
    assert len(persisted) == 1
    assert persisted[0].summary_id == summary_one.summary_id
    assert persisted[0].forecast_ids == summary_one.forecast_ids
    assert persisted[0].scored_forecast_ids == summary_one.scored_forecast_ids
    assert persisted[0].score_ids == summary_one.score_ids
    assert persisted[0].average_score == summary_one.average_score


def test_replay_evaluation_summary_identity_ignores_replay_id_but_keeps_evidence(tmp_path):
    forecast = Forecast(
        forecast_id="forecast:a",
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        anchor_time=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        target_window_start=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        candle_interval_minutes=60,
        expected_candle_count=2,
        status="resolved",
        status_reason="scored",
        predicted_regime="trend_up",
        confidence=0.55,
        provider_data_through=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        observed_candle_count=2,
    )
    score = ForecastScore(
        score_id="score:a",
        forecast_id=forecast.forecast_id,
        scored_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        predicted_regime="trend_up",
        actual_regime="trend_up",
        score=1.0,
        target_window_start=forecast.target_window_start,
        target_window_end=forecast.target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=2,
        observed_candle_count=2,
        provider_data_through=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        scoring_basis="regime_direction_over_fully_covered_hourly_window",
    )
    review = Review(
        review_id="review:a",
        created_at=datetime(2026, 4, 21, 9, 5, tzinfo=UTC),
        score_ids=[score.score_id],
        forecast_ids=[forecast.forecast_id],
        average_score=1.0,
        threshold_used=0.6,
        decision_basis="average of last 1 valid scores",
        summary="keep current settings",
        proposal_recommended=True,
        proposal_reason="average_score_below_threshold",
    )
    proposal = Proposal(
        proposal_id="proposal:a",
        created_at=datetime(2026, 4, 21, 9, 6, tzinfo=UTC),
        review_id=review.review_id,
        score_ids=[score.score_id],
        proposal_type="risk_adjustment",
        changes={"max_position_pct": 0.15, "new_entry_enabled": False},
        threshold_used=0.6,
        decision_basis="average of last 1 valid scores",
        rationale="Generated because average_score_below_threshold against threshold 0.60.",
    )

    summary_a = build_evaluation_summary(
        replay_id="replay:alpha",
        generated_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        forecasts=[forecast],
        scores=[score],
        reviews=[review],
        proposals=[proposal],
    )
    summary_b = build_evaluation_summary(
        replay_id="replay:beta",
        generated_at=datetime(2026, 4, 21, 9, 1, tzinfo=UTC),
        forecasts=[forecast],
        scores=[score],
        reviews=[review],
        proposals=[proposal],
    )

    assert summary_a.summary_id == summary_b.summary_id
    assert summary_a.review_ids == ["review:a"]
    assert summary_a.proposal_ids == ["proposal:a"]
    assert summary_a.score_ids == ["score:a"]


def test_replay_evaluation_summary_identity_changes_when_review_id_changes(tmp_path):
    forecast = Forecast(
        forecast_id="forecast:a",
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        anchor_time=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        target_window_start=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        candle_interval_minutes=60,
        expected_candle_count=2,
        status="resolved",
        status_reason="scored",
        predicted_regime="trend_up",
        confidence=0.55,
        provider_data_through=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        observed_candle_count=2,
    )
    score = ForecastScore(
        score_id="score:a",
        forecast_id=forecast.forecast_id,
        scored_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        predicted_regime="trend_up",
        actual_regime="trend_up",
        score=1.0,
        target_window_start=forecast.target_window_start,
        target_window_end=forecast.target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=2,
        observed_candle_count=2,
        provider_data_through=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        scoring_basis="regime_direction_over_fully_covered_hourly_window",
    )
    review_a = Review(
        review_id="review:a",
        created_at=datetime(2026, 4, 21, 9, 5, tzinfo=UTC),
        score_ids=[score.score_id],
        forecast_ids=[forecast.forecast_id],
        average_score=1.0,
        threshold_used=0.6,
        decision_basis="average of last 1 valid scores",
        summary="keep current settings",
        proposal_recommended=True,
        proposal_reason="average_score_below_threshold",
    )
    review_b = Review(
        review_id="review:b",
        created_at=datetime(2026, 4, 21, 9, 5, tzinfo=UTC),
        score_ids=[score.score_id],
        forecast_ids=[forecast.forecast_id],
        average_score=1.0,
        threshold_used=0.6,
        decision_basis="average of last 1 valid scores",
        summary="keep current settings",
        proposal_recommended=True,
        proposal_reason="average_score_below_threshold",
    )
    proposal = Proposal(
        proposal_id="proposal:a",
        created_at=datetime(2026, 4, 21, 9, 6, tzinfo=UTC),
        review_id=review_a.review_id,
        score_ids=[score.score_id],
        proposal_type="risk_adjustment",
        changes={"max_position_pct": 0.15, "new_entry_enabled": False},
        threshold_used=0.6,
        decision_basis="average of last 1 valid scores",
        rationale="Generated because average_score_below_threshold against threshold 0.60.",
    )

    summary_a = build_evaluation_summary(
        replay_id="replay:alpha",
        generated_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        forecasts=[forecast],
        scores=[score],
        reviews=[review_a],
        proposals=[proposal],
    )
    summary_b = build_evaluation_summary(
        replay_id="replay:alpha",
        generated_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        forecasts=[forecast],
        scores=[score],
        reviews=[review_b],
        proposals=[proposal],
    )

    assert summary_a.summary_id != summary_b.summary_id
    assert summary_a.review_ids == ["review:a"]
    assert summary_b.review_ids == ["review:b"]


def test_replay_evaluation_summary_identity_changes_when_proposal_id_changes(tmp_path):
    forecast = Forecast(
        forecast_id="forecast:a",
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        anchor_time=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        target_window_start=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        candle_interval_minutes=60,
        expected_candle_count=2,
        status="resolved",
        status_reason="scored",
        predicted_regime="trend_up",
        confidence=0.55,
        provider_data_through=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        observed_candle_count=2,
    )
    score = ForecastScore(
        score_id="score:a",
        forecast_id=forecast.forecast_id,
        scored_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        predicted_regime="trend_up",
        actual_regime="trend_up",
        score=1.0,
        target_window_start=forecast.target_window_start,
        target_window_end=forecast.target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=2,
        observed_candle_count=2,
        provider_data_through=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        scoring_basis="regime_direction_over_fully_covered_hourly_window",
    )
    review = Review(
        review_id="review:a",
        created_at=datetime(2026, 4, 21, 9, 5, tzinfo=UTC),
        score_ids=[score.score_id],
        forecast_ids=[forecast.forecast_id],
        average_score=1.0,
        threshold_used=0.6,
        decision_basis="average of last 1 valid scores",
        summary="keep current settings",
        proposal_recommended=True,
        proposal_reason="average_score_below_threshold",
    )
    proposal_a = Proposal(
        proposal_id="proposal:a",
        created_at=datetime(2026, 4, 21, 9, 6, tzinfo=UTC),
        review_id=review.review_id,
        score_ids=[score.score_id],
        proposal_type="risk_adjustment",
        changes={"max_position_pct": 0.15, "new_entry_enabled": False},
        threshold_used=0.6,
        decision_basis="average of last 1 valid scores",
        rationale="Generated because average_score_below_threshold against threshold 0.60.",
    )
    proposal_b = Proposal(
        proposal_id="proposal:b",
        created_at=datetime(2026, 4, 21, 9, 6, tzinfo=UTC),
        review_id=review.review_id,
        score_ids=[score.score_id],
        proposal_type="risk_adjustment",
        changes={"max_position_pct": 0.15, "new_entry_enabled": False},
        threshold_used=0.6,
        decision_basis="average of last 1 valid scores",
        rationale="Generated because average_score_below_threshold against threshold 0.60.",
    )

    summary_a = build_evaluation_summary(
        replay_id="replay:alpha",
        generated_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        forecasts=[forecast],
        scores=[score],
        reviews=[review],
        proposals=[proposal_a],
    )
    summary_b = build_evaluation_summary(
        replay_id="replay:alpha",
        generated_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        forecasts=[forecast],
        scores=[score],
        reviews=[review],
        proposals=[proposal_b],
    )

    assert summary_a.summary_id != summary_b.summary_id
    assert summary_a.proposal_ids == ["proposal:a"]
    assert summary_b.proposal_ids == ["proposal:b"]


def test_replay_evaluation_summary_recomputes_canonical_identity_on_load(tmp_path):
    forecast = Forecast(
        forecast_id="forecast:a",
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        anchor_time=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        target_window_start=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        candle_interval_minutes=60,
        expected_candle_count=2,
        status="resolved",
        status_reason="scored",
        predicted_regime="trend_up",
        confidence=0.55,
        provider_data_through=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        observed_candle_count=2,
    )
    score = ForecastScore(
        score_id="score:a",
        forecast_id=forecast.forecast_id,
        scored_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        predicted_regime="trend_up",
        actual_regime="trend_up",
        score=1.0,
        target_window_start=forecast.target_window_start,
        target_window_end=forecast.target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=2,
        observed_candle_count=2,
        provider_data_through=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        scoring_basis="regime_direction_over_fully_covered_hourly_window",
    )
    review = Review(
        review_id="review:a",
        created_at=datetime(2026, 4, 21, 9, 5, tzinfo=UTC),
        score_ids=[score.score_id],
        forecast_ids=[forecast.forecast_id],
        average_score=1.0,
        threshold_used=0.6,
        decision_basis="average of last 1 valid scores",
        summary="keep current settings",
        proposal_recommended=False,
        proposal_reason="average_score_at_or_above_threshold",
    )

    summary = build_evaluation_summary(
        replay_id="replay:alpha",
        generated_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        forecasts=[forecast],
        scores=[score],
        reviews=[review],
        proposals=[],
    )

    repository = JsonFileRepository(tmp_path)
    repository.save_evaluation_summary(summary)

    path = repository.evaluation_summaries_path
    payload = path.read_text(encoding="utf-8").strip()
    path.write_text(payload.replace(summary.summary_id, "evaluation-summary:stale"), encoding="utf-8")

    loaded = repository.load_evaluation_summaries()
    assert len(loaded) == 1
    assert loaded[0].summary_id == summary.summary_id
    assert loaded[0].review_ids == ["review:a"]


def test_replay_evaluation_summary_load_collapses_duplicate_stale_rows(tmp_path):
    repository = JsonFileRepository(tmp_path)
    forecast = Forecast(
        forecast_id="forecast:a",
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        anchor_time=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        target_window_start=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        candle_interval_minutes=60,
        expected_candle_count=2,
        status="resolved",
        status_reason="scored",
        predicted_regime="trend_up",
        confidence=0.55,
        provider_data_through=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        observed_candle_count=2,
    )
    score = ForecastScore(
        score_id="score:a",
        forecast_id=forecast.forecast_id,
        scored_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        predicted_regime="trend_up",
        actual_regime="trend_up",
        score=1.0,
        target_window_start=forecast.target_window_start,
        target_window_end=forecast.target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=2,
        observed_candle_count=2,
        provider_data_through=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        scoring_basis="regime_direction_over_fully_covered_hourly_window",
    )
    review = Review(
        review_id="review:a",
        created_at=datetime(2026, 4, 21, 9, 5, tzinfo=UTC),
        score_ids=[score.score_id],
        forecast_ids=[forecast.forecast_id],
        average_score=1.0,
        threshold_used=0.6,
        decision_basis="average of last 1 valid scores",
        summary="keep current settings",
        proposal_recommended=True,
        proposal_reason="average_score_below_threshold",
    )
    proposal = Proposal(
        proposal_id="proposal:a",
        created_at=datetime(2026, 4, 21, 9, 6, tzinfo=UTC),
        review_id=review.review_id,
        score_ids=[score.score_id],
        proposal_type="risk_adjustment",
        changes={"max_position_pct": 0.15, "new_entry_enabled": False},
        threshold_used=0.6,
        decision_basis="average of last 1 valid scores",
        rationale="Generated because average_score_below_threshold against threshold 0.60.",
    )

    summary = build_evaluation_summary(
        replay_id="replay:alpha",
        generated_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        forecasts=[forecast],
        scores=[score],
        reviews=[review],
        proposals=[proposal],
    )

    first_row = summary.to_dict()
    second_row = summary.to_dict()
    first_row["summary_id"] = "evaluation-summary:stale-a"
    second_row["summary_id"] = "evaluation-summary:stale-b"
    repository.evaluation_summaries_path.write_text(
        "\n".join((json.dumps(first_row), json.dumps(second_row))) + "\n",
        encoding="utf-8",
    )

    loaded = repository.load_evaluation_summaries()
    assert len(loaded) == 1
    assert loaded[0].summary_id == summary.summary_id
    assert loaded[0].review_ids == ["review:a"]
    assert loaded[0].proposal_ids == ["proposal:a"]


def test_replay_evaluation_summary_save_recomputes_canonical_identity(tmp_path):
    repository = JsonFileRepository(tmp_path)
    forecast = Forecast(
        forecast_id="forecast:a",
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        anchor_time=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        target_window_start=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        candle_interval_minutes=60,
        expected_candle_count=2,
        status="resolved",
        status_reason="scored",
        predicted_regime="trend_up",
        confidence=0.55,
        provider_data_through=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        observed_candle_count=2,
    )
    score = ForecastScore(
        score_id="score:a",
        forecast_id=forecast.forecast_id,
        scored_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        predicted_regime="trend_up",
        actual_regime="trend_up",
        score=1.0,
        target_window_start=forecast.target_window_start,
        target_window_end=forecast.target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=2,
        observed_candle_count=2,
        provider_data_through=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        scoring_basis="regime_direction_over_fully_covered_hourly_window",
    )
    review = Review(
        review_id="review:a",
        created_at=datetime(2026, 4, 21, 9, 5, tzinfo=UTC),
        score_ids=[score.score_id],
        forecast_ids=[forecast.forecast_id],
        average_score=1.0,
        threshold_used=0.6,
        decision_basis="average of last 1 valid scores",
        summary="keep current settings",
        proposal_recommended=True,
        proposal_reason="average_score_below_threshold",
    )
    proposal = Proposal(
        proposal_id="proposal:a",
        created_at=datetime(2026, 4, 21, 9, 6, tzinfo=UTC),
        review_id=review.review_id,
        score_ids=[score.score_id],
        proposal_type="risk_adjustment",
        changes={"max_position_pct": 0.15, "new_entry_enabled": False},
        threshold_used=0.6,
        decision_basis="average of last 1 valid scores",
        rationale="Generated because average_score_below_threshold against threshold 0.60.",
    )

    summary = build_evaluation_summary(
        replay_id="replay:alpha",
        generated_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        forecasts=[forecast],
        scores=[score],
        reviews=[review],
        proposals=[proposal],
    )
    repository.save_evaluation_summary(summary)

    stale = build_evaluation_summary(
        replay_id="replay:beta",
        generated_at=datetime(2026, 4, 21, 9, 1, tzinfo=UTC),
        forecasts=[forecast],
        scores=[score],
        reviews=[review],
        proposals=[proposal],
    )
    stale.summary_id = "evaluation-summary:stale"
    repository.save_evaluation_summary(stale)

    persisted = repository.load_evaluation_summaries()
    assert len(persisted) == 1
    assert persisted[0].summary_id == summary.summary_id
    assert persisted[0].review_ids == ["review:a"]
    assert persisted[0].proposal_ids == ["proposal:a"]


def test_replay_evaluation_summary_identity_changes_when_score_id_changes(tmp_path):
    repository = JsonFileRepository(tmp_path)
    forecast = Forecast(
        forecast_id="forecast:a",
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        anchor_time=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        target_window_start=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        candle_interval_minutes=60,
        expected_candle_count=2,
        status="resolved",
        status_reason="scored",
        predicted_regime="trend_up",
        confidence=0.55,
        provider_data_through=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        observed_candle_count=2,
    )
    score_a = ForecastScore(
        score_id="score:a",
        forecast_id=forecast.forecast_id,
        scored_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        predicted_regime="trend_up",
        actual_regime="trend_up",
        score=1.0,
        target_window_start=forecast.target_window_start,
        target_window_end=forecast.target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=2,
        observed_candle_count=2,
        provider_data_through=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        scoring_basis="regime_direction_over_fully_covered_hourly_window",
    )
    score_b = ForecastScore(
        score_id="score:b",
        forecast_id=forecast.forecast_id,
        scored_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        predicted_regime="trend_up",
        actual_regime="trend_up",
        score=1.0,
        target_window_start=forecast.target_window_start,
        target_window_end=forecast.target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=2,
        observed_candle_count=2,
        provider_data_through=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        scoring_basis="regime_direction_over_fully_covered_hourly_window",
    )

    summary_a = build_evaluation_summary(
        replay_id="replay:demo",
        generated_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        forecasts=[forecast],
        scores=[score_a],
        reviews=[],
        proposals=[],
    )
    summary_b = build_evaluation_summary(
        replay_id="replay:demo",
        generated_at=datetime(2026, 4, 21, 9, 5, tzinfo=UTC),
        forecasts=[forecast],
        scores=[score_b],
        reviews=[],
        proposals=[],
    )

    assert summary_a.summary_id != summary_b.summary_id

    repository.save_evaluation_summary(summary_a)
    repository.save_evaluation_summary(summary_b)

    persisted = repository.load_evaluation_summaries()
    assert len(persisted) == 2
    assert {item.summary_id for item in persisted} == {summary_a.summary_id, summary_b.summary_id}
    assert persisted[0].score_ids != persisted[1].score_ids


def test_replay_runner_advances_hourly_and_reuses_existing_contract(tmp_path):
    provider = InMemoryMarketDataProvider(
        {
            "BTC-USD": make_hourly_candles(
                datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
                12,
                start_price=100,
                step=2,
            )
        }
    )
    repository = JsonFileRepository(tmp_path)
    runner = ReplayRunner(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=2, lookback_candles=3),
        data_provider=provider,
        repository=repository,
    )

    result = runner.run_range(
        start=datetime(2026, 4, 21, 4, 0, tzinfo=UTC),
        end=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
    )

    assert result.cycles_run == 5
    assert result.forecasts_created == 5
    assert result.scores_created == 3
    assert result.first_cycle_at == datetime(2026, 4, 21, 4, 0, tzinfo=UTC)
    assert result.last_cycle_at == datetime(2026, 4, 21, 8, 0, tzinfo=UTC)


def test_replay_runner_counts_only_actual_forecast_inserts_on_rerun(tmp_path):
    provider = InMemoryMarketDataProvider(
        {
            "BTC-USD": make_hourly_candles(
                datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
                12,
                start_price=100,
                step=2,
            )
        }
    )
    repository = JsonFileRepository(tmp_path)
    runner = ReplayRunner(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=2, lookback_candles=3),
        data_provider=provider,
        repository=repository,
    )

    first_run = runner.run_range(
        start=datetime(2026, 4, 21, 4, 0, tzinfo=UTC),
        end=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
    )
    second_run = runner.run_range(
        start=datetime(2026, 4, 21, 4, 0, tzinfo=UTC),
        end=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
    )

    assert first_run.forecasts_created == 5
    assert second_run.cycles_run == 5
    assert second_run.forecasts_created == 0
    assert len(repository.load_forecasts()) == 5


def test_replay_runner_rejects_non_hour_aligned_input_range(tmp_path):
    provider = InMemoryMarketDataProvider(
        {
            "BTC-USD": make_hourly_candles(
                datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
                12,
                start_price=100,
                step=2,
            )
        }
    )
    runner = ReplayRunner(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=2, lookback_candles=3),
        data_provider=provider,
        repository=JsonFileRepository(tmp_path),
    )

    try:
        runner.run_range(
            start=datetime(2026, 4, 21, 4, 30, tzinfo=UTC),
            end=datetime(2026, 4, 21, 8, 15, tzinfo=UTC),
        )
    except ValueError as exc:
        assert "hour-aligned" in str(exc)
    else:
        raise AssertionError("expected ValueError for non-hour-aligned replay range")


def test_replay_runner_rejects_reversed_input_range(tmp_path):
    provider = InMemoryMarketDataProvider(
        {
            "BTC-USD": make_hourly_candles(
                datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
                12,
                start_price=100,
                step=2,
            )
        }
    )
    runner = ReplayRunner(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=2, lookback_candles=3),
        data_provider=provider,
        repository=JsonFileRepository(tmp_path),
    )

    try:
        runner.run_range(
            start=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
            end=datetime(2026, 4, 21, 4, 0, tzinfo=UTC),
        )
    except ValueError as exc:
        assert "start" in str(exc)
    else:
        raise AssertionError("expected ValueError for reversed replay range")


def test_replay_runner_rejects_naive_input_datetimes(tmp_path):
    provider = InMemoryMarketDataProvider(
        {
            "BTC-USD": make_hourly_candles(
                datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
                12,
                start_price=100,
                step=2,
            )
        }
    )
    runner = ReplayRunner(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=2, lookback_candles=3),
        data_provider=provider,
        repository=JsonFileRepository(tmp_path),
    )

    try:
        runner.run_range(
            start=datetime(2026, 4, 21, 4, 0),
            end=datetime(2026, 4, 21, 8, 0),
        )
    except ValueError as exc:
        assert "timezone-aware" in str(exc)
    else:
        raise AssertionError("expected ValueError for naive replay datetimes")


def test_replay_runner_stores_exact_expected_hourly_anchors(tmp_path):
    provider = InMemoryMarketDataProvider(
        {
            "BTC-USD": make_hourly_candles(
                datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
                12,
                start_price=100,
                step=2,
            )
        }
    )
    repository = JsonFileRepository(tmp_path)
    runner = ReplayRunner(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=2, lookback_candles=3),
        data_provider=provider,
        repository=repository,
    )

    result = runner.run_range(
        start=datetime(2026, 4, 21, 4, 0, tzinfo=UTC),
        end=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
    )

    assert [forecast.anchor_time for forecast in repository.load_forecasts()] == [
        datetime(2026, 4, 21, 4, 0, tzinfo=UTC),
        datetime(2026, 4, 21, 5, 0, tzinfo=UTC),
        datetime(2026, 4, 21, 6, 0, tzinfo=UTC),
        datetime(2026, 4, 21, 7, 0, tzinfo=UTC),
        datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
    ]
    assert result.first_cycle_at == datetime(2026, 4, 21, 4, 0, tzinfo=UTC)
    assert result.last_cycle_at == datetime(2026, 4, 21, 8, 0, tzinfo=UTC)
