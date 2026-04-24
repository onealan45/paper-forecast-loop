from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from forecast_loop.config import LoopConfig
from forecast_loop.pipeline import ForecastingLoop


@dataclass(slots=True)
class ReplayResult:
    cycles_run: int
    forecasts_created: int
    scores_created: int
    first_cycle_at: datetime
    last_cycle_at: datetime


class ReplayRunner:
    def __init__(self, config: LoopConfig, data_provider, repository) -> None:
        self.loop = ForecastingLoop(config=config, data_provider=data_provider, repository=repository)

    def run_range(self, start: datetime, end: datetime) -> ReplayResult:
        self._require_timezone_aware(start, "start")
        self._require_timezone_aware(end, "end")
        start_utc = start.astimezone(UTC)
        end_utc = end.astimezone(UTC)
        self._validate_range(start_utc, end_utc)

        now = start_utc
        cycles_run = 0
        forecasts_created = 0
        scores_created = 0

        while now <= end_utc:
            forecasts_before = len(self.loop.repository.load_forecasts())
            result = self.loop.run_cycle(now=now)
            forecasts_after = len(self.loop.repository.load_forecasts())
            cycles_run += 1
            forecasts_created += max(0, forecasts_after - forecasts_before)
            scores_created += len(result.scores)
            now += timedelta(hours=1)

        return ReplayResult(
            cycles_run=cycles_run,
            forecasts_created=forecasts_created,
            scores_created=scores_created,
            first_cycle_at=start_utc,
            last_cycle_at=end_utc,
        )

    def _validate_range(self, start: datetime, end: datetime) -> None:
        if start > end:
            raise ValueError("replay range start must be <= end")

        if not self._is_hour_aligned(start) or not self._is_hour_aligned(end):
            raise ValueError("replay range must use hour-aligned UTC boundaries")

    def _require_timezone_aware(self, value: datetime, label: str) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"replay range {label} must be timezone-aware")

    def _is_hour_aligned(self, value: datetime) -> bool:
        return value == value.replace(minute=0, second=0, microsecond=0)
