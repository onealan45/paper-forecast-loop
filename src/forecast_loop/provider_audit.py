from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from forecast_loop.models import MarketCandle, ProviderRun


SCHEMA_VERSION = "market_candles_v1"


class AuditedMarketDataProvider:
    def __init__(self, *, provider: Any, provider_name: str, repository) -> None:
        self.provider = provider
        self.provider_name = provider_name
        self.repository = repository
        self.candle_interval_minutes = provider.candle_interval_minutes

    def get_recent_candles(self, symbol: str, lookback_candles: int, end_time=None) -> list[MarketCandle]:
        return self._record(
            symbol=symbol,
            operation="get_recent_candles",
            fetch=lambda: self.provider.get_recent_candles(symbol, lookback_candles, end_time=end_time),
        )

    def get_candles_between(self, symbol: str, start, end) -> list[MarketCandle]:
        return self._record(
            symbol=symbol,
            operation="get_candles_between",
            fetch=lambda: self.provider.get_candles_between(symbol, start, end),
        )

    def get_latest_candle_boundary(self, symbol: str, end_time: datetime | None = None) -> datetime | None:
        started_at = datetime.now(tz=UTC)
        try:
            boundary = self.provider.get_latest_candle_boundary(symbol, end_time=end_time)
        except Exception as exc:
            self._save_run(
                symbol=symbol,
                operation="get_latest_candle_boundary",
                started_at=started_at,
                completed_at=datetime.now(tz=UTC),
                status="error",
                candles=[],
                error=exc,
            )
            raise
        self._save_run(
            symbol=symbol,
            operation="get_latest_candle_boundary",
            started_at=started_at,
            completed_at=datetime.now(tz=UTC),
            status="success" if boundary is not None else "empty",
            candles=[],
            data_start=boundary,
            data_end=boundary,
        )
        return boundary

    def _record(self, *, symbol: str, operation: str, fetch) -> list[MarketCandle]:
        started_at = datetime.now(tz=UTC)
        try:
            candles = fetch()
        except Exception as exc:
            self._save_run(
                symbol=symbol,
                operation=operation,
                started_at=started_at,
                completed_at=datetime.now(tz=UTC),
                status="error",
                candles=[],
                error=exc,
            )
            raise
        self._save_run(
            symbol=symbol,
            operation=operation,
            started_at=started_at,
            completed_at=datetime.now(tz=UTC),
            status="success" if candles else "empty",
            candles=candles,
        )
        return candles

    def _save_run(
        self,
        *,
        symbol: str,
        operation: str,
        started_at: datetime,
        completed_at: datetime,
        status: str,
        candles: list[MarketCandle],
        data_start: datetime | None = None,
        data_end: datetime | None = None,
        error: Exception | None = None,
    ) -> None:
        timestamps = [candle.timestamp for candle in candles]
        if timestamps:
            data_start = min(timestamps)
            data_end = max(timestamps)
        provider_run_id = ProviderRun.build_id(
            provider=self.provider_name,
            symbol=symbol,
            operation=operation,
            started_at=started_at,
            completed_at=completed_at,
            status=status,
        )
        self.repository.save_provider_run(
            ProviderRun(
                provider_run_id=provider_run_id,
                created_at=completed_at,
                provider=self.provider_name,
                symbol=symbol,
                operation=operation,
                status=status,
                started_at=started_at,
                completed_at=completed_at,
                candle_count=len(candles),
                data_start=data_start,
                data_end=data_end,
                schema_version=SCHEMA_VERSION,
                error_type=type(error).__name__ if error else None,
                error_message=str(error) if error else None,
            )
        )
