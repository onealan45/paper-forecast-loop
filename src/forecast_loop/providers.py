from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import json
from typing import Callable
from urllib.request import urlopen

from forecast_loop.models import MarketCandle


HOURLY_INTERVAL = timedelta(hours=1)


def align_to_hour_boundary(timestamp: datetime) -> datetime:
    utc_timestamp = timestamp.astimezone(UTC)
    return utc_timestamp.replace(minute=0, second=0, microsecond=0)


def _normalize_hourly_candles(candles: list[MarketCandle]) -> list[MarketCandle]:
    candles_by_boundary: dict[datetime, MarketCandle] = {}
    for candle in candles:
        boundary = align_to_hour_boundary(candle.timestamp)
        candles_by_boundary[boundary] = MarketCandle(
            timestamp=boundary,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
        )
    return [candles_by_boundary[key] for key in sorted(candles_by_boundary)]


@dataclass(slots=True)
class InMemoryMarketDataProvider:
    candles_by_symbol: dict[str, list[MarketCandle]]
    candle_interval_minutes: int = 60

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
        return _normalize_hourly_candles(self.candles_by_symbol.get(symbol, []))


def build_sample_provider(now: datetime, symbol: str) -> InMemoryMarketDataProvider:
    anchor = align_to_hour_boundary(now)
    candles = []
    for hour in range(48):
        timestamp = anchor - timedelta(hours=47 - hour)
        baseline = 100 + (hour * 0.8)
        candles.append(
            MarketCandle(
                timestamp=timestamp,
                open=baseline - 0.4,
                high=baseline + 0.6,
                low=baseline - 0.8,
                close=baseline,
                volume=1_000 + (hour * 10),
            )
        )
    return InMemoryMarketDataProvider({symbol: candles})


@dataclass(slots=True)
class CoinGeckoMarketDataProvider:
    days: int = 7
    http_get: Callable[[str], dict] | None = None
    candle_interval_minutes: int = 60
    _cache: dict[str, list[MarketCandle]] = field(init=False, default_factory=dict)

    SYMBOL_MAP = {
        "BTC-USD": "bitcoin",
        "ETH-USD": "ethereum",
    }

    def __post_init__(self) -> None:
        self._cache = {}

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
        if symbol in self._cache:
            return self._cache[symbol]

        coin_id = self.SYMBOL_MAP[symbol]
        url = (
            f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
            f"?vs_currency=usd&days={self.days}&interval=hourly"
        )
        payload = self._fetch_json(url)
        volume_by_timestamp = {
            int(item[0]): float(item[1])
            for item in payload.get("total_volumes", [])
        }
        raw_candles = [
            MarketCandle(
                timestamp=datetime.fromtimestamp(int(price_point[0]) / 1000, tz=UTC),
                open=float(price_point[1]),
                high=float(price_point[1]),
                low=float(price_point[1]),
                close=float(price_point[1]),
                volume=volume_by_timestamp.get(int(price_point[0]), 0.0),
            )
            for price_point in payload.get("prices", [])
        ]
        self._cache[symbol] = _normalize_hourly_candles(raw_candles)
        return self._cache[symbol]

    def _fetch_json(self, url: str) -> dict:
        if self.http_get is not None:
            return self.http_get(url)

        with urlopen(url, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
