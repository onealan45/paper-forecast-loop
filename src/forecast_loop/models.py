from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
import json
from hashlib import sha1


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _deserialize_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def _evaluation_summary_identity(
    forecast_ids: list[str],
    scored_forecast_ids: list[str],
    score_ids: list[str],
    review_ids: list[str],
    proposal_ids: list[str],
    replay_window_start: datetime | None,
    replay_window_end: datetime | None,
    anchor_time_start: datetime | None,
    anchor_time_end: datetime | None,
    forecast_count: int,
    resolved_count: int,
    waiting_for_data_count: int,
    unscorable_count: int,
    average_score: float | None,
) -> str:
    payload = {
        "forecast_ids": sorted(forecast_ids),
        "scored_forecast_ids": sorted(scored_forecast_ids),
        "score_ids": sorted(score_ids),
        "review_ids": sorted(review_ids),
        "proposal_ids": sorted(proposal_ids),
        "replay_window_start": _serialize_datetime(replay_window_start),
        "replay_window_end": _serialize_datetime(replay_window_end),
        "anchor_time_start": _serialize_datetime(anchor_time_start),
        "anchor_time_end": _serialize_datetime(anchor_time_end),
        "forecast_count": forecast_count,
        "resolved_count": resolved_count,
        "waiting_for_data_count": waiting_for_data_count,
        "unscorable_count": unscorable_count,
        "average_score": average_score,
    }
    digest = sha1(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
    return f"evaluation-summary:{digest}"


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
    anchor_time: datetime
    target_window_start: datetime
    target_window_end: datetime
    candle_interval_minutes: int
    expected_candle_count: int
    status: str
    status_reason: str
    predicted_regime: str | None
    confidence: float | None
    provider_data_through: datetime | None = None
    observed_candle_count: int = 0

    def to_dict(self) -> dict:
        payload = asdict(self)
        for key in (
            "created_at",
            "anchor_time",
            "target_window_start",
            "target_window_end",
            "provider_data_through",
        ):
            payload[key] = _serialize_datetime(payload[key])
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "Forecast":
        target_window_start = _deserialize_datetime(payload.get("target_window_start")) or datetime.fromisoformat(
            payload.get("created_at")
        )
        target_window_end = _deserialize_datetime(payload.get("target_window_end")) or datetime.fromisoformat(
            payload.get("horizon_end")
        )
        candle_interval_minutes = payload.get("candle_interval_minutes", 60)
        expected_candle_count = payload.get("expected_candle_count")
        if expected_candle_count is None:
            interval = timedelta(minutes=candle_interval_minutes)
            expected_candle_count = int((target_window_end - target_window_start) / interval) + 1

        status = payload.get("status", "pending")
        default_reason = {
            "pending": "awaiting_horizon_end",
            "resolved": "scored",
            "waiting_for_data": "awaiting_provider_coverage",
            "unscorable": "legacy_unscorable",
        }.get(status, "legacy_status")

        return cls(
            forecast_id=payload["forecast_id"],
            symbol=payload["symbol"],
            created_at=_deserialize_datetime(payload.get("created_at")) or target_window_start,
            anchor_time=_deserialize_datetime(payload.get("anchor_time")) or target_window_start,
            target_window_start=target_window_start,
            target_window_end=target_window_end,
            candle_interval_minutes=candle_interval_minutes,
            expected_candle_count=expected_candle_count,
            status=status,
            status_reason=payload.get("status_reason", default_reason),
            predicted_regime=payload.get("predicted_regime"),
            confidence=payload.get("confidence"),
            provider_data_through=_deserialize_datetime(payload.get("provider_data_through")),
            observed_candle_count=payload.get("observed_candle_count", 0),
        )


@dataclass(slots=True)
class ForecastScore:
    score_id: str
    forecast_id: str
    scored_at: datetime
    predicted_regime: str
    actual_regime: str
    score: float
    target_window_start: datetime
    target_window_end: datetime
    candle_interval_minutes: int
    expected_candle_count: int
    observed_candle_count: int
    provider_data_through: datetime
    scoring_basis: str

    def to_dict(self) -> dict:
        payload = asdict(self)
        for key in ("scored_at", "target_window_start", "target_window_end", "provider_data_through"):
            payload[key] = _serialize_datetime(payload[key])
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "ForecastScore":
        return cls(
            score_id=payload.get("score_id", f"score:{payload['forecast_id']}"),
            forecast_id=payload["forecast_id"],
            scored_at=_deserialize_datetime(payload.get("scored_at")) or datetime.now(),
            predicted_regime=payload.get("predicted_regime", "unknown"),
            actual_regime=payload["actual_regime"],
            score=payload["score"],
            target_window_start=_deserialize_datetime(payload.get("target_window_start")) or _deserialize_datetime(
                payload.get("scored_at")
            ),
            target_window_end=_deserialize_datetime(payload.get("target_window_end")) or _deserialize_datetime(
                payload.get("scored_at")
            ),
            candle_interval_minutes=payload.get("candle_interval_minutes", 60),
            expected_candle_count=payload.get("expected_candle_count", 0),
            observed_candle_count=payload.get("observed_candle_count", 0),
            provider_data_through=_deserialize_datetime(payload.get("provider_data_through"))
            or _deserialize_datetime(payload.get("scored_at"))
            or datetime.now(),
            scoring_basis=payload.get("scoring_basis", "legacy_regime_classification"),
        )


@dataclass(slots=True)
class Review:
    review_id: str
    created_at: datetime
    score_ids: list[str]
    forecast_ids: list[str]
    average_score: float
    threshold_used: float
    decision_basis: str
    summary: str
    proposal_recommended: bool
    proposal_reason: str

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "Review":
        return cls(
            review_id=payload["review_id"],
            created_at=datetime.fromisoformat(payload["created_at"]),
            score_ids=payload.get("score_ids", []),
            forecast_ids=payload.get("forecast_ids", []),
            average_score=payload["average_score"],
            threshold_used=payload.get("threshold_used", 0.6),
            decision_basis=payload.get("decision_basis", "legacy_review_basis"),
            summary=payload["summary"],
            proposal_recommended=payload.get("proposal_recommended", payload["average_score"] < 0.6),
            proposal_reason=payload.get("proposal_reason", "legacy_review_reason"),
        )


@dataclass(slots=True)
class Proposal:
    proposal_id: str
    created_at: datetime
    review_id: str
    score_ids: list[str]
    proposal_type: str
    changes: dict[str, float | bool]
    threshold_used: float
    decision_basis: str
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
            review_id=payload.get("review_id", "legacy_review"),
            score_ids=payload.get("score_ids", []),
            proposal_type=payload["proposal_type"],
            changes=payload["changes"],
            threshold_used=payload.get("threshold_used", 0.6),
            decision_basis=payload.get("decision_basis", "legacy_proposal_basis"),
            rationale=payload["rationale"],
        )


@dataclass(slots=True)
class EvaluationSummary:
    summary_id: str
    replay_id: str
    generated_at: datetime
    forecast_ids: list[str]
    scored_forecast_ids: list[str]
    replay_window_start: datetime | None
    replay_window_end: datetime | None
    anchor_time_start: datetime | None
    anchor_time_end: datetime | None
    forecast_count: int
    resolved_count: int
    waiting_for_data_count: int
    unscorable_count: int
    average_score: float | None
    score_ids: list[str]
    review_ids: list[str]
    proposal_ids: list[str]

    def to_dict(self) -> dict:
        payload = asdict(self)
        for key in ("generated_at", "replay_window_start", "replay_window_end", "anchor_time_start", "anchor_time_end"):
            payload[key] = _serialize_datetime(payload[key])
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "EvaluationSummary":
        replay_window_start = _deserialize_datetime(payload.get("replay_window_start"))
        replay_window_end = _deserialize_datetime(payload.get("replay_window_end"))
        anchor_time_start = _deserialize_datetime(payload.get("anchor_time_start"))
        anchor_time_end = _deserialize_datetime(payload.get("anchor_time_end"))
        forecast_ids = payload.get("forecast_ids", [])
        scored_forecast_ids = payload.get("scored_forecast_ids", [])
        score_ids = payload.get("score_ids", [])
        review_ids = payload.get("review_ids", [])
        proposal_ids = payload.get("proposal_ids", [])
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
            forecast_count=payload["forecast_count"],
            resolved_count=payload["resolved_count"],
            waiting_for_data_count=payload["waiting_for_data_count"],
            unscorable_count=payload["unscorable_count"],
            average_score=payload.get("average_score"),
        )
        return cls(
            summary_id=summary_id,
            replay_id=payload["replay_id"],
            generated_at=datetime.fromisoformat(payload["generated_at"]),
            forecast_ids=sorted(forecast_ids),
            scored_forecast_ids=sorted(scored_forecast_ids),
            replay_window_start=replay_window_start,
            replay_window_end=replay_window_end,
            anchor_time_start=anchor_time_start,
            anchor_time_end=anchor_time_end,
            forecast_count=payload["forecast_count"],
            resolved_count=payload["resolved_count"],
            waiting_for_data_count=payload["waiting_for_data_count"],
            unscorable_count=payload["unscorable_count"],
            average_score=payload.get("average_score"),
            score_ids=sorted(score_ids),
            review_ids=sorted(review_ids),
            proposal_ids=sorted(proposal_ids),
        )


@dataclass(slots=True)
class CycleResult:
    new_forecast: Forecast | None
    scores: list[ForecastScore] = field(default_factory=list)
    review: Review | None = None
    proposal: Proposal | None = None
