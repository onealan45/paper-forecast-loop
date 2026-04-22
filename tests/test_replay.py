from datetime import UTC, datetime, timedelta

from forecast_loop.config import LoopConfig
from forecast_loop.providers import InMemoryMarketDataProvider
from forecast_loop.replay import ReplayRunner
from forecast_loop.storage import JsonFileRepository


def make_hourly_candles(start: datetime, count: int, *, start_price: float = 100.0, step: float = 1.0):
    from forecast_loop.models import MarketCandle

    return [
        MarketCandle(
            timestamp=start + timedelta(hours=index),
            open=start_price + (index * step),
            high=start_price + (index * step) + 0.5,
            low=start_price + (index * step) - 0.5,
            close=start_price + (index * step),
            volume=1_000 + index,
        )
        for index in range(count)
    ]


def test_replay_runner_advances_hourly_and_reuses_existing_contract(tmp_path):
    provider = InMemoryMarketDataProvider(
        {
            "BTC-USD": make_hourly_candles(
                datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
                12,
                start_price=100,
                step=2,
            )
        }
    )
    repository = JsonFileRepository(tmp_path)
    runner = ReplayRunner(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=2, lookback_candles=3),
        data_provider=provider,
        repository=repository,
    )

    result = runner.run_range(
        start=datetime(2026, 4, 21, 4, 0, tzinfo=UTC),
        end=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
    )

    assert result.cycles_run == 5
    assert result.forecasts_created == 5
    assert result.scores_created == 3
    assert result.first_cycle_at == datetime(2026, 4, 21, 4, 0, tzinfo=UTC)
    assert result.last_cycle_at == datetime(2026, 4, 21, 8, 0, tzinfo=UTC)


def test_replay_runner_counts_only_actual_forecast_inserts_on_rerun(tmp_path):
    provider = InMemoryMarketDataProvider(
        {
            "BTC-USD": make_hourly_candles(
                datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
                12,
                start_price=100,
                step=2,
            )
        }
    )
    repository = JsonFileRepository(tmp_path)
    runner = ReplayRunner(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=2, lookback_candles=3),
        data_provider=provider,
        repository=repository,
    )

    first_run = runner.run_range(
        start=datetime(2026, 4, 21, 4, 0, tzinfo=UTC),
        end=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
    )
    second_run = runner.run_range(
        start=datetime(2026, 4, 21, 4, 0, tzinfo=UTC),
        end=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
    )

    assert first_run.forecasts_created == 5
    assert second_run.cycles_run == 5
    assert second_run.forecasts_created == 0
    assert len(repository.load_forecasts()) == 5


def test_replay_runner_rejects_non_hour_aligned_input_range(tmp_path):
    provider = InMemoryMarketDataProvider(
        {
            "BTC-USD": make_hourly_candles(
                datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
                12,
                start_price=100,
                step=2,
            )
        }
    )
    runner = ReplayRunner(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=2, lookback_candles=3),
        data_provider=provider,
        repository=JsonFileRepository(tmp_path),
    )

    try:
        runner.run_range(
            start=datetime(2026, 4, 21, 4, 30, tzinfo=UTC),
            end=datetime(2026, 4, 21, 8, 15, tzinfo=UTC),
        )
    except ValueError as exc:
        assert "hour-aligned" in str(exc)
    else:
        raise AssertionError("expected ValueError for non-hour-aligned replay range")


def test_replay_runner_rejects_reversed_input_range(tmp_path):
    provider = InMemoryMarketDataProvider(
        {
            "BTC-USD": make_hourly_candles(
                datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
                12,
                start_price=100,
                step=2,
            )
        }
    )
    runner = ReplayRunner(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=2, lookback_candles=3),
        data_provider=provider,
        repository=JsonFileRepository(tmp_path),
    )

    try:
        runner.run_range(
            start=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
            end=datetime(2026, 4, 21, 4, 0, tzinfo=UTC),
        )
    except ValueError as exc:
        assert "start" in str(exc)
    else:
        raise AssertionError("expected ValueError for reversed replay range")


def test_replay_runner_rejects_naive_input_datetimes(tmp_path):
    provider = InMemoryMarketDataProvider(
        {
            "BTC-USD": make_hourly_candles(
                datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
                12,
                start_price=100,
                step=2,
            )
        }
    )
    runner = ReplayRunner(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=2, lookback_candles=3),
        data_provider=provider,
        repository=JsonFileRepository(tmp_path),
    )

    try:
        runner.run_range(
            start=datetime(2026, 4, 21, 4, 0),
            end=datetime(2026, 4, 21, 8, 0),
        )
    except ValueError as exc:
        assert "timezone-aware" in str(exc)
    else:
        raise AssertionError("expected ValueError for naive replay datetimes")


def test_replay_runner_stores_exact_expected_hourly_anchors(tmp_path):
    provider = InMemoryMarketDataProvider(
        {
            "BTC-USD": make_hourly_candles(
                datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
                12,
                start_price=100,
                step=2,
            )
        }
    )
    repository = JsonFileRepository(tmp_path)
    runner = ReplayRunner(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=2, lookback_candles=3),
        data_provider=provider,
        repository=repository,
    )

    result = runner.run_range(
        start=datetime(2026, 4, 21, 4, 0, tzinfo=UTC),
        end=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
    )

    assert [forecast.anchor_time for forecast in repository.load_forecasts()] == [
        datetime(2026, 4, 21, 4, 0, tzinfo=UTC),
        datetime(2026, 4, 21, 5, 0, tzinfo=UTC),
        datetime(2026, 4, 21, 6, 0, tzinfo=UTC),
        datetime(2026, 4, 21, 7, 0, tzinfo=UTC),
        datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
    ]
    assert result.first_cycle_at == datetime(2026, 4, 21, 4, 0, tzinfo=UTC)
    assert result.last_cycle_at == datetime(2026, 4, 21, 8, 0, tzinfo=UTC)
