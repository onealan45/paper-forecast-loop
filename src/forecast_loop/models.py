from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
import json
from hashlib import sha1


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _deserialize_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def _require_aware_datetime(payload: dict, key: str) -> datetime:
    if key not in payload or payload[key] in (None, ""):
        raise ValueError(f"missing required datetime field: {key}")
    value = _deserialize_datetime(payload[key])
    if value is None:
        raise ValueError(f"missing required datetime field: {key}")
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(f"datetime field must include timezone: {key}")
    return value


def _require_string(payload: dict, key: str) -> str:
    if key not in payload or not isinstance(payload[key], str) or not payload[key]:
        raise ValueError(f"missing required string field: {key}")
    return payload[key]


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


def _stable_artifact_id(prefix: str, payload: dict) -> str:
    digest = sha1(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{digest}"


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
class BaselineEvaluation:
    baseline_id: str
    created_at: datetime
    symbol: str
    sample_size: int
    directional_accuracy: float | None
    baseline_accuracy: float | None
    model_edge: float | None
    recent_score: float | None
    evidence_grade: str
    forecast_ids: list[str]
    score_ids: list[str]
    decision_basis: str

    @classmethod
    def build_id(
        cls,
        *,
        symbol: str,
        score_ids: list[str],
        baseline_accuracy: float | None,
        directional_accuracy: float | None,
        recent_score: float | None,
    ) -> str:
        return _stable_artifact_id(
            "baseline",
            {
                "symbol": symbol,
                "score_ids": sorted(score_ids),
                "baseline_accuracy": baseline_accuracy,
                "directional_accuracy": directional_accuracy,
                "recent_score": recent_score,
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "BaselineEvaluation":
        return cls(
            baseline_id=payload["baseline_id"],
            created_at=datetime.fromisoformat(payload["created_at"]),
            symbol=payload["symbol"],
            sample_size=payload["sample_size"],
            directional_accuracy=payload.get("directional_accuracy"),
            baseline_accuracy=payload.get("baseline_accuracy"),
            model_edge=payload.get("model_edge"),
            recent_score=payload.get("recent_score"),
            evidence_grade=payload.get("evidence_grade", "INSUFFICIENT"),
            forecast_ids=payload.get("forecast_ids", []),
            score_ids=payload.get("score_ids", []),
            decision_basis=payload.get("decision_basis", "legacy_baseline_evaluation"),
        )


@dataclass(slots=True)
class PaperPosition:
    symbol: str
    quantity: float
    avg_price: float
    market_price: float
    market_value: float
    unrealized_pnl: float
    position_pct: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "PaperPosition":
        return cls(
            symbol=payload["symbol"],
            quantity=payload.get("quantity", 0.0),
            avg_price=payload.get("avg_price", 0.0),
            market_price=payload.get("market_price", 0.0),
            market_value=payload.get("market_value", 0.0),
            unrealized_pnl=payload.get("unrealized_pnl", 0.0),
            position_pct=payload.get("position_pct", 0.0),
        )


@dataclass(slots=True)
class PaperPortfolioSnapshot:
    snapshot_id: str
    created_at: datetime
    equity: float
    cash: float
    gross_exposure_pct: float
    net_exposure_pct: float
    max_drawdown_pct: float | None
    positions: list[PaperPosition]
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    nav: float | None = None

    @classmethod
    def build_id(
        cls,
        *,
        created_at: datetime,
        equity: float,
        cash: float,
        positions: list[PaperPosition],
    ) -> str:
        return _stable_artifact_id(
            "portfolio",
            {
                "created_at": created_at.isoformat(),
                "equity": round(equity, 8),
                "cash": round(cash, 8),
                "positions": [position.to_dict() for position in positions],
            },
        )

    @classmethod
    def empty(cls, *, created_at: datetime, equity: float = 10_000.0) -> "PaperPortfolioSnapshot":
        snapshot_id = cls.build_id(created_at=created_at, equity=equity, cash=equity, positions=[])
        return cls(
            snapshot_id=snapshot_id,
            created_at=created_at,
            equity=equity,
            cash=equity,
            gross_exposure_pct=0.0,
            net_exposure_pct=0.0,
            max_drawdown_pct=None,
            positions=[],
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            nav=equity,
        )

    def position_pct_for(self, symbol: str) -> float:
        for position in self.positions:
            if position.symbol == symbol:
                return position.position_pct
        return 0.0

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        payload["positions"] = [position.to_dict() for position in self.positions]
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "PaperPortfolioSnapshot":
        return cls(
            snapshot_id=payload["snapshot_id"],
            created_at=datetime.fromisoformat(payload["created_at"]),
            equity=payload.get("equity", 0.0),
            cash=payload.get("cash", 0.0),
            gross_exposure_pct=payload.get("gross_exposure_pct", 0.0),
            net_exposure_pct=payload.get("net_exposure_pct", 0.0),
            max_drawdown_pct=payload.get("max_drawdown_pct"),
            positions=[PaperPosition.from_dict(item) for item in payload.get("positions", [])],
            realized_pnl=payload.get("realized_pnl", 0.0),
            unrealized_pnl=payload.get("unrealized_pnl", 0.0),
            nav=payload.get("nav", payload.get("equity")),
        )


class PaperOrderStatus(StrEnum):
    CREATED = "CREATED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PaperOrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class PaperOrderType(StrEnum):
    TARGET_PERCENT = "TARGET_PERCENT"


@dataclass(slots=True)
class PaperOrder:
    order_id: str
    created_at: datetime
    decision_id: str
    symbol: str
    side: str
    order_type: str
    status: str
    target_position_pct: float | None
    current_position_pct: float | None
    max_position_pct: float
    rationale: str

    @classmethod
    def build_id(
        cls,
        *,
        decision_id: str,
        symbol: str,
        side: str,
        target_position_pct: float | None,
        order_type: str,
    ) -> str:
        return _stable_artifact_id(
            "paper-order",
            {
                "decision_id": decision_id,
                "symbol": symbol,
                "side": side,
                "target_position_pct": target_position_pct,
                "order_type": order_type,
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "PaperOrder":
        return cls(
            order_id=payload["order_id"],
            created_at=datetime.fromisoformat(payload["created_at"]),
            decision_id=payload["decision_id"],
            symbol=payload["symbol"],
            side=payload["side"],
            order_type=payload.get("order_type", PaperOrderType.TARGET_PERCENT.value),
            status=payload.get("status", PaperOrderStatus.CREATED.value),
            target_position_pct=payload.get("target_position_pct"),
            current_position_pct=payload.get("current_position_pct"),
            max_position_pct=payload.get("max_position_pct", 0.0),
            rationale=payload.get("rationale", "legacy_paper_order"),
        )


@dataclass(slots=True)
class PaperFill:
    fill_id: str
    order_id: str
    decision_id: str
    symbol: str
    side: str
    filled_at: datetime
    quantity: float
    market_price: float
    fill_price: float
    gross_value: float
    fee: float
    fee_bps: float
    slippage_bps: float
    net_cash_change: float

    @classmethod
    def build_id(
        cls,
        *,
        order_id: str,
        symbol: str,
        side: str,
        quantity: float,
        fill_price: float,
    ) -> str:
        return _stable_artifact_id(
            "paper-fill",
            {
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "quantity": round(quantity, 12),
                "fill_price": round(fill_price, 12),
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["filled_at"] = self.filled_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "PaperFill":
        return cls(
            fill_id=payload["fill_id"],
            order_id=payload["order_id"],
            decision_id=payload["decision_id"],
            symbol=payload["symbol"],
            side=payload["side"],
            filled_at=datetime.fromisoformat(payload["filled_at"]),
            quantity=payload.get("quantity", 0.0),
            market_price=payload.get("market_price", 0.0),
            fill_price=payload.get("fill_price", 0.0),
            gross_value=payload.get("gross_value", 0.0),
            fee=payload.get("fee", 0.0),
            fee_bps=payload.get("fee_bps", 0.0),
            slippage_bps=payload.get("slippage_bps", 0.0),
            net_cash_change=payload.get("net_cash_change", 0.0),
        )


@dataclass(slots=True)
class EquityCurvePoint:
    point_id: str
    created_at: datetime
    equity: float
    cash: float
    realized_pnl: float
    unrealized_pnl: float
    gross_exposure_pct: float
    net_exposure_pct: float
    max_drawdown_pct: float | None

    @classmethod
    def build_id(cls, *, created_at: datetime, equity: float, cash: float) -> str:
        return _stable_artifact_id(
            "equity",
            {
                "created_at": created_at.isoformat(),
                "equity": round(equity, 8),
                "cash": round(cash, 8),
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "EquityCurvePoint":
        return cls(
            point_id=payload["point_id"],
            created_at=datetime.fromisoformat(payload["created_at"]),
            equity=payload.get("equity", 0.0),
            cash=payload.get("cash", 0.0),
            realized_pnl=payload.get("realized_pnl", 0.0),
            unrealized_pnl=payload.get("unrealized_pnl", 0.0),
            gross_exposure_pct=payload.get("gross_exposure_pct", 0.0),
            net_exposure_pct=payload.get("net_exposure_pct", 0.0),
            max_drawdown_pct=payload.get("max_drawdown_pct"),
        )


@dataclass(slots=True)
class RiskSnapshot:
    risk_id: str
    created_at: datetime
    symbol: str
    status: str
    severity: str
    current_drawdown_pct: float
    max_drawdown_pct: float
    gross_exposure_pct: float
    net_exposure_pct: float
    position_pct: float
    max_position_pct: float
    max_gross_exposure_pct: float
    reduce_risk_drawdown_pct: float
    stop_new_entries_drawdown_pct: float
    findings: list[str]
    recommended_action: str
    decision_basis: str

    @classmethod
    def build_id(
        cls,
        *,
        created_at: datetime,
        symbol: str,
        status: str,
        current_drawdown_pct: float,
        gross_exposure_pct: float,
        findings: list[str],
    ) -> str:
        return _stable_artifact_id(
            "risk",
            {
                "created_at": created_at.isoformat(),
                "symbol": symbol,
                "status": status,
                "current_drawdown_pct": round(current_drawdown_pct, 8),
                "gross_exposure_pct": round(gross_exposure_pct, 8),
                "findings": sorted(findings),
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "RiskSnapshot":
        return cls(
            risk_id=payload["risk_id"],
            created_at=datetime.fromisoformat(payload["created_at"]),
            symbol=payload["symbol"],
            status=payload.get("status", "OK"),
            severity=payload.get("severity", "none"),
            current_drawdown_pct=payload.get("current_drawdown_pct", 0.0),
            max_drawdown_pct=payload.get("max_drawdown_pct", 0.0),
            gross_exposure_pct=payload.get("gross_exposure_pct", 0.0),
            net_exposure_pct=payload.get("net_exposure_pct", 0.0),
            position_pct=payload.get("position_pct", 0.0),
            max_position_pct=payload.get("max_position_pct", 0.15),
            max_gross_exposure_pct=payload.get("max_gross_exposure_pct", 0.20),
            reduce_risk_drawdown_pct=payload.get("reduce_risk_drawdown_pct", 0.05),
            stop_new_entries_drawdown_pct=payload.get("stop_new_entries_drawdown_pct", 0.10),
            findings=payload.get("findings", []),
            recommended_action=payload.get("recommended_action", payload.get("status", "OK")),
            decision_basis=payload.get("decision_basis", "legacy_risk_snapshot"),
        )


@dataclass(slots=True)
class ProviderRun:
    provider_run_id: str
    created_at: datetime
    provider: str
    symbol: str
    operation: str
    status: str
    started_at: datetime
    completed_at: datetime
    candle_count: int
    data_start: datetime | None
    data_end: datetime | None
    schema_version: str
    error_type: str | None = None
    error_message: str | None = None

    @classmethod
    def build_id(
        cls,
        *,
        provider: str,
        symbol: str,
        operation: str,
        started_at: datetime,
        completed_at: datetime,
        status: str,
    ) -> str:
        return _stable_artifact_id(
            "provider-run",
            {
                "provider": provider,
                "symbol": symbol,
                "operation": operation,
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "status": status,
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        for key in ("created_at", "started_at", "completed_at", "data_start", "data_end"):
            payload[key] = _serialize_datetime(payload[key])
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "ProviderRun":
        status = _require_string(payload, "status")
        if status not in {"success", "empty", "error"}:
            raise ValueError(f"unsupported provider run status: {status}")
        if "candle_count" not in payload:
            raise ValueError("missing required integer field: candle_count")
        return cls(
            provider_run_id=_require_string(payload, "provider_run_id"),
            created_at=_require_aware_datetime(payload, "created_at"),
            provider=_require_string(payload, "provider"),
            symbol=_require_string(payload, "symbol"),
            operation=_require_string(payload, "operation"),
            status=status,
            started_at=_require_aware_datetime(payload, "started_at"),
            completed_at=_require_aware_datetime(payload, "completed_at"),
            candle_count=int(payload["candle_count"]),
            data_start=_deserialize_datetime(payload.get("data_start")),
            data_end=_deserialize_datetime(payload.get("data_end")),
            schema_version=_require_string(payload, "schema_version"),
            error_type=payload.get("error_type"),
            error_message=payload.get("error_message"),
        )


@dataclass(slots=True)
class StrategyDecision:
    decision_id: str
    created_at: datetime
    symbol: str
    horizon_hours: int
    action: str
    confidence: float | None
    evidence_grade: str
    risk_level: str
    tradeable: bool
    blocked_reason: str | None
    recommended_position_pct: float | None
    current_position_pct: float | None
    max_position_pct: float
    invalidation_conditions: list[str]
    reason_summary: str
    forecast_ids: list[str]
    score_ids: list[str]
    review_ids: list[str]
    baseline_ids: list[str]
    decision_basis: str

    @classmethod
    def build_fail_closed(
        cls,
        *,
        symbol: str,
        horizon_hours: int,
        created_at: datetime,
        blocked_reason: str,
        reason_summary: str,
        repair_request_id: str | None,
    ) -> "StrategyDecision":
        decision_basis = (
            f"action=STOP_NEW_ENTRIES; evidence_grade=INSUFFICIENT; "
            f"blocked_reason={blocked_reason}; repair_request_id={repair_request_id or 'none'}"
        )
        decision_id = cls.build_id(
            symbol=symbol,
            horizon_hours=horizon_hours,
            action="STOP_NEW_ENTRIES",
            forecast_ids=[],
            score_ids=[],
            review_ids=[],
            baseline_ids=[],
            decision_basis=decision_basis,
        )
        return cls(
            decision_id=decision_id,
            created_at=created_at,
            symbol=symbol,
            horizon_hours=horizon_hours,
            action="STOP_NEW_ENTRIES",
            confidence=None,
            evidence_grade="INSUFFICIENT",
            risk_level="HIGH",
            tradeable=False,
            blocked_reason=blocked_reason,
            recommended_position_pct=0.0,
            current_position_pct=None,
            max_position_pct=0.15,
            invalidation_conditions=[
                "health-check repair request 已處理完成。",
                "storage artifacts 可正常讀取且 health-check 回到 healthy。",
                "重新產生最新 forecast 與 strategy decision。",
            ],
            reason_summary=reason_summary,
            forecast_ids=[],
            score_ids=[],
            review_ids=[],
            baseline_ids=[],
            decision_basis=decision_basis,
        )

    @classmethod
    def build_id(
        cls,
        *,
        symbol: str,
        horizon_hours: int,
        action: str,
        forecast_ids: list[str],
        score_ids: list[str],
        review_ids: list[str],
        baseline_ids: list[str],
        decision_basis: str,
    ) -> str:
        return _stable_artifact_id(
            "decision",
            {
                "symbol": symbol,
                "horizon_hours": horizon_hours,
                "action": action,
                "forecast_ids": sorted(forecast_ids),
                "score_ids": sorted(score_ids),
                "review_ids": sorted(review_ids),
                "baseline_ids": sorted(baseline_ids),
                "decision_basis": decision_basis,
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "StrategyDecision":
        return cls(
            decision_id=payload["decision_id"],
            created_at=datetime.fromisoformat(payload["created_at"]),
            symbol=payload["symbol"],
            horizon_hours=payload.get("horizon_hours", 24),
            action=payload["action"],
            confidence=payload.get("confidence"),
            evidence_grade=payload.get("evidence_grade", "INSUFFICIENT"),
            risk_level=payload.get("risk_level", "UNKNOWN"),
            tradeable=payload.get("tradeable", False),
            blocked_reason=payload.get("blocked_reason"),
            recommended_position_pct=payload.get("recommended_position_pct"),
            current_position_pct=payload.get("current_position_pct"),
            max_position_pct=payload.get("max_position_pct", 0.0),
            invalidation_conditions=payload.get("invalidation_conditions", []),
            reason_summary=payload["reason_summary"],
            forecast_ids=payload.get("forecast_ids", []),
            score_ids=payload.get("score_ids", []),
            review_ids=payload.get("review_ids", []),
            baseline_ids=payload.get("baseline_ids", []),
            decision_basis=payload.get("decision_basis", "legacy_strategy_decision"),
        )


@dataclass(slots=True)
class HealthFinding:
    code: str
    severity: str
    message: str
    artifact_path: str | None = None
    repair_required: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "HealthFinding":
        return cls(
            code=payload["code"],
            severity=payload.get("severity", "warning"),
            message=payload["message"],
            artifact_path=payload.get("artifact_path"),
            repair_required=payload.get("repair_required", False),
        )


@dataclass(slots=True)
class HealthCheckResult:
    check_id: str
    created_at: datetime
    status: str
    severity: str
    repair_required: bool
    repair_request_id: str | None
    findings: list[HealthFinding]

    @classmethod
    def build_id(cls, *, created_at: datetime, findings: list[HealthFinding]) -> str:
        return _stable_artifact_id(
            "health",
            {
                "created_at": created_at.isoformat(),
                "findings": [finding.to_dict() for finding in findings],
            },
        )

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "severity": self.severity,
            "repair_required": self.repair_required,
            "repair_request_id": self.repair_request_id,
            "findings": [finding.to_dict() for finding in self.findings],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "HealthCheckResult":
        return cls(
            check_id=payload["check_id"],
            created_at=datetime.fromisoformat(payload["created_at"]),
            status=payload["status"],
            severity=payload.get("severity", "none"),
            repair_required=payload.get("repair_required", False),
            repair_request_id=payload.get("repair_request_id"),
            findings=[HealthFinding.from_dict(item) for item in payload.get("findings", [])],
        )


@dataclass(slots=True)
class RepairRequest:
    repair_request_id: str
    created_at: datetime
    status: str
    severity: str
    observed_failure: str
    reproduction_command: str
    expected_behavior: str
    affected_artifacts: list[str]
    recommended_tests: list[str]
    safety_boundary: str
    acceptance_criteria: list[str]
    finding_codes: list[str]
    prompt_path: str | None = None

    @classmethod
    def build_id(cls, *, created_at: datetime, finding_codes: list[str], observed_failure: str) -> str:
        return _stable_artifact_id(
            "repair",
            {
                "created_at": created_at.isoformat(),
                "finding_codes": sorted(finding_codes),
                "observed_failure": observed_failure,
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "RepairRequest":
        return cls(
            repair_request_id=payload["repair_request_id"],
            created_at=datetime.fromisoformat(payload["created_at"]),
            status=payload.get("status", "pending"),
            severity=payload.get("severity", "blocking"),
            observed_failure=payload["observed_failure"],
            reproduction_command=payload["reproduction_command"],
            expected_behavior=payload["expected_behavior"],
            affected_artifacts=payload.get("affected_artifacts", []),
            recommended_tests=payload.get("recommended_tests", []),
            safety_boundary=payload.get("safety_boundary", "paper-only; no live trading"),
            acceptance_criteria=payload.get("acceptance_criteria", []),
            finding_codes=payload.get("finding_codes", []),
            prompt_path=payload.get("prompt_path"),
        )


@dataclass(slots=True)
class CycleResult:
    new_forecast: Forecast | None
    scores: list[ForecastScore] = field(default_factory=list)
    review: Review | None = None
    proposal: Proposal | None = None
