from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha1
import json
import math
from pathlib import Path

from forecast_loop.models import CanonicalEvent, EventReliabilityCheck, MarketCandleRecord, MarketReactionCheck
from forecast_loop.storage import JsonFileRepository


@dataclass(slots=True)
class MarketReactionBuildResult:
    storage_dir: Path
    created_at: datetime
    symbol: str | None
    event_ids: list[str]
    check_ids: list[str]
    market_reaction_check_count: int

    def to_dict(self) -> dict:
        return {
            "storage_dir": str(self.storage_dir.resolve()),
            "created_at": self.created_at.isoformat(),
            "symbol": self.symbol,
            "event_ids": self.event_ids,
            "check_ids": self.check_ids,
            "market_reaction_check_count": self.market_reaction_check_count,
        }


def build_market_reactions(
    *,
    storage_dir: Path | str,
    created_at: datetime,
    symbol: str | None = None,
    already_priced_return_threshold: float = 0.03,
    volume_shock_z_threshold: float = 3.0,
) -> MarketReactionBuildResult:
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("created_at must be timezone-aware")
    if already_priced_return_threshold <= 0:
        raise ValueError("already_priced_return_threshold must be greater than 0")
    if volume_shock_z_threshold <= 0:
        raise ValueError("volume_shock_z_threshold must be greater than 0")
    created_at_utc = created_at.astimezone(UTC)
    repository = JsonFileRepository(storage_dir)
    events = _eligible_events(repository.load_canonical_events(), created_at=created_at_utc, symbol=symbol)
    reliability_by_event = _latest_reliability_by_event(
        repository.load_event_reliability_checks(),
        created_at=created_at_utc,
    )
    candles_by_symbol = _candles_by_symbol(repository.load_market_candles(), created_at=created_at_utc)
    event_ids: list[str] = []
    check_ids: list[str] = []

    for event in events:
        reliability = reliability_by_event.get(event.event_id)
        check = _build_market_reaction_check(
            event=event,
            reliability=reliability,
            candles=candles_by_symbol.get(event.symbol, []),
            created_at=created_at_utc,
            already_priced_return_threshold=already_priced_return_threshold,
            volume_shock_z_threshold=volume_shock_z_threshold,
        )
        _replace_unique(repository.market_reaction_checks_path, check.to_dict(), identity_key="check_id")
        event_ids.append(event.event_id)
        check_ids.append(check.check_id)

    return MarketReactionBuildResult(
        storage_dir=Path(storage_dir),
        created_at=created_at_utc,
        symbol=symbol,
        event_ids=event_ids,
        check_ids=check_ids,
        market_reaction_check_count=len(check_ids),
    )


def _eligible_events(
    events: list[CanonicalEvent],
    *,
    created_at: datetime,
    symbol: str | None,
) -> list[CanonicalEvent]:
    eligible: list[CanonicalEvent] = []
    for event in events:
        if symbol is not None and event.symbol != symbol:
            continue
        if event.available_at is None or event.available_at > created_at:
            continue
        if event.fetched_at > created_at:
            continue
        if event.created_at is not None and event.created_at > created_at:
            continue
        eligible.append(event)
    return sorted(eligible, key=lambda event: (event.available_at or event.fetched_at, event.event_id))


def _latest_reliability_by_event(
    checks: list[EventReliabilityCheck],
    *,
    created_at: datetime,
) -> dict[str, EventReliabilityCheck]:
    result: dict[str, EventReliabilityCheck] = {}
    for check in sorted(checks, key=lambda item: (item.created_at, item.check_id)):
        if check.created_at > created_at:
            continue
        result[check.event_id] = check
    return result


def _candles_by_symbol(records: list[MarketCandleRecord], *, created_at: datetime) -> dict[str, list[MarketCandleRecord]]:
    by_symbol_and_time: dict[tuple[str, datetime], MarketCandleRecord] = {}
    for record in records:
        if record.timestamp > created_at or record.imported_at > created_at:
            continue
        key = (record.symbol, record.timestamp)
        existing = by_symbol_and_time.get(key)
        if existing is None or (record.imported_at, record.source, record.candle_id) > (
            existing.imported_at,
            existing.source,
            existing.candle_id,
        ):
            by_symbol_and_time[key] = record
    result: dict[str, list[MarketCandleRecord]] = {}
    for record in by_symbol_and_time.values():
        result.setdefault(record.symbol, []).append(record)
    for symbol_records in result.values():
        symbol_records.sort(key=lambda record: record.timestamp)
    return result


def _build_market_reaction_check(
    *,
    event: CanonicalEvent,
    reliability: EventReliabilityCheck | None,
    candles: list[MarketCandleRecord],
    created_at: datetime,
    already_priced_return_threshold: float,
    volume_shock_z_threshold: float,
) -> MarketReactionCheck:
    event_timestamp = event.available_at or event.event_time or event.fetched_at
    pre_event_ret_1h = _return_between(candles, event_timestamp - timedelta(hours=1), event_timestamp)
    pre_event_ret_4h = _return_between(candles, event_timestamp - timedelta(hours=4), event_timestamp)
    pre_event_ret_24h = _return_between(candles, event_timestamp - timedelta(hours=24), event_timestamp)
    post_event_ret_1h = (
        _return_between(candles, event_timestamp, event_timestamp + timedelta(hours=1))
        if event_timestamp + timedelta(hours=1) <= created_at
        else None
    )
    volume_shock_z = _volume_shock_z(candles, event_timestamp)
    pre_event_drift_z = _pre_event_drift_z(candles, event_timestamp, pre_event_ret_4h)
    priced_in_ratio = (
        abs(pre_event_ret_4h) / already_priced_return_threshold
        if pre_event_ret_4h is not None
        else None
    )
    already_priced = bool(
        (pre_event_ret_4h is not None and abs(pre_event_ret_4h) >= already_priced_return_threshold)
        or (volume_shock_z is not None and abs(volume_shock_z) >= volume_shock_z_threshold)
    )
    flags = _market_reaction_flags(
        reliability=reliability,
        pre_event_ret_4h=pre_event_ret_4h,
        already_priced=already_priced,
    )
    passed = not flags
    return MarketReactionCheck(
        check_id=_build_check_id(event_id=event.event_id, created_at=created_at),
        event_id=event.event_id,
        symbol=event.symbol,
        created_at=created_at,
        decision_timestamp=created_at,
        event_timestamp_used=event_timestamp,
        pre_event_ret_1h=pre_event_ret_1h,
        pre_event_ret_4h=pre_event_ret_4h,
        pre_event_ret_24h=pre_event_ret_24h,
        post_event_ret_15m=None,
        post_event_ret_1h=post_event_ret_1h,
        pre_event_drift_z=pre_event_drift_z,
        volume_shock_z=volume_shock_z,
        priced_in_ratio=priced_in_ratio,
        already_priced=already_priced,
        passed=passed,
        blocked_reason=flags[0] if flags else None,
        flags=flags,
    )


def _market_reaction_flags(
    *,
    reliability: EventReliabilityCheck | None,
    pre_event_ret_4h: float | None,
    already_priced: bool,
) -> list[str]:
    if reliability is None or not reliability.passed:
        return ["event_reliability_not_passed"]
    flags: list[str] = []
    if pre_event_ret_4h is None:
        flags.append("insufficient_pre_event_coverage")
    if already_priced:
        flags.append("already_priced")
    return flags


def _return_between(candles: list[MarketCandleRecord], start: datetime, end: datetime) -> float | None:
    start_candle = _candle_at(candles, _hour_boundary(start))
    end_candle = _candle_at(candles, _hour_boundary(end))
    if start_candle is None or end_candle is None or start_candle.close == 0:
        return None
    return (end_candle.close / start_candle.close) - 1.0


def _candle_at_or_before(candles: list[MarketCandleRecord], timestamp: datetime) -> MarketCandleRecord | None:
    result = None
    for candle in candles:
        if candle.timestamp <= timestamp:
            result = candle
        else:
            break
    return result


def _candle_at(candles: list[MarketCandleRecord], timestamp: datetime) -> MarketCandleRecord | None:
    for candle in candles:
        if candle.timestamp == timestamp:
            return candle
    return None


def _volume_shock_z(candles: list[MarketCandleRecord], event_timestamp: datetime) -> float | None:
    event_boundary = _hour_boundary(event_timestamp)
    event_candle = _candle_at(candles, event_boundary)
    prior = [
        candle.volume
        for candle in candles
        if event_boundary - timedelta(hours=24) <= candle.timestamp < event_boundary
    ]
    if event_candle is None or len(prior) < 2:
        return None
    mean = sum(prior) / len(prior)
    stdev = _sample_stdev(prior)
    if stdev is None or stdev == 0:
        return None
    return (event_candle.volume - mean) / stdev


def _pre_event_drift_z(
    candles: list[MarketCandleRecord],
    event_timestamp: datetime,
    pre_event_ret_4h: float | None,
) -> float | None:
    if pre_event_ret_4h is None:
        return None
    returns: list[float] = []
    previous = None
    event_boundary = _hour_boundary(event_timestamp)
    for candle in candles:
        if not (event_boundary - timedelta(hours=24) <= candle.timestamp <= event_boundary):
            continue
        if previous is not None and previous.close != 0:
            returns.append((candle.close / previous.close) - 1.0)
        previous = candle
    stdev = _sample_stdev(returns)
    if stdev is None or stdev == 0:
        return None
    return pre_event_ret_4h / stdev


def _hour_boundary(timestamp: datetime) -> datetime:
    return timestamp.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def _sample_stdev(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def _build_check_id(*, event_id: str, created_at: datetime) -> str:
    digest = sha1(
        json.dumps(
            {
                "event_id": event_id,
                "created_at": created_at.isoformat(),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"market-reaction:{digest}"


def _replace_unique(path: Path, payload: dict, *, identity_key: str) -> None:
    rows: list[dict] = []
    replaced = False
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            existing = json.loads(line)
            if existing.get(identity_key) == payload.get(identity_key):
                rows.append(payload)
                replaced = True
            else:
                rows.append(existing)
    if not replaced:
        rows.append(payload)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
