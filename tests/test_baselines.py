from datetime import UTC, datetime, timedelta

from forecast_loop.baselines import build_baseline_evaluation, build_baseline_suite
from forecast_loop.models import Forecast, ForecastScore


def _forecast(index: int, actual: str, hit: bool) -> Forecast:
    anchor = datetime(2026, 4, 1, tzinfo=UTC) + timedelta(days=index)
    predicted = actual if hit else ("trend_down" if actual == "trend_up" else "trend_up")
    return Forecast(
        forecast_id=f"forecast:{index}",
        symbol="BTC-USD",
        created_at=anchor,
        anchor_time=anchor,
        target_window_start=anchor,
        target_window_end=anchor + timedelta(hours=24),
        candle_interval_minutes=60,
        expected_candle_count=24,
        status="resolved",
        status_reason="scored",
        predicted_regime=predicted,
        confidence=0.7,
        provider_data_through=anchor,
        observed_candle_count=24,
    )


def _score(index: int, forecast: Forecast, actual: str, hit: bool) -> ForecastScore:
    return ForecastScore(
        score_id=f"score:{index}",
        forecast_id=forecast.forecast_id,
        scored_at=forecast.target_window_end,
        predicted_regime=forecast.predicted_regime or "unknown",
        actual_regime=actual,
        score=1.0 if hit else 0.0,
        target_window_start=forecast.target_window_start,
        target_window_end=forecast.target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=24,
        observed_candle_count=24,
        provider_data_through=forecast.target_window_end,
        scoring_basis="test",
    )


def _forecast_scores(actuals: list[str], hits: list[bool]) -> tuple[list[Forecast], list[ForecastScore]]:
    forecasts = []
    scores = []
    for index, (actual, hit) in enumerate(zip(actuals, hits, strict=True)):
        forecast = _forecast(index, actual, hit)
        forecasts.append(forecast)
        scores.append(_score(index, forecast, actual, hit))
    return forecasts, scores


def test_baseline_evaluation_records_required_expanded_suite():
    forecasts, scores = _forecast_scores(
        ["trend_up", "trend_up", "trend_down", "trend_up", "trend_down", "trend_down", "trend_up"],
        [True, True, True, False, True, True, False],
    )

    baseline = build_baseline_evaluation(
        symbol="BTC-USD",
        generated_at=datetime(2026, 4, 24, tzinfo=UTC),
        forecasts=forecasts,
        scores=scores,
    )
    suite_names = {result["baseline_name"] for result in baseline.baseline_results}

    assert baseline.baseline_accuracy == baseline.baseline_results[0]["accuracy"]
    assert suite_names == {
        "naive_persistence",
        "no_trade_cash",
        "buy_and_hold",
        "moving_average_trend",
        "momentum_7d",
        "momentum_14d",
        "deterministic_random",
    }


def test_no_trade_cash_baseline_records_no_directional_prediction():
    _, scores = _forecast_scores(["trend_up", "trend_down"], [True, True])

    results = build_baseline_suite(symbol="BTC-USD", scores=scores)
    no_trade = next(result for result in results if result["baseline_name"] == "no_trade_cash")

    assert no_trade["accuracy"] is None
    assert no_trade["evaluated_count"] == 0
    assert no_trade["hit_count"] == 0


def test_deterministic_random_baseline_is_stable():
    _, scores = _forecast_scores(["trend_up", "trend_down", "range_bound"], [True, True, True])

    first = build_baseline_suite(symbol="BTC-USD", scores=scores)
    second = build_baseline_suite(symbol="BTC-USD", scores=scores)

    assert first == second
