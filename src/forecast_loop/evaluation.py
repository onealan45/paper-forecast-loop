from __future__ import annotations

from datetime import datetime

from forecast_loop.models import EvaluationSummary, Forecast, ForecastScore, Proposal, Review, _evaluation_summary_identity


def build_evaluation_summary(
    replay_id: str,
    generated_at: datetime,
    forecasts: list[Forecast],
    scores: list[ForecastScore],
    reviews: list[Review],
    proposals: list[Proposal],
) -> EvaluationSummary:
    forecast_ids = [forecast.forecast_id for forecast in forecasts]
    scored_forecast_ids = [score.forecast_id for score in scores]
    score_ids = [score.score_id for score in scores]
    review_ids = [review.review_id for review in reviews]
    proposal_ids = [proposal.proposal_id for proposal in proposals]
    resolved_count = sum(1 for forecast in forecasts if forecast.status == "resolved")
    waiting_for_data_count = sum(1 for forecast in forecasts if forecast.status == "waiting_for_data")
    unscorable_count = sum(1 for forecast in forecasts if forecast.status == "unscorable")
    average_score = sum(score.score for score in scores) / len(scores) if scores else None
    replay_window_start = min((forecast.target_window_start for forecast in forecasts), default=None)
    replay_window_end = max((forecast.target_window_end for forecast in forecasts), default=None)
    anchor_time_start = min((forecast.anchor_time for forecast in forecasts), default=None)
    anchor_time_end = max((forecast.anchor_time for forecast in forecasts), default=None)
    summary_id = _evaluation_summary_identity(
        forecast_ids=forecast_ids,
        scored_forecast_ids=scored_forecast_ids,
        score_ids=score_ids,
        review_ids=review_ids,
        proposal_ids=proposal_ids,
        replay_window_start=replay_window_start,
        replay_window_end=replay_window_end,
        anchor_time_start=anchor_time_start,
        anchor_time_end=anchor_time_end,
        forecast_count=len(forecasts),
        resolved_count=resolved_count,
        waiting_for_data_count=waiting_for_data_count,
        unscorable_count=unscorable_count,
        average_score=average_score,
    )

    return EvaluationSummary(
        summary_id=summary_id,
        replay_id=replay_id,
        generated_at=generated_at,
        forecast_ids=sorted(forecast_ids),
        scored_forecast_ids=sorted(scored_forecast_ids),
        replay_window_start=replay_window_start,
        replay_window_end=replay_window_end,
        anchor_time_start=anchor_time_start,
        anchor_time_end=anchor_time_end,
        forecast_count=len(forecasts),
        resolved_count=resolved_count,
        waiting_for_data_count=waiting_for_data_count,
        unscorable_count=unscorable_count,
        average_score=average_score,
        score_ids=sorted(score_ids),
        review_ids=sorted(review_ids),
        proposal_ids=sorted(proposal_ids),
    )
