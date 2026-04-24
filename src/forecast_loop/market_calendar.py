from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


US_EQUITY_TIMEZONE = ZoneInfo("America/New_York")
US_EQUITY_CLOSE_TIME = time(16, 0)

# Static prototype set for M3D fixture validation. A later market-calendar
# provider can replace this table without changing the artifact contract.
US_EQUITY_HOLIDAYS_2026 = {
    date(2026, 1, 1),
    date(2026, 1, 19),
    date(2026, 2, 16),
    date(2026, 4, 3),
    date(2026, 5, 25),
    date(2026, 6, 19),
    date(2026, 7, 3),
    date(2026, 9, 7),
    date(2026, 11, 26),
    date(2026, 12, 25),
}


@dataclass(frozen=True, slots=True)
class MarketSession:
    market: str
    trading_date: date
    timezone: str
    close_utc: datetime

    def to_dict(self) -> dict:
        return {
            "market": self.market,
            "trading_date": self.trading_date.isoformat(),
            "timezone": self.timezone,
            "close_utc": self.close_utc.isoformat(),
        }


def is_us_equity_trading_day(trading_date: date) -> bool:
    if trading_date.weekday() >= 5:
        return False
    return trading_date not in US_EQUITY_HOLIDAYS_2026


def us_equity_close_utc(trading_date: date) -> datetime:
    local_close = datetime.combine(
        trading_date,
        US_EQUITY_CLOSE_TIME,
        tzinfo=US_EQUITY_TIMEZONE,
    )
    return local_close.astimezone(UTC)


def us_equity_sessions(start_date: date, end_date: date) -> list[MarketSession]:
    if start_date > end_date:
        raise ValueError("market-calendar start-date must be <= end-date")
    sessions: list[MarketSession] = []
    current = start_date
    while current <= end_date:
        if is_us_equity_trading_day(current):
            sessions.append(
                MarketSession(
                    market="US",
                    trading_date=current,
                    timezone=str(US_EQUITY_TIMEZONE),
                    close_utc=us_equity_close_utc(current),
                )
            )
        current += timedelta(days=1)
    return sessions


def parse_date(value: str, *, label: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid {label} '{value}'. Expected YYYY-MM-DD.") from exc
