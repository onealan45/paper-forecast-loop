from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
import math
from pathlib import Path

from forecast_loop.models import MarketCandle, MarketCandleRecord
from forecast_loop.providers import align_to_hour_boundary
from forecast_loop.storage import JsonFileRepository


@dataclass(slots=True)
class CandleImportResult:
    storage_dir: Path
    input_path: Path
    symbol: str
    source: str
    imported_count: int
    skipped_duplicate_count: int
    total_rows: int

    def to_dict(self) -> dict:
        return {
            "storage_dir": str(self.storage_dir.resolve()),
            "input_path": str(self.input_path.resolve()),
            "symbol": self.symbol,
            "source": self.source,
            "imported_count": self.imported_count,
            "skipped_duplicate_count": self.skipped_duplicate_count,
            "total_rows": self.total_rows,
        }


@dataclass(slots=True)
class CandleExportResult:
    storage_dir: Path
    output_path: Path
    symbol: str
    exported_count: int

    def to_dict(self) -> dict:
        return {
            "storage_dir": str(self.storage_dir.resolve()),
            "output_path": str(self.output_path.resolve()),
            "symbol": self.symbol,
            "exported_count": self.exported_count,
        }


@dataclass(slots=True)
class CandleFetchResult:
    storage_dir: Path
    symbol: str
    provider: str
    source: str
    requested_lookback_candles: int
    fetched_count: int
    stored_count: int
    skipped_duplicate_count: int
    latest_candle_timestamp: datetime | None

    def to_dict(self) -> dict:
        return {
            "storage_dir": str(self.storage_dir.resolve()),
            "symbol": self.symbol,
            "provider": self.provider,
            "source": self.source,
            "requested_lookback_candles": self.requested_lookback_candles,
            "fetched_count": self.fetched_count,
            "stored_count": self.stored_count,
            "skipped_duplicate_count": self.skipped_duplicate_count,
            "latest_candle_timestamp": (
                self.latest_candle_timestamp.isoformat()
                if self.latest_candle_timestamp is not None
                else None
            ),
        }


class StoredCandleProvider:
    candle_interval_minutes = 60

    def __init__(self, repository: JsonFileRepository) -> None:
        self.repository = repository

    def get_recent_candles(self, symbol: str, lookback_candles: int, end_time=None) -> list[MarketCandle]:
        candles = self._load_candles(symbol)
        if end_time is not None:
            end_boundary = align_to_hour_boundary(end_time)
            candles = [candle for candle in candles if candle.timestamp <= end_boundary]
        return candles[-lookback_candles:]

    def get_candles_between(self, symbol: str, start, end) -> list[MarketCandle]:
        start_boundary = align_to_hour_boundary(start)
        end_boundary = align_to_hour_boundary(end)
        return [
            candle
            for candle in self._load_candles(symbol)
            if start_boundary <= candle.timestamp <= end_boundary
        ]

    def get_latest_candle_boundary(self, symbol: str, end_time: datetime | None = None) -> datetime | None:
        candles = self.get_recent_candles(symbol, lookback_candles=10_000, end_time=end_time)
        if not candles:
            return None
        return candles[-1].timestamp

    def _load_candles(self, symbol: str) -> list[MarketCandle]:
        records = [
            record
            for record in self.repository.load_market_candles()
            if record.symbol == symbol
        ]
        for record in records:
            _validate_candle_record(record)
        records.sort(key=lambda record: record.timestamp)
        return [record.to_candle() for record in records]


def import_market_candles(
    *,
    storage_dir: Path | str,
    input_path: Path | str,
    symbol: str,
    source: str,
    imported_at: datetime,
) -> CandleImportResult:
    repository = JsonFileRepository(storage_dir)
    input_file = Path(input_path)
    if not input_file.exists():
        raise ValueError(f"candle import input does not exist: {input_file}")
    if imported_at.tzinfo is None or imported_at.utcoffset() is None:
        raise ValueError("imported_at must be timezone-aware")

    existing_records = repository.load_market_candles()
    existing_ids = {record.candle_id for record in existing_records}
    existing_boundaries = {_candle_boundary_key(record) for record in existing_records}
    imported_count = 0
    skipped_duplicate_count = 0
    total_rows = 0
    for line_number, line in enumerate(input_file.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        total_rows += 1
        try:
            payload = json.loads(line)
            record = _record_from_import_payload(
                payload,
                default_symbol=symbol,
                source=source,
                imported_at=imported_at.astimezone(UTC),
            )
            _validate_candle_record(record)
        except Exception as exc:
            raise ValueError(f"{input_file}:{line_number} cannot be imported: {exc}") from exc
        boundary_key = _candle_boundary_key(record)
        if record.candle_id in existing_ids or boundary_key in existing_boundaries:
            skipped_duplicate_count += 1
            continue
        repository.save_market_candle(record)
        existing_ids.add(record.candle_id)
        existing_boundaries.add(boundary_key)
        imported_count += 1

    return CandleImportResult(
        storage_dir=Path(storage_dir),
        input_path=input_file,
        symbol=symbol,
        source=source,
        imported_count=imported_count,
        skipped_duplicate_count=skipped_duplicate_count,
        total_rows=total_rows,
    )


def export_market_candles(
    *,
    storage_dir: Path | str,
    output_path: Path | str,
    symbol: str,
) -> CandleExportResult:
    repository = JsonFileRepository(storage_dir)
    rows = [
        json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True)
        for record in repository.load_market_candles()
        if record.symbol == symbol
    ]
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    return CandleExportResult(
        storage_dir=Path(storage_dir),
        output_path=output_file,
        symbol=symbol,
        exported_count=len(rows),
    )


def fetch_market_candles(
    *,
    storage_dir: Path | str,
    provider,
    provider_name: str,
    symbol: str,
    lookback_candles: int,
    source: str,
    imported_at: datetime,
    end_time: datetime | None = None,
) -> CandleFetchResult:
    if lookback_candles <= 0:
        raise ValueError("fetch-candles lookback-candles must be greater than 0")
    if imported_at.tzinfo is None or imported_at.utcoffset() is None:
        raise ValueError("imported_at must be timezone-aware")

    repository = JsonFileRepository(storage_dir)
    candles = provider.get_recent_candles(
        symbol,
        lookback_candles=lookback_candles,
        end_time=end_time,
    )
    existing_records = repository.load_market_candles()
    existing_ids = {record.candle_id for record in existing_records}
    existing_boundaries = {_candle_boundary_key(record) for record in existing_records}
    stored_count = 0
    skipped_duplicate_count = 0
    latest_candle_timestamp: datetime | None = None

    for candle in candles:
        record = MarketCandleRecord.from_candle(
            candle,
            symbol=symbol,
            source=source,
            imported_at=imported_at.astimezone(UTC),
        )
        _validate_candle_record(record)
        latest_candle_timestamp = record.timestamp.astimezone(UTC)
        boundary_key = _candle_boundary_key(record)
        if record.candle_id in existing_ids or boundary_key in existing_boundaries:
            skipped_duplicate_count += 1
            continue
        repository.save_market_candle(record)
        existing_ids.add(record.candle_id)
        existing_boundaries.add(boundary_key)
        stored_count += 1

    return CandleFetchResult(
        storage_dir=Path(storage_dir),
        symbol=symbol,
        provider=provider_name,
        source=source,
        requested_lookback_candles=lookback_candles,
        fetched_count=len(candles),
        stored_count=stored_count,
        skipped_duplicate_count=skipped_duplicate_count,
        latest_candle_timestamp=latest_candle_timestamp,
    )


def run_candle_health(
    *,
    storage_dir: Path | str,
    symbol: str,
    start: datetime,
    end: datetime,
    interval_minutes: int = 60,
) -> dict:
    if interval_minutes <= 0:
        raise ValueError("candle-health interval-minutes must be greater than 0")
    if interval_minutes != 60:
        raise ValueError("M3C candle-health supports hourly candles only: interval-minutes must be 60")
    storage_path = Path(storage_dir)
    candle_path = storage_path / "market_candles.jsonl"
    findings: list[dict] = []
    if not storage_path.exists() or not storage_path.is_dir():
        return _candle_health_result(
            storage_path=storage_path,
            symbol=symbol,
            start=start,
            end=end,
            candle_count=0,
            findings=[
                {
                    "code": "storage_dir_missing",
                    "severity": "blocking",
                    "message": f"storage directory does not exist: {storage_path}",
                }
            ],
            missing_boundaries=[],
            duplicate_boundaries=[],
        )
    if not candle_path.exists():
        return _candle_health_result(
            storage_path=storage_path,
            symbol=symbol,
            start=start,
            end=end,
            candle_count=0,
            findings=[
                {
                    "code": "market_candles_missing",
                    "severity": "blocking",
                    "message": f"market_candles.jsonl does not exist: {candle_path}",
                }
            ],
            missing_boundaries=[],
            duplicate_boundaries=[],
        )

    records: list[MarketCandleRecord] = []
    seen_boundaries: set[datetime] = set()
    duplicate_boundaries: set[datetime] = set()
    for line_number, line in enumerate(candle_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = MarketCandleRecord.from_dict(json.loads(line))
            _validate_candle_record(record)
        except Exception as exc:
            findings.append(
                {
                    "code": "bad_candle_row",
                    "severity": "blocking",
                    "message": f"market_candles.jsonl:{line_number} cannot be parsed: {exc}",
                }
            )
            continue
        if record.symbol != symbol:
            continue
        boundary = record.timestamp.astimezone(UTC)
        if boundary in seen_boundaries:
            duplicate_boundaries.add(boundary)
        seen_boundaries.add(boundary)
        records.append(record)

    if duplicate_boundaries:
        findings.append(
            {
                "code": "duplicate_candle_timestamp",
                "severity": "blocking",
                "message": f"{len(duplicate_boundaries)} duplicate candle timestamp(s) for {symbol}.",
            }
        )

    expected = _expected_boundaries(start=start, end=end, interval_minutes=interval_minutes)
    observed = {record.timestamp.astimezone(UTC) for record in records}
    missing_boundaries = [boundary for boundary in expected if boundary not in observed]
    if missing_boundaries:
        findings.append(
            {
                "code": "missing_candle_timestamp",
                "severity": "blocking",
                "message": f"{len(missing_boundaries)} expected candle timestamp(s) are missing for {symbol}.",
            }
        )

    return _candle_health_result(
        storage_path=storage_path,
        symbol=symbol,
        start=start,
        end=end,
        candle_count=len(records),
        findings=findings,
        missing_boundaries=missing_boundaries,
        duplicate_boundaries=sorted(duplicate_boundaries),
    )


def _record_from_import_payload(
    payload: dict,
    *,
    default_symbol: str,
    source: str,
    imported_at: datetime,
) -> MarketCandleRecord:
    if "candle_id" in payload:
        return MarketCandleRecord.from_dict(payload)
    symbol = payload.get("symbol") or default_symbol
    timestamp = _parse_required_datetime(payload.get("timestamp"), "timestamp")
    candle = MarketCandle(
        timestamp=timestamp,
        open=float(payload["open"]),
        high=float(payload["high"]),
        low=float(payload["low"]),
        close=float(payload["close"]),
        volume=float(payload["volume"]),
    )
    record = MarketCandleRecord.from_candle(
        candle,
        symbol=symbol,
        source=source,
        imported_at=imported_at,
    )
    adjusted_close = payload.get("adjusted_close")
    if adjusted_close is not None:
        record.adjusted_close = float(adjusted_close)
    return record


def _parse_required_datetime(value: str | None, label: str) -> datetime:
    if value is None:
        raise ValueError(f"missing required datetime field: {label}")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"datetime field must include timezone: {label}")
    return parsed.astimezone(UTC)


def _expected_boundaries(*, start: datetime, end: datetime, interval_minutes: int) -> list[datetime]:
    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be greater than 0")
    if interval_minutes != 60:
        raise ValueError("M3C supports hourly candles only")
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("candle-health start must be timezone-aware")
    if end.tzinfo is None or end.utcoffset() is None:
        raise ValueError("candle-health end must be timezone-aware")
    start_utc = start.astimezone(UTC)
    end_utc = end.astimezone(UTC)
    if start_utc != align_to_hour_boundary(start_utc):
        raise ValueError("candle-health start must be hour-aligned")
    if end_utc != align_to_hour_boundary(end_utc):
        raise ValueError("candle-health end must be hour-aligned")
    if start_utc > end_utc:
        raise ValueError("candle-health start must be <= end")
    interval = timedelta(minutes=interval_minutes)
    boundaries: list[datetime] = []
    current = start_utc
    while current <= end_utc:
        boundaries.append(current)
        current += interval
    return boundaries


def _validate_candle_record(record: MarketCandleRecord) -> None:
    timestamp = record.timestamp.astimezone(UTC)
    if timestamp != align_to_hour_boundary(timestamp):
        raise ValueError(f"candle timestamp must be hour-aligned: {record.timestamp.isoformat()}")
    values = {
        "open": record.open,
        "high": record.high,
        "low": record.low,
        "close": record.close,
        "volume": record.volume,
    }
    for label, value in values.items():
        if not math.isfinite(value):
            raise ValueError(f"candle {label} must be finite")
    if record.adjusted_close is not None and not math.isfinite(record.adjusted_close):
        raise ValueError("candle adjusted_close must be finite")
    if record.high < max(record.open, record.close, record.low):
        raise ValueError("candle high must be >= open, close, and low")
    if record.low > min(record.open, record.close, record.high):
        raise ValueError("candle low must be <= open, close, and high")
    if record.volume < 0:
        raise ValueError("candle volume must be non-negative")


def _candle_boundary_key(record: MarketCandleRecord) -> tuple[str, datetime]:
    return (record.symbol, record.timestamp.astimezone(UTC))


def _candle_health_result(
    *,
    storage_path: Path,
    symbol: str,
    start: datetime,
    end: datetime,
    candle_count: int,
    findings: list[dict],
    missing_boundaries: list[datetime],
    duplicate_boundaries: list[datetime],
) -> dict:
    status = "healthy" if not findings else "unhealthy"
    return {
        "status": status,
        "severity": "none" if status == "healthy" else "blocking",
        "repair_required": status != "healthy",
        "storage_dir": str(storage_path.resolve()),
        "symbol": symbol,
        "start": start.astimezone(UTC).isoformat(),
        "end": end.astimezone(UTC).isoformat(),
        "candle_count": candle_count,
        "missing_count": len(missing_boundaries),
        "duplicate_count": len(duplicate_boundaries),
        "missing_timestamps": [boundary.isoformat() for boundary in missing_boundaries],
        "duplicate_timestamps": [boundary.isoformat() for boundary in duplicate_boundaries],
        "findings": findings,
    }
