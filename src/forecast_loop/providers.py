from __future__ import annotations

from datetime import UTC, datetime, timedelta
from dataclasses import dataclass, field
import json
from typing import Callable
from urllib.request import urlopen

from forecast_loop.models import MarketCandle


@dataclass(slots=True)
class InMemoryMarketDataProvider:
    candles_by_symbol: dict[str, list[MarketCandle]]

    def get_recent_candles(self, symbol: str, lookback_candles: int, end_time=None) -> list[MarketCandle]:
        candles = self.candles_by_symbol[symbol]
        if end_time is not None:
            candles = [candle for candle in candles if candle.timestamp <= end_time]
        return candles[-lookback_candles:]

    def get_candles_between(self, symbol: str, start, end) -> list[MarketCandle]:
        return [
            candle
            for candle in self.candles_by_symbol[symbol]
            if start <= candle.timestamp <= end
        ]


def build_sample_provider(now: datetime, symbol: str) -> InMemoryMarketDataProvider:
    anchor = now.astimezone(UTC)
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
            candles = [candle for candle in candles if candle.timestamp <= end_time]
        return candles[-lookback_candles:]

    def get_candles_between(self, symbol: str, start, end) -> list[MarketCandle]:
        return [
            candle
            for candle in self._load_candles(symbol)
            if start <= candle.timestamp <= end
        ]

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
        candles = [
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
        self._cache[symbol] = candles
        return candles

    def _fetch_json(self, url: str) -> dict:
        if self.http_get is not None:
            return self.http_get(url)

        with urlopen(url, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
