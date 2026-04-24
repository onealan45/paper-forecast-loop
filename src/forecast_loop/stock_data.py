from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import csv
import json
import math
from pathlib import Path

from forecast_loop.market_calendar import (
    is_us_equity_trading_day,
    us_equity_close_utc,
    us_equity_sessions,
)
from forecast_loop.models import MarketCandle, MarketCandleRecord
from forecast_loop.storage import JsonFileRepository


US_ETF_FIXTURE_SYMBOLS = {"SPY", "QQQ", "TLT", "GLD"}


@dataclass(slots=True)
class StockCsvImportResult:
    storage_dir: Path
    input_path: Path
    symbol: str
    source: str
    imported_count: int
    skipped_duplicate_count: int
    skipped_non_trading_day_count: int
    total_rows: int

    def to_dict(self) -> dict:
        return {
            "storage_dir": str(self.storage_dir.resolve()),
            "input_path": str(self.input_path.resolve()),
            "symbol": self.symbol,
            "source": self.source,
            "imported_count": self.imported_count,
            "skipped_duplicate_count": self.skipped_duplicate_count,
            "skipped_non_trading_day_count": self.skipped_non_trading_day_count,
            "total_rows": self.total_rows,
        }


class StockCsvFixtureProvider:
    candle_interval_minutes = 1440

    def __init__(self, csv_path: Path | str, *, symbol: str) -> None:
        self.csv_path = Path(csv_path)
        self.symbol = symbol.upper()

    def get_recent_candles(self, symbol: str, lookback_candles: int, end_time=None) -> list[MarketCandle]:
        candles = self._load_candles(symbol)
        if end_time is not None:
            end_utc = end_time.astimezone(UTC)
            candles = [candle for candle in candles if candle.timestamp <= end_utc]
        return candles[-lookback_candles:]

    def get_candles_between(self, symbol: str, start, end) -> list[MarketCandle]:
        start_utc = start.astimezone(UTC)
        end_utc = end.astimezone(UTC)
        return [
            candle
            for candle in self._load_candles(symbol)
            if start_utc <= candle.timestamp <= end_utc
        ]

    def get_latest_candle_boundary(self, symbol: str, end_time: datetime | None = None) -> datetime | None:
        candles = self.get_recent_candles(symbol, lookback_candles=10_000, end_time=end_time)
        if not candles:
            return None
        return candles[-1].timestamp

    def _load_candles(self, symbol: str) -> list[MarketCandle]:
        if symbol.upper() != self.symbol:
            return []
        rows = _read_stock_csv_rows(self.csv_path)
        records = [
            _record_from_stock_csv_row(
                row,
                symbol=self.symbol,
                source=f"csv-fixture:{self.csv_path.name}",
                imported_at=datetime.now(tz=UTC),
            )
            for row in rows
            if is_us_equity_trading_day(date.fromisoformat(row["date"]))
        ]
        for record in records:
            _validate_stock_candle_record(record)
        records.sort(key=lambda record: record.timestamp)
        return [record.to_candle() for record in records]


def import_stock_csv(
    *,
    storage_dir: Path | str,
    input_path: Path | str,
    symbol: str,
    source: str,
    imported_at: datetime,
) -> StockCsvImportResult:
    normalized_symbol = _require_us_etf_symbol(symbol)
    if imported_at.tzinfo is None or imported_at.utcoffset() is None:
        raise ValueError("imported_at must be timezone-aware")
    input_file = Path(input_path)
    rows = _read_stock_csv_rows(input_file)
    repository = JsonFileRepository(storage_dir)
    existing_ids = {record.candle_id for record in repository.load_market_candles()}
    imported_count = 0
    skipped_duplicate_count = 0
    skipped_non_trading_day_count = 0

    for line_number, row in enumerate(rows, start=2):
        trading_date = _parse_row_date(row)
        if not is_us_equity_trading_day(trading_date):
            skipped_non_trading_day_count += 1
            continue
        try:
            record = _record_from_stock_csv_row(
                row,
                symbol=normalized_symbol,
                source=source,
                imported_at=imported_at.astimezone(UTC),
            )
            _validate_stock_candle_record(record)
        except Exception as exc:
            raise ValueError(f"{input_file}:{line_number} cannot be imported: {exc}") from exc
        if record.candle_id in existing_ids:
            skipped_duplicate_count += 1
            continue
        repository.save_market_candle(record)
        existing_ids.add(record.candle_id)
        imported_count += 1

    return StockCsvImportResult(
        storage_dir=Path(storage_dir),
        input_path=input_file,
        symbol=normalized_symbol,
        source=source,
        imported_count=imported_count,
        skipped_duplicate_count=skipped_duplicate_count,
        skipped_non_trading_day_count=skipped_non_trading_day_count,
        total_rows=len(rows),
    )


def run_stock_candle_health(
    *,
    storage_dir: Path | str,
    symbol: str,
    start_date: date,
    end_date: date,
) -> dict:
    normalized_symbol = _require_us_etf_symbol(symbol)
    storage_path = Path(storage_dir)
    candle_path = storage_path / "market_candles.jsonl"
    findings: list[dict] = []
    if not storage_path.exists() or not storage_path.is_dir():
        return _stock_health_result(
            storage_path=storage_path,
            symbol=normalized_symbol,
            start_date=start_date,
            end_date=end_date,
            candle_count=0,
            findings=[
                {
                    "code": "storage_dir_missing",
                    "severity": "blocking",
                    "message": f"storage directory does not exist: {storage_path}",
                }
            ],
            missing_sessions=[],
            duplicate_sessions=[],
        )
    if not candle_path.exists():
        return _stock_health_result(
            storage_path=storage_path,
            symbol=normalized_symbol,
            start_date=start_date,
            end_date=end_date,
            candle_count=0,
            findings=[
                {
                    "code": "market_candles_missing",
                    "severity": "blocking",
                    "message": f"market_candles.jsonl does not exist: {candle_path}",
                }
            ],
            missing_sessions=[],
            duplicate_sessions=[],
        )

    records: list[MarketCandleRecord] = []
    seen_sessions: set[datetime] = set()
    duplicate_sessions: set[datetime] = set()
    for line_number, line in enumerate(candle_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = MarketCandleRecord.from_dict(json.loads(line))
            _validate_stock_candle_record(record)
        except Exception as exc:
            findings.append(
                {
                    "code": "bad_candle_row",
                    "severity": "blocking",
                    "message": f"market_candles.jsonl:{line_number} cannot be parsed: {exc}",
                }
            )
            continue
        if record.symbol != normalized_symbol:
            continue
        if record.adjusted_close is None:
            findings.append(
                {
                    "code": "missing_adjusted_close",
                    "severity": "blocking",
                    "message": f"market_candles.jsonl:{line_number} is missing adjusted_close for {normalized_symbol}.",
                }
            )
            continue
        session_close = record.timestamp.astimezone(UTC)
        if session_close in seen_sessions:
            duplicate_sessions.add(session_close)
        seen_sessions.add(session_close)
        records.append(record)

    if duplicate_sessions:
        findings.append(
            {
                "code": "duplicate_stock_session",
                "severity": "blocking",
                "message": f"{len(duplicate_sessions)} duplicate session(s) for {normalized_symbol}.",
            }
        )

    expected_sessions = us_equity_sessions(start_date, end_date)
    expected_closes = [session.close_utc for session in expected_sessions]
    observed = {record.timestamp.astimezone(UTC) for record in records}
    missing_sessions = [close_utc for close_utc in expected_closes if close_utc not in observed]
    if missing_sessions:
        findings.append(
            {
                "code": "missing_stock_session",
                "severity": "blocking",
                "message": f"{len(missing_sessions)} expected trading session(s) are missing for {normalized_symbol}.",
            }
        )

    return _stock_health_result(
        storage_path=storage_path,
        symbol=normalized_symbol,
        start_date=start_date,
        end_date=end_date,
        candle_count=len(records),
        findings=findings,
        missing_sessions=missing_sessions,
        duplicate_sessions=sorted(duplicate_sessions),
    )


def market_calendar_payload(*, market: str, start_date: date, end_date: date) -> dict:
    if market.upper() != "US":
        raise ValueError("M3D market-calendar supports US only")
    sessions = us_equity_sessions(start_date, end_date)
    return {
        "market": "US",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "timezone": "America/New_York",
        "session_count": len(sessions),
        "sessions": [session.to_dict() for session in sessions],
    }


def _record_from_stock_csv_row(
    row: dict[str, str],
    *,
    symbol: str,
    source: str,
    imported_at: datetime,
) -> MarketCandleRecord:
    trading_date = _parse_row_date(row)
    close_utc = us_equity_close_utc(trading_date)
    adjusted_close = float(row["adjusted_close"])
    candle = MarketCandle(
        timestamp=close_utc,
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        volume=float(row["volume"]),
    )
    record = MarketCandleRecord.from_candle(
        candle,
        symbol=symbol,
        source=source,
        imported_at=imported_at,
    )
    record.adjusted_close = adjusted_close
    return record


def _validate_stock_candle_record(record: MarketCandleRecord) -> None:
    values = {
        "open": record.open,
        "high": record.high,
        "low": record.low,
        "close": record.close,
        "volume": record.volume,
    }
    for label, value in values.items():
        if not math.isfinite(value):
            raise ValueError(f"stock candle {label} must be finite")
    if record.adjusted_close is not None and not math.isfinite(record.adjusted_close):
        raise ValueError("stock candle adjusted_close must be finite")
    if record.high < max(record.open, record.close, record.low):
        raise ValueError("stock candle high must be >= open, close, and low")
    if record.low > min(record.open, record.close, record.high):
        raise ValueError("stock candle low must be <= open, close, and high")
    if record.volume < 0:
        raise ValueError("stock candle volume must be non-negative")


def _read_stock_csv_rows(input_path: Path) -> list[dict[str, str]]:
    if not input_path.exists():
        raise ValueError(f"stock CSV input does not exist: {input_path}")
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required_columns = {"date", "open", "high", "low", "close", "adjusted_close", "volume"}
    if not rows:
        return []
    missing = required_columns.difference(rows[0])
    if missing:
        raise ValueError(f"stock CSV is missing required columns: {', '.join(sorted(missing))}")
    return rows


def _parse_row_date(row: dict[str, str]) -> date:
    try:
        return date.fromisoformat(row["date"])
    except Exception as exc:
        raise ValueError(f"invalid stock CSV date: {row.get('date')}") from exc


def _require_us_etf_symbol(symbol: str) -> str:
    normalized = symbol.upper()
    if normalized not in US_ETF_FIXTURE_SYMBOLS:
        raise ValueError(f"M3D stock CSV prototype supports: {', '.join(sorted(US_ETF_FIXTURE_SYMBOLS))}")
    return normalized


def _stock_health_result(
    *,
    storage_path: Path,
    symbol: str,
    start_date: date,
    end_date: date,
    candle_count: int,
    findings: list[dict],
    missing_sessions: list[datetime],
    duplicate_sessions: list[datetime],
) -> dict:
    status = "healthy" if not findings else "unhealthy"
    return {
        "status": status,
        "severity": "none" if status == "healthy" else "blocking",
        "repair_required": status != "healthy",
        "storage_dir": str(storage_path.resolve()),
        "symbol": symbol,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "candle_count": candle_count,
        "missing_session_count": len(missing_sessions),
        "duplicate_session_count": len(duplicate_sessions),
        "missing_session_closes_utc": [value.isoformat() for value in missing_sessions],
        "duplicate_session_closes_utc": [value.isoformat() for value in duplicate_sessions],
        "findings": findings,
    }
