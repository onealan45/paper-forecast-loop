from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
import json
import math
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


def _optional_aware_datetime(payload: dict, key: str) -> datetime | None:
    if key not in payload or payload[key] in (None, ""):
        return None
    value = _deserialize_datetime(payload[key])
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(f"datetime field must include timezone: {key}")
    return value


def _require_string(payload: dict, key: str) -> str:
    if key not in payload or not isinstance(payload[key], str) or not payload[key]:
        raise ValueError(f"missing required string field: {key}")
    return payload[key]


def _optional_float(value) -> float | None:
    if value in (None, ""):
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("numeric field must be finite")
    return result


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
class MarketCandleRecord:
    candle_id: str
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str
    imported_at: datetime
    adjusted_close: float | None = None

    @classmethod
    def build_id(cls, *, symbol: str, timestamp: datetime, source: str) -> str:
        return _stable_artifact_id(
            "market-candle",
            {
                "symbol": symbol,
                "timestamp": timestamp.isoformat(),
                "source": source,
            },
        )

    @classmethod
    def from_candle(
        cls,
        candle: MarketCandle,
        *,
        symbol: str,
        source: str,
        imported_at: datetime,
    ) -> "MarketCandleRecord":
        candle_id = cls.build_id(symbol=symbol, timestamp=candle.timestamp, source=source)
        return cls(
            candle_id=candle_id,
            symbol=symbol,
            timestamp=candle.timestamp,
            open=float(candle.open),
            high=float(candle.high),
            low=float(candle.low),
            close=float(candle.close),
            volume=float(candle.volume),
            source=source,
            imported_at=imported_at,
            adjusted_close=None,
        )

    def to_candle(self) -> MarketCandle:
        close = self.adjusted_close if self.adjusted_close is not None else self.close
        return MarketCandle(
            timestamp=self.timestamp,
            open=self.open,
            high=self.high,
            low=self.low,
            close=close,
            volume=self.volume,
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        payload["imported_at"] = self.imported_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "MarketCandleRecord":
        adjusted_close = payload.get("adjusted_close")
        return cls(
            candle_id=_require_string(payload, "candle_id"),
            symbol=_require_string(payload, "symbol"),
            timestamp=_require_aware_datetime(payload, "timestamp"),
            open=float(payload["open"]),
            high=float(payload["high"]),
            low=float(payload["low"]),
            close=float(payload["close"]),
            volume=float(payload["volume"]),
            source=_require_string(payload, "source"),
            imported_at=_require_aware_datetime(payload, "imported_at"),
            adjusted_close=float(adjusted_close) if adjusted_close is not None else None,
        )


@dataclass(slots=True)
class MacroEvent:
    event_id: str
    event_type: str
    name: str
    region: str
    scheduled_at: datetime
    source: str
    imported_at: datetime
    actual_value: float | None = None
    consensus_value: float | None = None
    previous_value: float | None = None
    unit: str | None = None
    importance: str = "medium"
    notes: str | None = None

    ALLOWED_TYPES = {"CPI", "PCE", "FOMC", "GDP", "NFP", "UNEMPLOYMENT"}

    @classmethod
    def build_id(
        cls,
        *,
        event_type: str,
        region: str,
        scheduled_at: datetime,
        source: str,
    ) -> str:
        return _stable_artifact_id(
            "macro-event",
            {
                "event_type": event_type.upper(),
                "region": region.upper(),
                "scheduled_at": scheduled_at.isoformat(),
                "source": source,
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["scheduled_at"] = self.scheduled_at.isoformat()
        payload["imported_at"] = self.imported_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "MacroEvent":
        event_type = _require_string(payload, "event_type").upper()
        if event_type not in cls.ALLOWED_TYPES:
            raise ValueError(f"unsupported macro event type: {event_type}")
        scheduled_at = _require_aware_datetime(payload, "scheduled_at")
        imported_at = _require_aware_datetime(payload, "imported_at")
        payload_event_id = payload.get("event_id")
        event_id = payload_event_id if isinstance(payload_event_id, str) and payload_event_id else cls.build_id(
            event_type=event_type,
            region=_require_string(payload, "region").upper(),
            scheduled_at=scheduled_at,
            source=_require_string(payload, "source"),
        )
        return cls(
            event_id=event_id,
            event_type=event_type,
            name=_require_string(payload, "name"),
            region=_require_string(payload, "region").upper(),
            scheduled_at=scheduled_at,
            source=_require_string(payload, "source"),
            imported_at=imported_at,
            actual_value=_optional_float(payload.get("actual_value")),
            consensus_value=_optional_float(payload.get("consensus_value")),
            previous_value=_optional_float(payload.get("previous_value")),
            unit=payload.get("unit"),
            importance=payload.get("importance", "medium"),
            notes=payload.get("notes"),
        )


@dataclass(slots=True)
class ResearchDatasetRow:
    forecast_id: str
    score_id: str
    symbol: str
    decision_timestamp: datetime
    feature_timestamp: datetime
    label_timestamp: datetime
    features: dict[str, object]
    label: dict[str, object]

    def to_dict(self) -> dict:
        payload = asdict(self)
        for key in ("decision_timestamp", "feature_timestamp", "label_timestamp"):
            payload[key] = payload[key].isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "ResearchDatasetRow":
        return cls(
            forecast_id=_require_string(payload, "forecast_id"),
            score_id=_require_string(payload, "score_id"),
            symbol=_require_string(payload, "symbol"),
            decision_timestamp=_require_aware_datetime(payload, "decision_timestamp"),
            feature_timestamp=_require_aware_datetime(payload, "feature_timestamp"),
            label_timestamp=_require_aware_datetime(payload, "label_timestamp"),
            features=dict(payload.get("features") or {}),
            label=dict(payload.get("label") or {}),
        )


@dataclass(slots=True)
class ResearchDataset:
    dataset_id: str
    created_at: datetime
    symbol: str
    row_count: int
    leakage_status: str
    leakage_findings: list[str]
    forecast_ids: list[str]
    score_ids: list[str]
    rows: list[ResearchDatasetRow]
    decision_basis: str

    @classmethod
    def build_id(
        cls,
        *,
        symbol: str,
        forecast_ids: list[str],
        score_ids: list[str],
        row_count: int,
        leakage_status: str,
    ) -> str:
        return _stable_artifact_id(
            "research-dataset",
            {
                "symbol": symbol,
                "forecast_ids": sorted(forecast_ids),
                "score_ids": sorted(score_ids),
                "row_count": row_count,
                "leakage_status": leakage_status,
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        payload["rows"] = [row.to_dict() for row in self.rows]
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "ResearchDataset":
        rows = [ResearchDatasetRow.from_dict(item) for item in payload.get("rows", [])]
        return cls(
            dataset_id=_require_string(payload, "dataset_id"),
            created_at=_require_aware_datetime(payload, "created_at"),
            symbol=_require_string(payload, "symbol"),
            row_count=int(payload.get("row_count", len(rows))),
            leakage_status=payload.get("leakage_status", "unknown"),
            leakage_findings=list(payload.get("leakage_findings", [])),
            forecast_ids=list(payload.get("forecast_ids", [])),
            score_ids=list(payload.get("score_ids", [])),
            rows=rows,
            decision_basis=payload.get("decision_basis", "legacy_research_dataset"),
        )


@dataclass(slots=True)
class BacktestRun:
    backtest_id: str
    created_at: datetime
    symbol: str
    start: datetime
    end: datetime
    strategy_name: str
    initial_cash: float
    fee_bps: float
    slippage_bps: float
    moving_average_window: int
    candle_ids: list[str]
    decision_basis: str

    @classmethod
    def build_id(
        cls,
        *,
        symbol: str,
        start: datetime,
        end: datetime,
        strategy_name: str,
        initial_cash: float,
        fee_bps: float,
        slippage_bps: float,
        moving_average_window: int,
        candle_ids: list[str],
    ) -> str:
        return _stable_artifact_id(
            "backtest-run",
            {
                "symbol": symbol,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "strategy_name": strategy_name,
                "initial_cash": round(initial_cash, 8),
                "fee_bps": round(fee_bps, 8),
                "slippage_bps": round(slippage_bps, 8),
                "moving_average_window": moving_average_window,
                "candle_ids": sorted(candle_ids),
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        for key in ("created_at", "start", "end"):
            payload[key] = payload[key].isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "BacktestRun":
        return cls(
            backtest_id=_require_string(payload, "backtest_id"),
            created_at=_require_aware_datetime(payload, "created_at"),
            symbol=_require_string(payload, "symbol"),
            start=_require_aware_datetime(payload, "start"),
            end=_require_aware_datetime(payload, "end"),
            strategy_name=payload.get("strategy_name", "moving_average_trend"),
            initial_cash=float(payload.get("initial_cash", 0.0)),
            fee_bps=float(payload.get("fee_bps", 0.0)),
            slippage_bps=float(payload.get("slippage_bps", 0.0)),
            moving_average_window=int(payload.get("moving_average_window", 0)),
            candle_ids=list(payload.get("candle_ids", [])),
            decision_basis=payload.get("decision_basis", "legacy_backtest_run"),
        )


@dataclass(slots=True)
class BacktestResult:
    result_id: str
    backtest_id: str
    created_at: datetime
    symbol: str
    start: datetime
    end: datetime
    initial_cash: float
    final_equity: float
    strategy_return: float
    benchmark_return: float
    max_drawdown: float
    sharpe: float | None
    turnover: float
    win_rate: float | None
    trade_count: int
    equity_curve: list[dict[str, object]]
    decision_basis: str

    @classmethod
    def build_id(
        cls,
        *,
        backtest_id: str,
        final_equity: float,
        trade_count: int,
        strategy_return: float,
    ) -> str:
        return _stable_artifact_id(
            "backtest-result",
            {
                "backtest_id": backtest_id,
                "final_equity": round(final_equity, 8),
                "trade_count": trade_count,
                "strategy_return": round(strategy_return, 8),
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        for key in ("created_at", "start", "end"):
            payload[key] = payload[key].isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "BacktestResult":
        return cls(
            result_id=_require_string(payload, "result_id"),
            backtest_id=_require_string(payload, "backtest_id"),
            created_at=_require_aware_datetime(payload, "created_at"),
            symbol=_require_string(payload, "symbol"),
            start=_require_aware_datetime(payload, "start"),
            end=_require_aware_datetime(payload, "end"),
            initial_cash=float(payload.get("initial_cash", 0.0)),
            final_equity=float(payload.get("final_equity", 0.0)),
            strategy_return=float(payload.get("strategy_return", 0.0)),
            benchmark_return=float(payload.get("benchmark_return", 0.0)),
            max_drawdown=float(payload.get("max_drawdown", 0.0)),
            sharpe=_optional_float(payload.get("sharpe")),
            turnover=float(payload.get("turnover", 0.0)),
            win_rate=_optional_float(payload.get("win_rate")),
            trade_count=int(payload.get("trade_count", 0)),
            equity_curve=list(payload.get("equity_curve", [])),
            decision_basis=payload.get("decision_basis", "legacy_backtest_result"),
        )


@dataclass(slots=True)
class WalkForwardWindow:
    window_id: str
    train_start: datetime
    train_end: datetime
    validation_start: datetime
    validation_end: datetime
    test_start: datetime
    test_end: datetime
    train_candle_count: int
    validation_candle_count: int
    test_candle_count: int
    validation_backtest_result_id: str
    test_backtest_result_id: str
    validation_return: float
    test_return: float
    benchmark_return: float
    excess_return: float
    overfit_flags: list[str]
    decision_basis: str

    @classmethod
    def build_id(
        cls,
        *,
        train_start: datetime,
        validation_start: datetime,
        test_start: datetime,
        validation_backtest_result_id: str,
        test_backtest_result_id: str,
    ) -> str:
        return _stable_artifact_id(
            "walk-forward-window",
            {
                "train_start": train_start.isoformat(),
                "validation_start": validation_start.isoformat(),
                "test_start": test_start.isoformat(),
                "validation_backtest_result_id": validation_backtest_result_id,
                "test_backtest_result_id": test_backtest_result_id,
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        for key in (
            "train_start",
            "train_end",
            "validation_start",
            "validation_end",
            "test_start",
            "test_end",
        ):
            payload[key] = payload[key].isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "WalkForwardWindow":
        return cls(
            window_id=_require_string(payload, "window_id"),
            train_start=_require_aware_datetime(payload, "train_start"),
            train_end=_require_aware_datetime(payload, "train_end"),
            validation_start=_require_aware_datetime(payload, "validation_start"),
            validation_end=_require_aware_datetime(payload, "validation_end"),
            test_start=_require_aware_datetime(payload, "test_start"),
            test_end=_require_aware_datetime(payload, "test_end"),
            train_candle_count=int(payload.get("train_candle_count", 0)),
            validation_candle_count=int(payload.get("validation_candle_count", 0)),
            test_candle_count=int(payload.get("test_candle_count", 0)),
            validation_backtest_result_id=_require_string(payload, "validation_backtest_result_id"),
            test_backtest_result_id=_require_string(payload, "test_backtest_result_id"),
            validation_return=float(payload.get("validation_return", 0.0)),
            test_return=float(payload.get("test_return", 0.0)),
            benchmark_return=float(payload.get("benchmark_return", 0.0)),
            excess_return=float(payload.get("excess_return", 0.0)),
            overfit_flags=list(payload.get("overfit_flags", [])),
            decision_basis=payload.get("decision_basis", "legacy_walk_forward_window"),
        )


@dataclass(slots=True)
class WalkForwardValidation:
    validation_id: str
    created_at: datetime
    symbol: str
    start: datetime
    end: datetime
    strategy_name: str
    train_size: int
    validation_size: int
    test_size: int
    step_size: int
    initial_cash: float
    fee_bps: float
    slippage_bps: float
    moving_average_window: int
    window_count: int
    average_validation_return: float
    average_test_return: float
    average_benchmark_return: float
    average_excess_return: float
    test_win_rate: float
    overfit_window_count: int
    overfit_risk_flags: list[str]
    backtest_result_ids: list[str]
    windows: list[WalkForwardWindow]
    decision_basis: str

    @classmethod
    def build_id(
        cls,
        *,
        symbol: str,
        start: datetime,
        end: datetime,
        train_size: int,
        validation_size: int,
        test_size: int,
        step_size: int,
        moving_average_window: int,
        backtest_result_ids: list[str],
    ) -> str:
        return _stable_artifact_id(
            "walk-forward",
            {
                "symbol": symbol,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "train_size": train_size,
                "validation_size": validation_size,
                "test_size": test_size,
                "step_size": step_size,
                "moving_average_window": moving_average_window,
                "backtest_result_ids": sorted(backtest_result_ids),
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        for key in ("created_at", "start", "end"):
            payload[key] = payload[key].isoformat()
        payload["windows"] = [window.to_dict() for window in self.windows]
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "WalkForwardValidation":
        windows = [WalkForwardWindow.from_dict(item) for item in payload.get("windows", [])]
        return cls(
            validation_id=_require_string(payload, "validation_id"),
            created_at=_require_aware_datetime(payload, "created_at"),
            symbol=_require_string(payload, "symbol"),
            start=_require_aware_datetime(payload, "start"),
            end=_require_aware_datetime(payload, "end"),
            strategy_name=payload.get("strategy_name", "moving_average_trend"),
            train_size=int(payload.get("train_size", 0)),
            validation_size=int(payload.get("validation_size", 0)),
            test_size=int(payload.get("test_size", 0)),
            step_size=int(payload.get("step_size", 0)),
            initial_cash=float(payload.get("initial_cash", 0.0)),
            fee_bps=float(payload.get("fee_bps", 0.0)),
            slippage_bps=float(payload.get("slippage_bps", 0.0)),
            moving_average_window=int(payload.get("moving_average_window", 0)),
            window_count=int(payload.get("window_count", len(windows))),
            average_validation_return=float(payload.get("average_validation_return", 0.0)),
            average_test_return=float(payload.get("average_test_return", 0.0)),
            average_benchmark_return=float(payload.get("average_benchmark_return", 0.0)),
            average_excess_return=float(payload.get("average_excess_return", 0.0)),
            test_win_rate=float(payload.get("test_win_rate", 0.0)),
            overfit_window_count=int(payload.get("overfit_window_count", 0)),
            overfit_risk_flags=list(payload.get("overfit_risk_flags", [])),
            backtest_result_ids=list(payload.get("backtest_result_ids", [])),
            windows=windows,
            decision_basis=payload.get("decision_basis", "legacy_walk_forward_validation"),
        )


@dataclass(slots=True)
class SourceDocument:
    document_id: str
    source_name: str
    source_type: str
    source_url: str | None
    stable_source_id: str | None
    published_at: datetime | None
    available_at: datetime | None
    fetched_at: datetime
    processed_at: datetime
    language: str
    headline: str
    summary: str
    raw_text_hash: str
    normalized_text_hash: str
    body_excerpt: str
    entities: list[str]
    symbols: list[str]
    topics: list[str]
    source_reliability_score: float
    duplicate_group_id: str | None
    license_note: str | None
    ingestion_run_id: str | None

    def to_dict(self) -> dict:
        payload = asdict(self)
        for key in ("published_at", "available_at", "fetched_at", "processed_at"):
            payload[key] = _serialize_datetime(payload[key])
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "SourceDocument":
        return cls(
            document_id=_require_string(payload, "document_id"),
            source_name=_require_string(payload, "source_name"),
            source_type=_require_string(payload, "source_type"),
            source_url=payload.get("source_url"),
            stable_source_id=payload.get("stable_source_id"),
            published_at=_optional_aware_datetime(payload, "published_at"),
            available_at=_optional_aware_datetime(payload, "available_at"),
            fetched_at=_require_aware_datetime(payload, "fetched_at"),
            processed_at=_require_aware_datetime(payload, "processed_at"),
            language=payload.get("language", "unknown"),
            headline=payload.get("headline", ""),
            summary=payload.get("summary", ""),
            raw_text_hash=payload.get("raw_text_hash", ""),
            normalized_text_hash=payload.get("normalized_text_hash", ""),
            body_excerpt=payload.get("body_excerpt", ""),
            entities=list(payload.get("entities", [])),
            symbols=list(payload.get("symbols", [])),
            topics=list(payload.get("topics", [])),
            source_reliability_score=float(payload.get("source_reliability_score", 0.0)),
            duplicate_group_id=payload.get("duplicate_group_id"),
            license_note=payload.get("license_note"),
            ingestion_run_id=payload.get("ingestion_run_id"),
        )


@dataclass(slots=True)
class SourceIngestionRun:
    ingestion_run_id: str
    created_at: datetime
    source_name: str
    source_type: str
    status: str
    document_ids: list[str]
    fetched_count: int
    stored_count: int
    error_message: str | None
    decision_basis: str

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "SourceIngestionRun":
        return cls(
            ingestion_run_id=_require_string(payload, "ingestion_run_id"),
            created_at=_require_aware_datetime(payload, "created_at"),
            source_name=_require_string(payload, "source_name"),
            source_type=_require_string(payload, "source_type"),
            status=_require_string(payload, "status"),
            document_ids=list(payload.get("document_ids", [])),
            fetched_count=int(payload.get("fetched_count", 0)),
            stored_count=int(payload.get("stored_count", 0)),
            error_message=payload.get("error_message"),
            decision_basis=payload.get("decision_basis", ""),
        )


@dataclass(slots=True)
class CanonicalEvent:
    event_id: str
    event_family: str
    event_type: str
    symbol: str
    title: str
    summary: str
    event_time: datetime | None
    published_at: datetime | None
    available_at: datetime | None
    fetched_at: datetime
    source_document_ids: list[str]
    primary_document_id: str | None
    credibility_score: float
    cross_source_count: int
    official_source_flag: bool
    duplicate_group_id: str | None
    status: str

    def to_dict(self) -> dict:
        payload = asdict(self)
        for key in ("event_time", "published_at", "available_at", "fetched_at"):
            payload[key] = _serialize_datetime(payload[key])
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "CanonicalEvent":
        return cls(
            event_id=_require_string(payload, "event_id"),
            event_family=_require_string(payload, "event_family"),
            event_type=_require_string(payload, "event_type"),
            symbol=_require_string(payload, "symbol"),
            title=payload.get("title", ""),
            summary=payload.get("summary", ""),
            event_time=_optional_aware_datetime(payload, "event_time"),
            published_at=_optional_aware_datetime(payload, "published_at"),
            available_at=_optional_aware_datetime(payload, "available_at"),
            fetched_at=_require_aware_datetime(payload, "fetched_at"),
            source_document_ids=list(payload.get("source_document_ids", [])),
            primary_document_id=payload.get("primary_document_id"),
            credibility_score=float(payload.get("credibility_score", 0.0)),
            cross_source_count=int(payload.get("cross_source_count", 0)),
            official_source_flag=bool(payload.get("official_source_flag", False)),
            duplicate_group_id=payload.get("duplicate_group_id"),
            status=payload.get("status", "candidate"),
        )


@dataclass(slots=True)
class EventReliabilityCheck:
    check_id: str
    event_id: str
    created_at: datetime
    symbol: str
    source_type: str
    source_reliability_score: float
    official_source_flag: bool
    cross_source_count: int
    duplicate_count: int
    has_stable_source: bool
    has_required_timestamps: bool
    raw_hash_present: bool
    passed: bool
    blocked_reason: str | None
    flags: list[str]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "EventReliabilityCheck":
        return cls(
            check_id=_require_string(payload, "check_id"),
            event_id=_require_string(payload, "event_id"),
            created_at=_require_aware_datetime(payload, "created_at"),
            symbol=_require_string(payload, "symbol"),
            source_type=_require_string(payload, "source_type"),
            source_reliability_score=float(payload.get("source_reliability_score", 0.0)),
            official_source_flag=bool(payload.get("official_source_flag", False)),
            cross_source_count=int(payload.get("cross_source_count", 0)),
            duplicate_count=int(payload.get("duplicate_count", 0)),
            has_stable_source=bool(payload.get("has_stable_source", False)),
            has_required_timestamps=bool(payload.get("has_required_timestamps", False)),
            raw_hash_present=bool(payload.get("raw_hash_present", False)),
            passed=bool(payload.get("passed", False)),
            blocked_reason=payload.get("blocked_reason"),
            flags=list(payload.get("flags", [])),
        )


@dataclass(slots=True)
class MarketReactionCheck:
    check_id: str
    event_id: str
    symbol: str
    created_at: datetime
    decision_timestamp: datetime
    event_timestamp_used: datetime
    pre_event_ret_1h: float | None
    pre_event_ret_4h: float | None
    pre_event_ret_24h: float | None
    post_event_ret_15m: float | None
    post_event_ret_1h: float | None
    pre_event_drift_z: float | None
    volume_shock_z: float | None
    priced_in_ratio: float | None
    already_priced: bool
    passed: bool
    blocked_reason: str | None
    flags: list[str]

    def to_dict(self) -> dict:
        payload = asdict(self)
        for key in ("created_at", "decision_timestamp", "event_timestamp_used"):
            payload[key] = _serialize_datetime(payload[key])
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "MarketReactionCheck":
        return cls(
            check_id=_require_string(payload, "check_id"),
            event_id=_require_string(payload, "event_id"),
            symbol=_require_string(payload, "symbol"),
            created_at=_require_aware_datetime(payload, "created_at"),
            decision_timestamp=_require_aware_datetime(payload, "decision_timestamp"),
            event_timestamp_used=_require_aware_datetime(payload, "event_timestamp_used"),
            pre_event_ret_1h=_optional_float(payload.get("pre_event_ret_1h")),
            pre_event_ret_4h=_optional_float(payload.get("pre_event_ret_4h")),
            pre_event_ret_24h=_optional_float(payload.get("pre_event_ret_24h")),
            post_event_ret_15m=_optional_float(payload.get("post_event_ret_15m")),
            post_event_ret_1h=_optional_float(payload.get("post_event_ret_1h")),
            pre_event_drift_z=_optional_float(payload.get("pre_event_drift_z")),
            volume_shock_z=_optional_float(payload.get("volume_shock_z")),
            priced_in_ratio=_optional_float(payload.get("priced_in_ratio")),
            already_priced=bool(payload.get("already_priced", False)),
            passed=bool(payload.get("passed", False)),
            blocked_reason=payload.get("blocked_reason"),
            flags=list(payload.get("flags", [])),
        )


@dataclass(slots=True)
class EventEdgeEvaluation:
    evaluation_id: str
    event_family: str
    event_type: str
    symbol: str
    created_at: datetime
    split: str
    horizon_hours: int
    sample_n: int
    average_forward_return: float | None
    average_benchmark_return: float | None
    average_excess_return_after_costs: float | None
    hit_rate: float | None
    max_adverse_excursion_p50: float | None
    max_adverse_excursion_p90: float | None
    max_drawdown_if_traded: float | None
    turnover: float | None
    estimated_cost_bps: float
    dsr: float | None
    white_rc_p: float | None
    stability_score: float | None
    passed: bool
    blocked_reason: str | None
    flags: list[str]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "EventEdgeEvaluation":
        return cls(
            evaluation_id=_require_string(payload, "evaluation_id"),
            event_family=_require_string(payload, "event_family"),
            event_type=_require_string(payload, "event_type"),
            symbol=_require_string(payload, "symbol"),
            created_at=_require_aware_datetime(payload, "created_at"),
            split=payload.get("split", "validation"),
            horizon_hours=int(payload.get("horizon_hours", 24)),
            sample_n=int(payload.get("sample_n", 0)),
            average_forward_return=_optional_float(payload.get("average_forward_return")),
            average_benchmark_return=_optional_float(payload.get("average_benchmark_return")),
            average_excess_return_after_costs=_optional_float(payload.get("average_excess_return_after_costs")),
            hit_rate=_optional_float(payload.get("hit_rate")),
            max_adverse_excursion_p50=_optional_float(payload.get("max_adverse_excursion_p50")),
            max_adverse_excursion_p90=_optional_float(payload.get("max_adverse_excursion_p90")),
            max_drawdown_if_traded=_optional_float(payload.get("max_drawdown_if_traded")),
            turnover=_optional_float(payload.get("turnover")),
            estimated_cost_bps=float(payload.get("estimated_cost_bps", 0.0)),
            dsr=_optional_float(payload.get("dsr")),
            white_rc_p=_optional_float(payload.get("white_rc_p")),
            stability_score=_optional_float(payload.get("stability_score")),
            passed=bool(payload.get("passed", False)),
            blocked_reason=payload.get("blocked_reason"),
            flags=list(payload.get("flags", [])),
        )


@dataclass(slots=True)
class FeatureSnapshot:
    feature_snapshot_id: str
    created_at: datetime
    decision_timestamp: datetime
    symbol: str
    source_kind: str
    feature_namespace: str
    feature_name: str
    feature_value: float | str | bool | None
    feature_timestamp: datetime
    training_cutoff: datetime
    source_document_ids: list[str]
    event_ids: list[str]
    lineage_hash: str
    leakage_safe: bool
    flags: list[str]

    def to_dict(self) -> dict:
        payload = asdict(self)
        for key in ("created_at", "decision_timestamp", "feature_timestamp", "training_cutoff"):
            payload[key] = _serialize_datetime(payload[key])
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "FeatureSnapshot":
        return cls(
            feature_snapshot_id=_require_string(payload, "feature_snapshot_id"),
            created_at=_require_aware_datetime(payload, "created_at"),
            decision_timestamp=_require_aware_datetime(payload, "decision_timestamp"),
            symbol=_require_string(payload, "symbol"),
            source_kind=_require_string(payload, "source_kind"),
            feature_namespace=_require_string(payload, "feature_namespace"),
            feature_name=_require_string(payload, "feature_name"),
            feature_value=payload.get("feature_value"),
            feature_timestamp=_require_aware_datetime(payload, "feature_timestamp"),
            training_cutoff=_require_aware_datetime(payload, "training_cutoff"),
            source_document_ids=list(payload.get("source_document_ids", [])),
            event_ids=list(payload.get("event_ids", [])),
            lineage_hash=payload.get("lineage_hash", ""),
            leakage_safe=bool(payload.get("leakage_safe", False)),
            flags=list(payload.get("flags", [])),
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
    baseline_results: list[dict[str, object]] = field(default_factory=list)

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
            baseline_results=list(payload.get("baseline_results", [])),
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


class BrokerOrderStatus(StrEnum):
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    ERROR = "ERROR"


class BrokerReconciliationStatus(StrEnum):
    MATCHED = "MATCHED"
    MISMATCH = "MISMATCH"
    ERROR = "ERROR"


class ExecutionSafetyGateStatus(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"


class PaperControlAction(StrEnum):
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    STOP_NEW_ENTRIES = "STOP_NEW_ENTRIES"
    REDUCE_RISK = "REDUCE_RISK"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    SET_MAX_POSITION = "SET_MAX_POSITION"


@dataclass(slots=True)
class PaperControlEvent:
    control_id: str
    created_at: datetime
    action: str
    actor: str
    reason: str
    status: str
    symbol: str | None
    requires_confirmation: bool
    confirmed: bool
    parameter_name: str | None = None
    parameter_value: float | None = None
    decision_basis: str = "paper_control"

    @classmethod
    def build_id(
        cls,
        *,
        created_at: datetime,
        action: str,
        actor: str,
        reason: str,
        symbol: str | None,
        parameter_name: str | None,
        parameter_value: float | None,
    ) -> str:
        return _stable_artifact_id(
            "control",
            {
                "created_at": created_at.isoformat(),
                "action": action,
                "actor": actor,
                "reason": reason,
                "symbol": symbol,
                "parameter_name": parameter_name,
                "parameter_value": parameter_value,
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "PaperControlEvent":
        action = _require_string(payload, "action").upper()
        if action not in {item.value for item in PaperControlAction}:
            raise ValueError(f"unsupported paper control action: {action}")
        return cls(
            control_id=_require_string(payload, "control_id"),
            created_at=_require_aware_datetime(payload, "created_at"),
            action=action,
            actor=payload.get("actor", "operator"),
            reason=_require_string(payload, "reason"),
            status=payload.get("status", "ACTIVE"),
            symbol=payload.get("symbol"),
            requires_confirmation=bool(payload.get("requires_confirmation", False)),
            confirmed=bool(payload.get("confirmed", False)),
            parameter_name=payload.get("parameter_name"),
            parameter_value=_optional_float(payload.get("parameter_value")),
            decision_basis=payload.get("decision_basis", "legacy_paper_control"),
        )


@dataclass(slots=True)
class AutomationRun:
    automation_run_id: str
    started_at: datetime
    completed_at: datetime
    status: str
    symbol: str
    provider: str
    command: str
    steps: list[dict[str, str | None]]
    health_check_id: str | None
    decision_id: str | None
    repair_request_id: str | None
    decision_basis: str = "automation run log"

    @classmethod
    def build_id(
        cls,
        *,
        started_at: datetime,
        completed_at: datetime,
        symbol: str,
        provider: str,
        command: str,
        status: str,
    ) -> str:
        return _stable_artifact_id(
            "automation-run",
            {
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "symbol": symbol,
                "provider": provider,
                "command": command,
                "status": status,
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["started_at"] = self.started_at.isoformat()
        payload["completed_at"] = self.completed_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "AutomationRun":
        steps = []
        for step in payload.get("steps", []):
            if not isinstance(step, dict):
                raise ValueError("automation run step must be an object")
            steps.append(
                {
                    "name": str(step.get("name") or ""),
                    "status": str(step.get("status") or ""),
                    "artifact_id": step.get("artifact_id"),
                }
            )
        return cls(
            automation_run_id=_require_string(payload, "automation_run_id"),
            started_at=_require_aware_datetime(payload, "started_at"),
            completed_at=_require_aware_datetime(payload, "completed_at"),
            status=_require_string(payload, "status"),
            symbol=_require_string(payload, "symbol"),
            provider=_require_string(payload, "provider"),
            command=_require_string(payload, "command"),
            steps=steps,
            health_check_id=payload.get("health_check_id"),
            decision_id=payload.get("decision_id"),
            repair_request_id=payload.get("repair_request_id"),
            decision_basis=payload.get("decision_basis", "legacy_automation_run"),
        )


@dataclass(slots=True)
class NotificationArtifact:
    notification_id: str
    created_at: datetime
    symbol: str
    notification_type: str
    severity: str
    title: str
    message: str
    status: str
    delivery_channel: str
    action: str | None
    source_artifact_ids: list[str]
    decision_id: str | None
    health_check_id: str | None
    repair_request_id: str | None
    risk_id: str | None
    decision_basis: str

    ALLOWED_TYPES = {
        "NEW_DECISION",
        "BUY_SELL_BLOCKED",
        "STOP_NEW_ENTRIES",
        "HEALTH_BLOCKING",
        "REPAIR_REQUEST_CREATED",
        "DRAWDOWN_BREACH",
    }
    ALLOWED_SEVERITIES = {"info", "warning", "blocking"}

    @classmethod
    def build_id(
        cls,
        *,
        created_at: datetime,
        symbol: str,
        notification_type: str,
        source_artifact_ids: list[str],
        message: str,
    ) -> str:
        return _stable_artifact_id(
            "notification",
            {
                "created_at": created_at.isoformat(),
                "symbol": symbol,
                "notification_type": notification_type,
                "source_artifact_ids": sorted(source_artifact_ids),
                "message": message,
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "NotificationArtifact":
        notification_type = _require_string(payload, "notification_type")
        if notification_type not in cls.ALLOWED_TYPES:
            raise ValueError(f"unsupported notification type: {notification_type}")
        severity = _require_string(payload, "severity")
        if severity not in cls.ALLOWED_SEVERITIES:
            raise ValueError(f"unsupported notification severity: {severity}")
        return cls(
            notification_id=_require_string(payload, "notification_id"),
            created_at=_require_aware_datetime(payload, "created_at"),
            symbol=_require_string(payload, "symbol"),
            notification_type=notification_type,
            severity=severity,
            title=_require_string(payload, "title"),
            message=_require_string(payload, "message"),
            status=payload.get("status", "pending"),
            delivery_channel=payload.get("delivery_channel", "local_artifact"),
            action=payload.get("action"),
            source_artifact_ids=list(payload.get("source_artifact_ids", [])),
            decision_id=payload.get("decision_id"),
            health_check_id=payload.get("health_check_id"),
            repair_request_id=payload.get("repair_request_id"),
            risk_id=payload.get("risk_id"),
            decision_basis=payload.get("decision_basis", "legacy_notification_artifact"),
        )


@dataclass(slots=True)
class BrokerOrder:
    broker_order_id: str
    created_at: datetime
    updated_at: datetime
    local_order_id: str
    decision_id: str
    symbol: str
    side: str
    quantity: float | None
    target_position_pct: float | None
    broker: str
    broker_mode: str
    status: str
    broker_status: str | None
    broker_order_ref: str | None
    client_order_id: str | None
    error_message: str | None
    raw_response: dict
    decision_basis: str

    @classmethod
    def build_id(cls, *, local_order_id: str, broker: str, broker_mode: str) -> str:
        return _stable_artifact_id(
            "broker-order",
            {
                "local_order_id": local_order_id,
                "broker": broker,
                "broker_mode": broker_mode,
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        payload["updated_at"] = self.updated_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "BrokerOrder":
        status = _require_string(payload, "status")
        if status not in {item.value for item in BrokerOrderStatus}:
            raise ValueError(f"unsupported broker order status: {status}")
        return cls(
            broker_order_id=_require_string(payload, "broker_order_id"),
            created_at=_require_aware_datetime(payload, "created_at"),
            updated_at=_require_aware_datetime(payload, "updated_at"),
            local_order_id=_require_string(payload, "local_order_id"),
            decision_id=_require_string(payload, "decision_id"),
            symbol=_require_string(payload, "symbol"),
            side=_require_string(payload, "side"),
            quantity=_optional_float(payload.get("quantity")),
            target_position_pct=_optional_float(payload.get("target_position_pct")),
            broker=payload.get("broker", "unknown"),
            broker_mode=payload.get("broker_mode", "SANDBOX"),
            status=status,
            broker_status=payload.get("broker_status"),
            broker_order_ref=payload.get("broker_order_ref"),
            client_order_id=payload.get("client_order_id"),
            error_message=payload.get("error_message"),
            raw_response=dict(payload.get("raw_response", {})),
            decision_basis=payload.get("decision_basis", "legacy_broker_order"),
        )


@dataclass(slots=True)
class BrokerReconciliation:
    reconciliation_id: str
    created_at: datetime
    broker: str
    broker_mode: str
    status: str
    severity: str
    repair_required: bool
    local_broker_order_ids: list[str]
    external_order_refs: list[str]
    matched_order_refs: list[str]
    missing_external_order_ids: list[str]
    unknown_external_order_refs: list[str]
    duplicate_broker_order_refs: list[str]
    status_mismatches: list[dict]
    position_mismatches: list[dict]
    cash_mismatch: dict | None
    equity_mismatch: dict | None
    findings: list[dict]
    decision_basis: str

    @classmethod
    def build_id(
        cls,
        *,
        created_at: datetime,
        broker: str,
        broker_mode: str,
        local_broker_order_ids: list[str],
        external_order_refs: list[str],
        findings: list[dict],
    ) -> str:
        return _stable_artifact_id(
            "broker-reconciliation",
            {
                "created_at": created_at.isoformat(),
                "broker": broker,
                "broker_mode": broker_mode,
                "local_broker_order_ids": sorted(local_broker_order_ids),
                "external_order_refs": sorted(external_order_refs),
                "findings": findings,
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "BrokerReconciliation":
        status = _require_string(payload, "status")
        if status not in {item.value for item in BrokerReconciliationStatus}:
            raise ValueError(f"unsupported broker reconciliation status: {status}")
        severity = payload.get("severity", "none")
        if severity not in {"none", "warning", "blocking"}:
            raise ValueError(f"unsupported broker reconciliation severity: {severity}")
        return cls(
            reconciliation_id=_require_string(payload, "reconciliation_id"),
            created_at=_require_aware_datetime(payload, "created_at"),
            broker=_require_string(payload, "broker"),
            broker_mode=_require_string(payload, "broker_mode"),
            status=status,
            severity=severity,
            repair_required=bool(payload.get("repair_required", False)),
            local_broker_order_ids=list(payload.get("local_broker_order_ids", [])),
            external_order_refs=list(payload.get("external_order_refs", [])),
            matched_order_refs=list(payload.get("matched_order_refs", [])),
            missing_external_order_ids=list(payload.get("missing_external_order_ids", [])),
            unknown_external_order_refs=list(payload.get("unknown_external_order_refs", [])),
            duplicate_broker_order_refs=list(payload.get("duplicate_broker_order_refs", [])),
            status_mismatches=list(payload.get("status_mismatches", [])),
            position_mismatches=list(payload.get("position_mismatches", [])),
            cash_mismatch=payload.get("cash_mismatch"),
            equity_mismatch=payload.get("equity_mismatch"),
            findings=list(payload.get("findings", [])),
            decision_basis=payload.get("decision_basis", "legacy_broker_reconciliation"),
        )


@dataclass(slots=True)
class ExecutionSafetyGate:
    gate_id: str
    created_at: datetime
    symbol: str
    decision_id: str | None
    order_id: str | None
    broker: str
    broker_mode: str
    status: str
    severity: str
    allowed: bool
    checks: list[dict]
    health_check_id: str | None
    risk_id: str | None
    broker_reconciliation_id: str | None
    decision_basis: str

    @classmethod
    def build_id(
        cls,
        *,
        created_at: datetime,
        symbol: str,
        decision_id: str | None,
        order_id: str | None,
        broker: str,
        broker_mode: str,
        checks: list[dict],
    ) -> str:
        return _stable_artifact_id(
            "execution-gate",
            {
                "created_at": created_at.isoformat(),
                "symbol": symbol,
                "decision_id": decision_id,
                "order_id": order_id,
                "broker": broker,
                "broker_mode": broker_mode,
                "checks": checks,
            },
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "ExecutionSafetyGate":
        status = _require_string(payload, "status")
        if status not in {item.value for item in ExecutionSafetyGateStatus}:
            raise ValueError(f"unsupported execution safety gate status: {status}")
        severity = payload.get("severity", "none")
        if severity not in {"none", "blocking"}:
            raise ValueError(f"unsupported execution safety gate severity: {severity}")
        return cls(
            gate_id=_require_string(payload, "gate_id"),
            created_at=_require_aware_datetime(payload, "created_at"),
            symbol=_require_string(payload, "symbol"),
            decision_id=payload.get("decision_id"),
            order_id=payload.get("order_id"),
            broker=_require_string(payload, "broker"),
            broker_mode=_require_string(payload, "broker_mode"),
            status=status,
            severity=severity,
            allowed=bool(payload.get("allowed", False)),
            checks=list(payload.get("checks", [])),
            health_check_id=payload.get("health_check_id"),
            risk_id=payload.get("risk_id"),
            broker_reconciliation_id=payload.get("broker_reconciliation_id"),
            decision_basis=payload.get("decision_basis", "legacy_execution_safety_gate"),
        )


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
