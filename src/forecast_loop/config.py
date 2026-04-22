from dataclasses import dataclass


@dataclass(slots=True)
class LoopConfig:
    symbol: str
    horizon_hours: int = 24
    lookback_candles: int = 8
