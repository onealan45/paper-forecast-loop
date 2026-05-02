from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha1
import json
from pathlib import Path

from forecast_loop.models import CanonicalEvent, MarketCandleRecord, MarketReactionCheck, SourceDocument
from forecast_loop.storage import JsonFileRepository


@dataclass(slots=True)
class MarketDerivedEventBuildResult:
    storage_dir: Path
    created_at: datetime
    symbol: str
    source_document_ids: list[str]
    event_ids: list[str]
    check_ids: list[str]
    source_document_count: int
    event_count: int
    market_reaction_check_count: int

    def to_dict(self) -> dict:
        return {
            "storage_dir": str(self.storage_dir.resolve()),
            "created_at": self.created_at.isoformat(),
            "symbol": self.symbol,
            "source_document_ids": list(self.source_document_ids),
            "event_ids": list(self.event_ids),
            "check_ids": list(self.check_ids),
            "source_document_count": self.source_document_count,
            "event_count": self.event_count,
            "market_reaction_check_count": self.market_reaction_check_count,
        }


@dataclass(frozen=True, slots=True)
class _MarketMove:
    timestamp: datetime
    previous_timestamp: datetime
    hourly_return: float
    forward_return_24h: float
    close: float
    previous_close: float
    volume: float


def build_market_derived_events(
    *,
    storage_dir: Path | str,
    symbol: str,
    created_at: datetime,
    min_abs_return: float = 0.02,
    max_events: int = 20,
) -> MarketDerivedEventBuildResult:
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("created_at must be timezone-aware")
    if min_abs_return <= 0:
        raise ValueError("min_abs_return must be greater than 0")
    if max_events <= 0:
        raise ValueError("max_events must be greater than 0")
    created_at_utc = created_at.astimezone(UTC)
    symbol = symbol.upper()
    repository = JsonFileRepository(storage_dir)
    candles = _deduped_candles(repository.load_market_candles(), symbol=symbol, created_at=created_at_utc)
    moves = _market_moves(candles, min_abs_return=min_abs_return)[:max_events]

    source_document_ids: list[str] = []
    event_ids: list[str] = []
    check_ids: list[str] = []
    for move in moves:
        document = _source_document(symbol=symbol, move=move, created_at=created_at_utc)
        event = _canonical_event(symbol=symbol, move=move, document=document, created_at=created_at_utc)
        check = _market_reaction_check(symbol=symbol, move=move, event=event, candles=candles, created_at=created_at_utc)
        repository.save_source_document(document)
        repository.save_canonical_event(event)
        repository.save_market_reaction_check(check)
        source_document_ids.append(document.document_id)
        event_ids.append(event.event_id)
        check_ids.append(check.check_id)

    return MarketDerivedEventBuildResult(
        storage_dir=Path(storage_dir),
        created_at=created_at_utc,
        symbol=symbol,
        source_document_ids=source_document_ids,
        event_ids=event_ids,
        check_ids=check_ids,
        source_document_count=len(source_document_ids),
        event_count=len(event_ids),
        market_reaction_check_count=len(check_ids),
    )


def _deduped_candles(
    records: list[MarketCandleRecord],
    *,
    symbol: str,
    created_at: datetime,
) -> list[MarketCandleRecord]:
    by_time: dict[datetime, MarketCandleRecord] = {}
    for record in records:
        if record.symbol != symbol:
            continue
        if record.timestamp > created_at or record.imported_at > created_at:
            continue
        existing = by_time.get(record.timestamp)
        if existing is None or (record.imported_at, record.source, record.candle_id) > (
            existing.imported_at,
            existing.source,
            existing.candle_id,
        ):
            by_time[record.timestamp] = record
    return [by_time[key] for key in sorted(by_time)]


def _market_moves(candles: list[MarketCandleRecord], *, min_abs_return: float) -> list[_MarketMove]:
    by_time = {candle.timestamp: candle for candle in candles}
    moves: list[_MarketMove] = []
    for candle in candles:
        previous = by_time.get(candle.timestamp - timedelta(hours=1))
        forward = by_time.get(candle.timestamp + timedelta(hours=24))
        if previous is None or forward is None or previous.close == 0 or candle.close == 0:
            continue
        hourly_return = (candle.close / previous.close) - 1.0
        if abs(hourly_return) < min_abs_return:
            continue
        moves.append(
            _MarketMove(
                timestamp=candle.timestamp,
                previous_timestamp=previous.timestamp,
                hourly_return=hourly_return,
                forward_return_24h=(forward.close / candle.close) - 1.0,
                close=candle.close,
                previous_close=previous.close,
                volume=candle.volume,
            )
        )
    return sorted(moves, key=lambda item: (item.timestamp, abs(item.hourly_return)), reverse=True)


def _source_document(*, symbol: str, move: _MarketMove, created_at: datetime) -> SourceDocument:
    direction = "up" if move.hourly_return > 0 else "down"
    raw_text = (
        f"{symbol} market-derived {direction} move at {move.timestamp.isoformat()}: "
        f"hourly_return={move.hourly_return:.6f}, close={move.close:.6f}, "
        f"previous_close={move.previous_close:.6f}, volume={move.volume:.6f}."
    )
    raw_hash = _hash(raw_text)
    document_id = _artifact_id(
        "source-document",
        {
            "source": "market_derived_candle_event",
            "symbol": symbol,
            "timestamp": move.timestamp.isoformat(),
            "hourly_return": round(move.hourly_return, 10),
        },
    )
    return SourceDocument(
        document_id=document_id,
        source_name="Market Derived Candle Event",
        source_type="market_data",
        source_url=None,
        stable_source_id=f"market-derived-candle-event:{symbol}:{move.timestamp.isoformat()}",
        published_at=move.timestamp,
        available_at=move.timestamp,
        fetched_at=created_at,
        processed_at=created_at,
        language="machine",
        headline=f"{symbol} market-derived {direction} move",
        summary=raw_text,
        raw_text_hash=raw_hash,
        normalized_text_hash=_hash(raw_text.lower()),
        body_excerpt=raw_text,
        entities=[symbol],
        symbols=[symbol],
        topics=["market_derived_move"],
        source_reliability_score=100.0,
        duplicate_group_id=f"market-derived-move:{symbol}:{move.timestamp.isoformat()}",
        license_note="derived from local market_candles artifact",
        ingestion_run_id=None,
        source_id=None,
    )


def _canonical_event(
    *,
    symbol: str,
    move: _MarketMove,
    document: SourceDocument,
    created_at: datetime,
) -> CanonicalEvent:
    event_id = _artifact_id(
        "canonical-event",
        {
            "event_family": "market_derived_move",
            "symbol": symbol,
            "timestamp": move.timestamp.isoformat(),
            "document_id": document.document_id,
        },
    )
    return CanonicalEvent(
        event_id=event_id,
        event_family="market_derived_move",
        event_type="MARKET_DERIVED_MOVE",
        symbol=symbol,
        title=document.headline,
        summary=document.summary,
        event_time=move.timestamp,
        published_at=move.timestamp,
        available_at=move.timestamp,
        fetched_at=created_at,
        source_document_ids=[document.document_id],
        primary_document_id=document.document_id,
        credibility_score=100.0,
        cross_source_count=1,
        official_source_flag=False,
        duplicate_group_id=document.duplicate_group_id,
        status="reliable",
        created_at=created_at,
    )


def _market_reaction_check(
    *,
    symbol: str,
    move: _MarketMove,
    event: CanonicalEvent,
    candles: list[MarketCandleRecord],
    created_at: datetime,
) -> MarketReactionCheck:
    return MarketReactionCheck(
        check_id=_artifact_id(
            "market-reaction",
            {
                "source": "market_derived_candle_event",
                "event_id": event.event_id,
                "timestamp": move.timestamp.isoformat(),
            },
        ),
        event_id=event.event_id,
        symbol=symbol,
        created_at=created_at,
        decision_timestamp=created_at,
        event_timestamp_used=move.timestamp,
        pre_event_ret_1h=_return_between(candles, move.timestamp - timedelta(hours=1), move.timestamp),
        pre_event_ret_4h=_return_between(candles, move.timestamp - timedelta(hours=4), move.timestamp),
        pre_event_ret_24h=_return_between(candles, move.timestamp - timedelta(hours=24), move.timestamp),
        post_event_ret_15m=None,
        post_event_ret_1h=_return_between(candles, move.timestamp, move.timestamp + timedelta(hours=1)),
        pre_event_drift_z=None,
        volume_shock_z=None,
        priced_in_ratio=None,
        already_priced=False,
        passed=True,
        blocked_reason=None,
        flags=[],
    )


def _return_between(candles: list[MarketCandleRecord], start: datetime, end: datetime) -> float | None:
    start_candle = _candle_at(candles, start)
    end_candle = _candle_at(candles, end)
    if start_candle is None or end_candle is None or start_candle.close == 0:
        return None
    return (end_candle.close / start_candle.close) - 1.0


def _candle_at(candles: list[MarketCandleRecord], timestamp: datetime) -> MarketCandleRecord | None:
    for candle in candles:
        if candle.timestamp == timestamp:
            return candle
    return None


def _artifact_id(prefix: str, payload: dict) -> str:
    digest = sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{digest}"


def _hash(value: str) -> str:
    return sha1(value.encode("utf-8")).hexdigest()
