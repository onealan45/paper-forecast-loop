from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha1
import json
from pathlib import Path

from forecast_loop.models import CanonicalEvent, EventEdgeEvaluation, MarketCandleRecord, MarketReactionCheck
from forecast_loop.storage import JsonFileRepository


@dataclass(slots=True)
class EventEdgeBuildResult:
    storage_dir: Path
    created_at: datetime
    symbol: str | None
    horizon_hours: int
    evaluation_ids: list[str]
    evaluation_count: int

    def to_dict(self) -> dict:
        return {
            "storage_dir": str(self.storage_dir.resolve()),
            "created_at": self.created_at.isoformat(),
            "symbol": self.symbol,
            "horizon_hours": self.horizon_hours,
            "evaluation_ids": self.evaluation_ids,
            "evaluation_count": self.evaluation_count,
        }


@dataclass(slots=True)
class _EdgeSample:
    event: CanonicalEvent
    reaction: MarketReactionCheck
    candle_ids: list[str]
    input_watermark: datetime
    forward_return: float
    benchmark_return: float
    excess_return_after_costs: float
    max_adverse_excursion: float


def build_event_edge_evaluations(
    *,
    storage_dir: Path | str,
    created_at: datetime,
    symbol: str | None = None,
    horizon_hours: int = 24,
    min_sample_size: int = 3,
    estimated_cost_bps: float = 10.0,
) -> EventEdgeBuildResult:
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("created_at must be timezone-aware")
    if horizon_hours <= 0:
        raise ValueError("horizon_hours must be greater than 0")
    if min_sample_size <= 0:
        raise ValueError("min_sample_size must be greater than 0")
    if estimated_cost_bps < 0:
        raise ValueError("estimated_cost_bps must be non-negative")
    created_at_utc = created_at.astimezone(UTC)
    repository = JsonFileRepository(storage_dir)
    events_by_id = {
        event.event_id: event
        for event in repository.load_canonical_events()
        if _event_available(event, created_at=created_at_utc, symbol=symbol)
    }
    reactions = [
        reaction
        for reaction in _latest_reactions_by_event(
            repository.load_market_reaction_checks(),
            created_at=created_at_utc,
        ).values()
        if reaction.passed and reaction.event_id in events_by_id
    ]
    candles_by_symbol = _candles_by_symbol(repository.load_market_candles(), created_at=created_at_utc)
    samples = [
        sample
        for reaction in reactions
        if (
            sample := _sample_from_reaction(
                event=events_by_id[reaction.event_id],
                reaction=reaction,
                candles=candles_by_symbol.get(reaction.symbol, []),
                horizon_hours=horizon_hours,
                estimated_cost_bps=estimated_cost_bps,
            )
        )
        is not None
    ]
    evaluation_ids: list[str] = []
    for group_key, group_samples in _group_samples(samples, horizon_hours=horizon_hours).items():
        evaluation = _evaluation_from_samples(
            group_key=group_key,
            samples=group_samples,
            created_at=created_at_utc,
            horizon_hours=horizon_hours,
            min_sample_size=min_sample_size,
            estimated_cost_bps=estimated_cost_bps,
        )
        _replace_unique(repository.event_edge_evaluations_path, evaluation.to_dict(), identity_key="evaluation_id")
        evaluation_ids.append(evaluation.evaluation_id)

    return EventEdgeBuildResult(
        storage_dir=Path(storage_dir),
        created_at=created_at_utc,
        symbol=symbol,
        horizon_hours=horizon_hours,
        evaluation_ids=evaluation_ids,
        evaluation_count=len(evaluation_ids),
    )


def _event_available(event: CanonicalEvent, *, created_at: datetime, symbol: str | None) -> bool:
    if symbol is not None and event.symbol != symbol:
        return False
    if event.available_at is None or event.available_at > created_at:
        return False
    if event.fetched_at > created_at:
        return False
    if event.created_at is not None and event.created_at > created_at:
        return False
    return True


def _latest_reactions_by_event(
    reactions: list[MarketReactionCheck],
    *,
    created_at: datetime,
) -> dict[str, MarketReactionCheck]:
    latest: dict[str, MarketReactionCheck] = {}
    for reaction in sorted(reactions, key=lambda item: (item.created_at, item.check_id)):
        if reaction.created_at > created_at:
            continue
        latest[reaction.event_id] = reaction
    return latest


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


def _sample_from_reaction(
    *,
    event: CanonicalEvent,
    reaction: MarketReactionCheck,
    candles: list[MarketCandleRecord],
    horizon_hours: int,
    estimated_cost_bps: float,
) -> _EdgeSample | None:
    if reaction.event_timestamp_used != _hour_boundary(reaction.event_timestamp_used):
        return None
    start = reaction.event_timestamp_used
    end = start + timedelta(hours=horizon_hours)
    start_candle = _candle_at(candles, start)
    end_candle = _candle_at(candles, end)
    if start_candle is None or end_candle is None or start_candle.close == 0:
        return None
    window_candles = [candle for candle in candles if start <= candle.timestamp <= end]
    input_times = [
        event.available_at,
        event.fetched_at,
        reaction.created_at,
        *[max(candle.timestamp, candle.imported_at) for candle in window_candles],
    ]
    if event.created_at is not None:
        input_times.append(event.created_at)
    forward_return = (end_candle.close / start_candle.close) - 1.0
    benchmark_return = 0.0
    cost = estimated_cost_bps / 10_000.0
    adverse_returns = [
        (candle.low / start_candle.close) - 1.0
        for candle in window_candles
        if start_candle.close != 0
    ]
    return _EdgeSample(
        event=event,
        reaction=reaction,
        candle_ids=[candle.candle_id for candle in window_candles],
        input_watermark=max(value for value in input_times if value is not None),
        forward_return=forward_return,
        benchmark_return=benchmark_return,
        excess_return_after_costs=forward_return - benchmark_return - cost,
        max_adverse_excursion=min(adverse_returns) if adverse_returns else 0.0,
    )


def _group_samples(
    samples: list[_EdgeSample],
    *,
    horizon_hours: int,
) -> dict[tuple[str, str, str, int], list[_EdgeSample]]:
    groups: dict[tuple[str, str, str, int], list[_EdgeSample]] = {}
    for sample in samples:
        key = (
            sample.event.event_family,
            sample.event.event_type,
            sample.event.symbol,
            horizon_hours,
        )
        groups.setdefault(key, []).append(sample)
    return groups


def _evaluation_from_samples(
    *,
    group_key: tuple[str, str, str, int],
    samples: list[_EdgeSample],
    created_at: datetime,
    horizon_hours: int,
    min_sample_size: int,
    estimated_cost_bps: float,
) -> EventEdgeEvaluation:
    event_family, event_type, symbol, _ = group_key
    forward_returns = [sample.forward_return for sample in samples]
    benchmark_returns = [sample.benchmark_return for sample in samples]
    excess_returns = [sample.excess_return_after_costs for sample in samples]
    adverse_returns = sorted(sample.max_adverse_excursion for sample in samples)
    hit_rate = _average(1.0 if value > 0 else 0.0 for value in excess_returns)
    flags: list[str] = []
    if len(samples) < min_sample_size:
        flags.append("insufficient_sample_size")
    if _average(excess_returns) <= 0:
        flags.append("non_positive_after_cost_edge")
    if hit_rate < 0.5:
        flags.append("low_hit_rate")
    passed = not flags
    return EventEdgeEvaluation(
        evaluation_id=_build_evaluation_id(
            event_family=event_family,
            event_type=event_type,
            symbol=symbol,
            horizon_hours=horizon_hours,
            created_at=created_at,
        ),
        event_family=event_family,
        event_type=event_type,
        symbol=symbol,
        created_at=created_at,
        split="historical_event_sample",
        horizon_hours=horizon_hours,
        sample_n=len(samples),
        average_forward_return=_average(forward_returns),
        average_benchmark_return=_average(benchmark_returns),
        average_excess_return_after_costs=_average(excess_returns),
        hit_rate=hit_rate,
        max_adverse_excursion_p50=_percentile(adverse_returns, 0.5),
        max_adverse_excursion_p90=_percentile(adverse_returns, 0.9),
        max_drawdown_if_traded=min(adverse_returns) if adverse_returns else None,
        turnover=float(len(samples)),
        estimated_cost_bps=estimated_cost_bps,
        dsr=None,
        white_rc_p=None,
        stability_score=None,
        passed=passed,
        blocked_reason=flags[0] if flags else None,
        flags=flags,
        input_event_ids=sorted({sample.event.event_id for sample in samples}),
        input_reaction_check_ids=sorted({sample.reaction.check_id for sample in samples}),
        input_candle_ids=sorted({candle_id for sample in samples for candle_id in sample.candle_ids}),
        input_watermark=max(sample.input_watermark for sample in samples) if samples else None,
    )


def _average(values) -> float:
    numbers = list(values)
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    index = min(len(values) - 1, max(0, round((len(values) - 1) * quantile)))
    return values[index]


def _hour_boundary(timestamp: datetime) -> datetime:
    return timestamp.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def _candle_at(candles: list[MarketCandleRecord], timestamp: datetime) -> MarketCandleRecord | None:
    for candle in candles:
        if candle.timestamp == timestamp:
            return candle
    return None


def _build_evaluation_id(
    *,
    event_family: str,
    event_type: str,
    symbol: str,
    horizon_hours: int,
    created_at: datetime,
) -> str:
    digest = sha1(
        json.dumps(
            {
                "event_family": event_family,
                "event_type": event_type,
                "symbol": symbol,
                "horizon_hours": horizon_hours,
                "created_at": created_at.isoformat(),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"event-edge:{digest}"


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
