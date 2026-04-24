from __future__ import annotations

from datetime import datetime
from hashlib import sha1

from forecast_loop.models import BaselineEvaluation, Forecast, ForecastScore


REGIME_UNIVERSE = ("trend_up", "trend_down", "range_bound", "volatile_bull", "volatile_bear")
BULLISH_REGIMES = {"trend_up", "volatile_bull"}
BEARISH_REGIMES = {"trend_down", "volatile_bear"}


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
    baseline_results = build_baseline_suite(symbol=symbol, scores=scoped_scores)
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
            f"over {sample_size} scored forecasts; expanded suite recorded for research audit"
        ),
        baseline_results=baseline_results,
    )


def build_baseline_suite(*, symbol: str, scores: list[ForecastScore]) -> list[dict[str, object]]:
    scoped_scores = sorted(scores, key=lambda item: item.scored_at)
    actuals = [score.actual_regime for score in scoped_scores]
    return [
        _evaluate_baseline(
            name="naive_persistence",
            scores=scoped_scores,
            predictions=[None, *actuals[:-1]] if actuals else [],
            decision_basis="predict the next actual regime equals the previous actual regime",
        ),
        _evaluate_baseline(
            name="no_trade_cash",
            scores=scoped_scores,
            predictions=[None for _ in scoped_scores],
            decision_basis="cash/no-trade baseline records zero directional exposure",
        ),
        _evaluate_baseline(
            name="buy_and_hold",
            scores=scoped_scores,
            predictions=["trend_up" for _ in scoped_scores],
            decision_basis="always hold long exposure; represented as trend_up regime prediction",
        ),
        _evaluate_baseline(
            name="moving_average_trend",
            scores=scoped_scores,
            predictions=_rolling_direction_predictions(actuals, window=3),
            decision_basis="predict direction from the prior 3 scored actual regimes",
        ),
        _evaluate_baseline(
            name="momentum_7d",
            scores=scoped_scores,
            predictions=_rolling_direction_predictions(actuals, window=7),
            decision_basis="predict direction from the prior 7 scored actual regimes",
        ),
        _evaluate_baseline(
            name="momentum_14d",
            scores=scoped_scores,
            predictions=_rolling_direction_predictions(actuals, window=14),
            decision_basis="predict direction from the prior 14 scored actual regimes",
        ),
        _evaluate_baseline(
            name="deterministic_random",
            scores=scoped_scores,
            predictions=[_deterministic_random_regime(symbol, score) for score in scoped_scores],
            decision_basis="deterministic random regime baseline using stable score identifiers",
        ),
    ]


def _evaluate_baseline(
    *,
    name: str,
    scores: list[ForecastScore],
    predictions: list[str | None],
    decision_basis: str,
) -> dict[str, object]:
    evaluated = [
        (prediction, score)
        for prediction, score in zip(predictions, scores, strict=True)
        if prediction is not None
    ]
    hit_count = sum(1 for prediction, score in evaluated if prediction == score.actual_regime)
    evaluated_count = len(evaluated)
    accuracy = hit_count / evaluated_count if evaluated_count else None
    return {
        "baseline_name": name,
        "accuracy": accuracy,
        "evaluated_count": evaluated_count,
        "hit_count": hit_count,
        "sample_size": len(scores),
        "decision_basis": decision_basis,
    }


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


def _rolling_direction_predictions(actuals: list[str], *, window: int) -> list[str | None]:
    predictions: list[str | None] = []
    for index in range(len(actuals)):
        history = actuals[max(0, index - window) : index]
        predictions.append(_directional_regime(history) if history else None)
    return predictions


def _directional_regime(actuals: list[str]) -> str:
    bullish_count = sum(1 for actual in actuals if actual in BULLISH_REGIMES)
    bearish_count = sum(1 for actual in actuals if actual in BEARISH_REGIMES)
    return "trend_up" if bullish_count >= bearish_count else "trend_down"


def _deterministic_random_regime(symbol: str, score: ForecastScore) -> str:
    digest = sha1(f"{symbol}:{score.forecast_id}:{score.score_id}:deterministic-random".encode("utf-8")).hexdigest()
    return REGIME_UNIVERSE[int(digest[:8], 16) % len(REGIME_UNIVERSE)]


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
