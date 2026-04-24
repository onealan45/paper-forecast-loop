from __future__ import annotations

from datetime import datetime

from forecast_loop.models import BaselineEvaluation, Forecast, ForecastScore


def build_baseline_evaluation(
    *,
    symbol: str,
    generated_at: datetime,
    forecasts: list[Forecast],
    scores: list[ForecastScore],
    recent_window: int = 5,
) -> BaselineEvaluation:
    forecasts_by_id = {forecast.forecast_id: forecast for forecast in forecasts}
    scoped_scores = [
        score
        for score in scores
        if score.forecast_id in forecasts_by_id and forecasts_by_id[score.forecast_id].symbol == symbol
    ]
    scoped_scores = sorted(scoped_scores, key=lambda item: item.scored_at)
    score_ids = [score.score_id for score in scoped_scores]
    forecast_ids = [score.forecast_id for score in scoped_scores]
    sample_size = len(scoped_scores)
    directional_accuracy = _average([score.score for score in scoped_scores])
    recent_score = _average([score.score for score in scoped_scores[-recent_window:]])
    baseline_accuracy = _naive_persistence_accuracy(scoped_scores)
    model_edge = (
        directional_accuracy - baseline_accuracy
        if directional_accuracy is not None and baseline_accuracy is not None
        else None
    )
    evidence_grade = _evidence_grade(
        sample_size=sample_size,
        directional_accuracy=directional_accuracy,
        baseline_accuracy=baseline_accuracy,
        model_edge=model_edge,
        recent_score=recent_score,
    )
    baseline_id = BaselineEvaluation.build_id(
        symbol=symbol,
        score_ids=score_ids,
        baseline_accuracy=baseline_accuracy,
        directional_accuracy=directional_accuracy,
        recent_score=recent_score,
    )
    return BaselineEvaluation(
        baseline_id=baseline_id,
        created_at=generated_at,
        symbol=symbol,
        sample_size=sample_size,
        directional_accuracy=directional_accuracy,
        baseline_accuracy=baseline_accuracy,
        model_edge=model_edge,
        recent_score=recent_score,
        evidence_grade=evidence_grade,
        forecast_ids=forecast_ids,
        score_ids=score_ids,
        decision_basis=(
            "model directional accuracy compared with naive persistence baseline "
            f"over {sample_size} scored forecasts"
        ),
    )


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _naive_persistence_accuracy(scores: list[ForecastScore]) -> float | None:
    if len(scores) < 2:
        return None
    hits = 0
    total = 0
    previous_actual = scores[0].actual_regime
    for score in scores[1:]:
        if previous_actual == score.actual_regime:
            hits += 1
        total += 1
        previous_actual = score.actual_regime
    return hits / total if total else None


def _evidence_grade(
    *,
    sample_size: int,
    directional_accuracy: float | None,
    baseline_accuracy: float | None,
    model_edge: float | None,
    recent_score: float | None,
) -> str:
    if sample_size < 2 or directional_accuracy is None or baseline_accuracy is None or model_edge is None:
        return "INSUFFICIENT"
    if sample_size >= 20 and model_edge >= 0.10 and (recent_score or 0.0) >= 0.70:
        return "A"
    if sample_size >= 5 and model_edge > 0.05 and (recent_score or 0.0) >= 0.60:
        return "B"
    if sample_size >= 3 and model_edge > 0.0 and (recent_score or 0.0) >= 0.50:
        return "C"
    return "D"
