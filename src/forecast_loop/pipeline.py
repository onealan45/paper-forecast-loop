from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha1

from forecast_loop.config import LoopConfig
from forecast_loop.models import CycleResult, Forecast, ForecastScore, MarketCandle, Proposal, Review


@dataclass(slots=True)
class CoverageCheck:
    candles: list[MarketCandle]
    provider_data_through: datetime | None
    observed_candle_count: int
    coverage_complete: bool
    reason: str


class ForecastingLoop:
    def __init__(self, config: LoopConfig, data_provider, repository) -> None:
        self.config = config
        self.data_provider = data_provider
        self.repository = repository

    def run_cycle(self, now: datetime) -> CycleResult:
        forecasts = self.repository.load_forecasts()
        scores = self._score_resolvable_forecasts(forecasts, now)
        review = self._generate_review(now, scores)
        proposal = self._generate_proposal(now, review)
        new_forecast = self._create_or_get_forecast(forecasts, now)
        self.repository.replace_forecasts(forecasts)
        return CycleResult(new_forecast=new_forecast, scores=scores, review=review, proposal=proposal)

    def _create_or_get_forecast(self, forecasts: list[Forecast], now: datetime) -> Forecast | None:
        anchor_time = self.data_provider.get_latest_candle_boundary(self.config.symbol, end_time=now)
        if anchor_time is None:
            return None

        target_window_start = anchor_time
        target_window_end = anchor_time + timedelta(hours=self.config.horizon_hours)
        forecast_id = self._stable_id(
            "forecast",
            self.config.symbol,
            target_window_start.isoformat(),
            target_window_end.isoformat(),
        )
        existing_forecast = next((item for item in forecasts if item.forecast_id == forecast_id), None)
        if existing_forecast is not None:
            return existing_forecast

        lookback_candles = self.data_provider.get_recent_candles(
            self.config.symbol,
            lookback_candles=self.config.lookback_candles,
            end_time=anchor_time,
        )
        predicted_regime = self._classify_regime(lookback_candles)
        if predicted_regime is None:
            return None

        forecast = Forecast(
            forecast_id=forecast_id,
            symbol=self.config.symbol,
            created_at=now,
            anchor_time=anchor_time,
            target_window_start=target_window_start,
            target_window_end=target_window_end,
            candle_interval_minutes=self.data_provider.candle_interval_minutes,
            expected_candle_count=self._expected_candle_count(target_window_start, target_window_end),
            status="pending",
            status_reason="awaiting_horizon_end",
            predicted_regime=predicted_regime,
            confidence=0.55,
            provider_data_through=anchor_time,
            observed_candle_count=len(lookback_candles),
        )
        forecasts.append(forecast)
        return forecast

    def _score_resolvable_forecasts(self, forecasts: list[Forecast], now: datetime) -> list[ForecastScore]:
        scores: list[ForecastScore] = []
        for forecast in forecasts:
            score = self._score_forecast_if_ready(forecast, now)
            if score is None:
                continue
            self.repository.save_score(score)
            scores.append(score)
        return scores

    def _score_forecast_if_ready(self, forecast: Forecast, now: datetime) -> ForecastScore | None:
        if forecast.status in {"resolved", "unscorable"}:
            return None

        provider_data_through = self.data_provider.get_latest_candle_boundary(forecast.symbol, end_time=now)
        forecast.provider_data_through = provider_data_through
        forecast.observed_candle_count = self._observed_candle_count(forecast, provider_data_through)

        if now < forecast.target_window_end:
            forecast.status = "pending"
            forecast.status_reason = "awaiting_horizon_end"
            return None

        if provider_data_through is None or provider_data_through < forecast.target_window_end:
            forecast.status = "waiting_for_data"
            forecast.status_reason = "awaiting_provider_coverage"
            return None

        coverage = self._validate_coverage(forecast, provider_data_through)
        forecast.provider_data_through = coverage.provider_data_through
        forecast.observed_candle_count = coverage.observed_candle_count
        if not coverage.coverage_complete:
            forecast.status = "unscorable"
            forecast.status_reason = coverage.reason
            return None

        if self.repository.has_score_for_forecast(forecast.forecast_id):
            forecast.status = "resolved"
            forecast.status_reason = "score_already_recorded"
            return None

        actual_regime = self._classify_regime(coverage.candles)
        if actual_regime is None:
            forecast.status = "unscorable"
            forecast.status_reason = "insufficient_realized_candles"
            return None

        score = ForecastScore(
            score_id=self._stable_id("score", forecast.forecast_id),
            forecast_id=forecast.forecast_id,
            scored_at=now,
            predicted_regime=forecast.predicted_regime or "unknown",
            actual_regime=actual_regime,
            score=1.0 if actual_regime == forecast.predicted_regime else 0.0,
            target_window_start=forecast.target_window_start,
            target_window_end=forecast.target_window_end,
            candle_interval_minutes=forecast.candle_interval_minutes,
            expected_candle_count=forecast.expected_candle_count,
            observed_candle_count=coverage.observed_candle_count,
            provider_data_through=coverage.provider_data_through or forecast.target_window_end,
            scoring_basis="regime_direction_over_fully_covered_hourly_window",
        )
        forecast.status = "resolved"
        forecast.status_reason = "scored"
        return score

    def _validate_coverage(self, forecast: Forecast, provider_data_through: datetime) -> CoverageCheck:
        candles = self.data_provider.get_candles_between(
            forecast.symbol,
            forecast.target_window_start,
            forecast.target_window_end,
        )
        observed_boundaries = [candle.timestamp for candle in candles]
        expected_boundaries = self._expected_boundaries(forecast.target_window_start, forecast.target_window_end)
        missing_boundaries = [boundary for boundary in expected_boundaries if boundary not in set(observed_boundaries)]

        if not candles:
            return CoverageCheck(
                candles=[],
                provider_data_through=provider_data_through,
                observed_candle_count=0,
                coverage_complete=False,
                reason="empty_realized_window",
            )

        if missing_boundaries:
            return CoverageCheck(
                candles=candles,
                provider_data_through=provider_data_through,
                observed_candle_count=len(candles),
                coverage_complete=False,
                reason="missing_expected_candles",
            )

        return CoverageCheck(
            candles=candles,
            provider_data_through=provider_data_through,
            observed_candle_count=len(candles),
            coverage_complete=True,
            reason="complete_coverage",
        )

    def _generate_review(self, now: datetime, new_scores: list[ForecastScore]) -> Review | None:
        if not new_scores:
            return None

        recent_scores = self.repository.load_scores()[-self.config.review_window_size :]
        if not recent_scores:
            return None

        score_ids = [score.score_id for score in recent_scores]
        review_id = self._stable_id("review", *score_ids)
        existing = next((item for item in self.repository.load_reviews() if item.review_id == review_id), None)
        if existing is not None:
            return existing

        average_score = sum(score.score for score in recent_scores) / len(recent_scores)
        proposal_recommended = average_score < self.config.proposal_threshold
        review = Review(
            review_id=review_id,
            created_at=now,
            score_ids=score_ids,
            forecast_ids=[score.forecast_id for score in recent_scores],
            average_score=average_score,
            threshold_used=self.config.proposal_threshold,
            decision_basis=f"average of last {len(recent_scores)} valid scores",
            summary=(
                "Forecast accuracy below threshold; generate defensive paper-only adjustments."
                if proposal_recommended
                else "Forecast accuracy acceptable; keep current paper-only settings."
            ),
            proposal_recommended=proposal_recommended,
            proposal_reason=(
                "average_score_below_threshold"
                if proposal_recommended
                else "average_score_at_or_above_threshold"
            ),
        )
        self.repository.save_review(review)
        return review

    def _generate_proposal(self, now: datetime, review: Review | None) -> Proposal | None:
        if review is None or not review.proposal_recommended:
            return None

        proposal_id = self._stable_id("proposal", review.review_id)
        existing = next((item for item in self.repository.load_proposals() if item.proposal_id == proposal_id), None)
        if existing is not None:
            return existing

        proposal = Proposal(
            proposal_id=proposal_id,
            created_at=now,
            review_id=review.review_id,
            score_ids=review.score_ids,
            proposal_type="risk_adjustment",
            changes={"max_position_pct": 0.15, "new_entry_enabled": False},
            threshold_used=review.threshold_used,
            decision_basis=review.decision_basis,
            rationale=(
                f"Generated because {review.proposal_reason} "
                f"against threshold {review.threshold_used:.2f}."
            ),
        )
        self.repository.save_proposal(proposal)
        return proposal

    def _classify_regime(self, candles: list[MarketCandle]) -> str | None:
        if len(candles) < 2:
            return None

        start_close = candles[0].close
        end_close = candles[-1].close
        move_ratio = (end_close - start_close) / start_close
        if move_ratio <= -0.1:
            return "volatile_bear"
        if move_ratio >= 0.1:
            return "volatile_bull"
        if move_ratio >= 0:
            return "trend_up"
        return "trend_down"

    def _observed_candle_count(self, forecast: Forecast, provider_data_through: datetime | None) -> int:
        if provider_data_through is None:
            return 0
        if provider_data_through < forecast.target_window_start:
            return 0
        effective_end = min(provider_data_through, forecast.target_window_end)
        return len(
            self.data_provider.get_candles_between(
                forecast.symbol,
                forecast.target_window_start,
                effective_end,
            )
        )

    def _expected_candle_count(self, start: datetime, end: datetime) -> int:
        interval = timedelta(minutes=self.data_provider.candle_interval_minutes)
        return int((end - start) / interval) + 1

    def _expected_boundaries(self, start: datetime, end: datetime) -> list[datetime]:
        interval = timedelta(minutes=self.data_provider.candle_interval_minutes)
        boundaries = []
        current = start
        while current <= end:
            boundaries.append(current)
            current += interval
        return boundaries

    def _stable_id(self, prefix: str, *parts: str) -> str:
        digest = sha1("||".join(parts).encode("utf-8")).hexdigest()[:12]
        return f"{prefix}:{digest}"
