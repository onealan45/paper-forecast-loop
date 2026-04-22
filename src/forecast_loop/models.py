from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(slots=True)
class MarketCandle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "MarketCandle":
        return cls(
            timestamp=datetime.fromisoformat(payload["timestamp"]),
            open=payload["open"],
            high=payload["high"],
            low=payload["low"],
            close=payload["close"],
            volume=payload["volume"],
        )


@dataclass(slots=True)
class Forecast:
    forecast_id: str
    symbol: str
    created_at: datetime
    horizon_end: datetime
    status: str
    predicted_regime: str
    confidence: float

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        payload["horizon_end"] = self.horizon_end.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "Forecast":
        return cls(
            forecast_id=payload["forecast_id"],
            symbol=payload["symbol"],
            created_at=datetime.fromisoformat(payload["created_at"]),
            horizon_end=datetime.fromisoformat(payload["horizon_end"]),
            status=payload["status"],
            predicted_regime=payload["predicted_regime"],
            confidence=payload["confidence"],
        )


@dataclass(slots=True)
class ForecastScore:
    forecast_id: str
    scored_at: datetime
    actual_regime: str
    score: float

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["scored_at"] = self.scored_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "ForecastScore":
        return cls(
            forecast_id=payload["forecast_id"],
            scored_at=datetime.fromisoformat(payload["scored_at"]),
            actual_regime=payload["actual_regime"],
            score=payload["score"],
        )


@dataclass(slots=True)
class Review:
    review_id: str
    created_at: datetime
    average_score: float
    summary: str

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "Review":
        return cls(
            review_id=payload["review_id"],
            created_at=datetime.fromisoformat(payload["created_at"]),
            average_score=payload["average_score"],
            summary=payload["summary"],
        )


@dataclass(slots=True)
class Proposal:
    proposal_id: str
    created_at: datetime
    proposal_type: str
    changes: dict[str, float | bool]
    rationale: str

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "Proposal":
        return cls(
            proposal_id=payload["proposal_id"],
            created_at=datetime.fromisoformat(payload["created_at"]),
            proposal_type=payload["proposal_type"],
            changes=payload["changes"],
            rationale=payload["rationale"],
        )


@dataclass(slots=True)
class CycleResult:
    new_forecast: Forecast | None
    score: object | None = None
    review: Review | None = None
    proposal: Proposal | None = None
