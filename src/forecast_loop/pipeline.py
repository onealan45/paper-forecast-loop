from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from forecast_loop.config import LoopConfig
from forecast_loop.models import CycleResult, Forecast, ForecastScore, Proposal, Review


class ForecastingLoop:
    def __init__(self, config: LoopConfig, data_provider, repository) -> None:
        self.config = config
        self.data_provider = data_provider
        self.repository = repository

    def run_cycle(self, now: datetime) -> CycleResult:
        score = None
        review = None
        proposal = None

        forecasts = self.repository.load_forecasts()
        for forecast in forecasts:
            if forecast.status != "pending" or forecast.horizon_end > now:
                continue

            realized_candles = self.data_provider.get_candles_between(
                forecast.symbol,
                forecast.created_at,
                forecast.horizon_end,
            )
            actual_regime = self._classify_regime(realized_candles)
            score = ForecastScore(
                forecast_id=forecast.forecast_id,
                scored_at=now,
                actual_regime=actual_regime,
                score=1.0 if actual_regime == forecast.predicted_regime else 0.0,
            )
            forecast.status = "resolved"
            self.repository.save_score(score)

        self.repository.replace_forecasts(forecasts)

        if score is not None:
            recent_scores = self.repository.load_scores()[-5:]
            average_score = sum(item.score for item in recent_scores) / len(recent_scores)
            summary = (
                "Forecast accuracy below threshold; generate defensive paper-only adjustments."
                if average_score < 0.6
                else "Forecast accuracy acceptable; keep current paper-only settings."
            )
            review = Review(
                review_id=str(uuid4()),
                created_at=now,
                average_score=average_score,
                summary=summary,
            )
            self.repository.save_review(review)
            if average_score < 0.6:
                proposal = Proposal(
                    proposal_id=str(uuid4()),
                    created_at=now,
                    proposal_type="risk_adjustment",
                    changes={"max_position_pct": 0.15, "new_entry_enabled": False},
                    rationale="Recent paper-only forecast scores are below threshold.",
                )
                self.repository.save_proposal(proposal)

        candles = self.data_provider.get_recent_candles(
            self.config.symbol,
            self.config.lookback_candles,
            end_time=now,
        )
        predicted_regime = self._classify_regime(candles)
        forecast = Forecast(
            forecast_id=str(uuid4()),
            symbol=self.config.symbol,
            created_at=now,
            horizon_end=now + timedelta(hours=self.config.horizon_hours),
            status="pending",
            predicted_regime=predicted_regime,
            confidence=0.55,
        )
        self.repository.save_forecast(forecast)
        return CycleResult(new_forecast=forecast, score=score, review=review, proposal=proposal)

    def _classify_regime(self, candles) -> str:
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
