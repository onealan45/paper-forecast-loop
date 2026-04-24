from datetime import UTC, datetime, timedelta
import json

from forecast_loop.cli import main
from forecast_loop.config import LoopConfig
from forecast_loop.models import Forecast, MarketCandle
from forecast_loop.pipeline import ForecastingLoop
from forecast_loop.providers import CoinGeckoMarketDataProvider, InMemoryMarketDataProvider
from forecast_loop.storage import JsonFileRepository


def make_hourly_candles(start: datetime, count: int, *, start_price: float = 100.0, step: float = 1.0) -> list[MarketCandle]:
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


def make_forecast(
    *,
    forecast_id: str,
    anchor_time: datetime,
    target_hours: int,
    predicted_regime: str = "trend_up",
    status: str = "pending",
    status_reason: str = "awaiting_horizon_end",
    provider_data_through: datetime | None = None,
    observed_candle_count: int = 0,
) -> Forecast:
    target_window_start = anchor_time
    target_window_end = anchor_time + timedelta(hours=target_hours)
    return Forecast(
        forecast_id=forecast_id,
        symbol="BTC-USD",
        created_at=anchor_time + timedelta(minutes=5),
        anchor_time=anchor_time,
        target_window_start=target_window_start,
        target_window_end=target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=target_hours + 1,
        status=status,
        status_reason=status_reason,
        predicted_regime=predicted_regime,
        confidence=0.82,
        provider_data_through=provider_data_through,
        observed_candle_count=observed_candle_count,
    )


def test_run_cycle_aligns_forecast_to_latest_available_hourly_boundary(tmp_path):
    now = datetime(2026, 4, 21, 12, 37, tzinfo=UTC)
    provider = InMemoryMarketDataProvider(
        {"BTC-USD": make_hourly_candles(datetime(2026, 4, 21, 4, 0, tzinfo=UTC), 8)}
    )
    repository = JsonFileRepository(tmp_path)
    loop = ForecastingLoop(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=4, lookback_candles=4),
        data_provider=provider,
        repository=repository,
    )

    result = loop.run_cycle(now=now)

    assert result.new_forecast is not None
    assert result.new_forecast.anchor_time == datetime(2026, 4, 21, 11, 0, tzinfo=UTC)
    assert result.new_forecast.target_window_start == datetime(2026, 4, 21, 11, 0, tzinfo=UTC)
    assert result.new_forecast.target_window_end == datetime(2026, 4, 21, 15, 0, tzinfo=UTC)
    assert result.new_forecast.candle_interval_minutes == 60
    assert result.new_forecast.expected_candle_count == 5
    assert result.new_forecast.status == "pending"
    assert result.new_forecast.status_reason == "awaiting_horizon_end"
    assert result.new_forecast.provider_data_through == datetime(2026, 4, 21, 11, 0, tzinfo=UTC)
    assert result.new_forecast.observed_candle_count == 1


def test_run_cycle_keeps_matured_forecast_waiting_when_provider_coverage_is_incomplete(tmp_path):
    now = datetime(2026, 4, 21, 15, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_forecast(
        make_forecast(
            forecast_id="fc-waiting",
            anchor_time=datetime(2026, 4, 21, 10, 0, tzinfo=UTC),
            target_hours=4,
        )
    )
    provider = InMemoryMarketDataProvider(
        {"BTC-USD": make_hourly_candles(datetime(2026, 4, 21, 10, 0, tzinfo=UTC), 4)}
    )
    loop = ForecastingLoop(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=4, lookback_candles=4),
        data_provider=provider,
        repository=repository,
    )

    result = loop.run_cycle(now=now)

    stored_forecast = next(item for item in repository.load_forecasts() if item.forecast_id == "fc-waiting")
    assert stored_forecast.status == "waiting_for_data"
    assert stored_forecast.status_reason == "awaiting_provider_coverage"
    assert stored_forecast.provider_data_through == datetime(2026, 4, 21, 13, 0, tzinfo=UTC)
    assert stored_forecast.observed_candle_count == 4
    assert result.scores == []
    assert repository.load_scores() == []
    assert repository.load_reviews() == []
    assert repository.load_proposals() == []


def test_run_cycle_marks_forecast_unscorable_when_hourly_boundaries_are_missing(tmp_path):
    now = datetime(2026, 4, 21, 15, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_forecast(
        make_forecast(
            forecast_id="fc-unscorable",
            anchor_time=datetime(2026, 4, 21, 10, 0, tzinfo=UTC),
            target_hours=4,
        )
    )
    provider = InMemoryMarketDataProvider(
        {
            "BTC-USD": [
                make_hourly_candles(datetime(2026, 4, 21, 10, 0, tzinfo=UTC), 1)[0],
                make_hourly_candles(datetime(2026, 4, 21, 12, 0, tzinfo=UTC), 1)[0],
                make_hourly_candles(datetime(2026, 4, 21, 14, 0, tzinfo=UTC), 1)[0],
            ]
        }
    )
    loop = ForecastingLoop(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=4, lookback_candles=2),
        data_provider=provider,
        repository=repository,
    )

    result = loop.run_cycle(now=now)

    stored_forecast = next(item for item in repository.load_forecasts() if item.forecast_id == "fc-unscorable")
    assert stored_forecast.status == "unscorable"
    assert stored_forecast.status_reason == "missing_expected_candles"
    assert stored_forecast.provider_data_through == datetime(2026, 4, 21, 14, 0, tzinfo=UTC)
    assert stored_forecast.observed_candle_count == 3
    assert result.scores == []
    assert repository.load_scores() == []
    assert repository.load_reviews() == []
    assert repository.load_proposals() == []


def test_run_cycle_is_idempotent_for_scoring_review_and_forecast_creation(tmp_path):
    now = datetime(2026, 4, 21, 15, 10, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_forecast(
        make_forecast(
            forecast_id="fc-resolvable",
            anchor_time=datetime(2026, 4, 21, 10, 0, tzinfo=UTC),
            target_hours=4,
            predicted_regime="trend_up",
        )
    )
    provider = InMemoryMarketDataProvider(
        {"BTC-USD": make_hourly_candles(datetime(2026, 4, 21, 10, 0, tzinfo=UTC), 5)}
    )
    loop = ForecastingLoop(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=4, lookback_candles=4),
        data_provider=provider,
        repository=repository,
    )

    first_result = loop.run_cycle(now=now)
    second_result = loop.run_cycle(now=now)

    assert len(first_result.scores) == 1
    assert second_result.scores == []
    assert len(repository.load_scores()) == 1
    assert len(repository.load_reviews()) == 1
    assert len(repository.load_proposals()) == 0
    assert len(repository.load_forecasts()) == 2


def test_review_and_proposal_use_only_valid_scores(tmp_path):
    now = datetime(2026, 4, 21, 15, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_forecast(
        make_forecast(
            forecast_id="fc-valid",
            anchor_time=datetime(2026, 4, 21, 10, 0, tzinfo=UTC),
            target_hours=4,
            predicted_regime="trend_up",
        )
    )
    repository.save_forecast(
        make_forecast(
            forecast_id="fc-invalid",
            anchor_time=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
            target_hours=4,
            predicted_regime="trend_up",
        )
    )
    provider = InMemoryMarketDataProvider(
        {
            "BTC-USD": [
                *make_hourly_candles(datetime(2026, 4, 21, 10, 0, tzinfo=UTC), 5, step=-2),
            ]
        }
    )
    loop = ForecastingLoop(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=4, lookback_candles=4),
        data_provider=provider,
        repository=repository,
    )

    result = loop.run_cycle(now=now)

    assert len(result.scores) == 1
    stored_review = repository.load_reviews()[0]
    stored_proposal = repository.load_proposals()[0]
    assert stored_review.forecast_ids == ["fc-valid"]
    assert stored_review.score_ids == [result.scores[0].score_id]
    assert stored_proposal.review_id == stored_review.review_id
    assert stored_proposal.score_ids == stored_review.score_ids


def test_run_cycle_processes_multiple_matured_forecasts_in_one_batch(tmp_path):
    now = datetime(2026, 4, 21, 15, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_forecast(
        make_forecast(
            forecast_id="fc-a",
            anchor_time=datetime(2026, 4, 21, 10, 0, tzinfo=UTC),
            target_hours=4,
            predicted_regime="trend_down",
        )
    )
    repository.save_forecast(
        make_forecast(
            forecast_id="fc-b",
            anchor_time=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
            target_hours=4,
            predicted_regime="trend_down",
        )
    )
    provider = InMemoryMarketDataProvider(
        {"BTC-USD": make_hourly_candles(datetime(2026, 4, 21, 9, 0, tzinfo=UTC), 7, step=2)}
    )
    loop = ForecastingLoop(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=4, lookback_candles=4),
        data_provider=provider,
        repository=repository,
    )

    result = loop.run_cycle(now=now)

    assert len(result.scores) == 2
    assert {score.forecast_id for score in result.scores} == {"fc-a", "fc-b"}
    stored_review = repository.load_reviews()[0]
    stored_proposal = repository.load_proposals()[0]
    assert set(stored_review.forecast_ids) == {"fc-a", "fc-b"}
    assert set(stored_review.score_ids) == {score.score_id for score in result.scores}
    assert stored_proposal.review_id == stored_review.review_id
    assert set(stored_proposal.score_ids) == set(stored_review.score_ids)


def test_cli_run_once_with_sample_provider_writes_contract_metadata(tmp_path, capsys):
    exit_code = main(
        [
            "run-once",
            "--provider",
            "sample",
            "--symbol",
            "BTC-USD",
            "--storage-dir",
            str(tmp_path),
            "--now",
            "2026-04-21T12:00:00+00:00",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert (tmp_path / "forecasts.jsonl").exists()
    assert (tmp_path / "last_run_meta.json").exists()
    meta = json.loads((tmp_path / "last_run_meta.json").read_text(encoding="utf-8"))
    assert meta["provider"] == "sample"
    assert meta["symbol"] == "BTC-USD"
    assert meta["new_forecast"]["status"] == "pending"
    assert meta["new_forecast"]["target_window_start"] == "2026-04-21T12:00:00+00:00"
    assert meta["new_forecast"]["target_window_end"] == "2026-04-22T12:00:00+00:00"
    assert '"new_forecast_status": "pending"' in captured.out


def test_coingecko_provider_maps_public_prices_to_hourly_boundaries():
    payload = {
        "prices": [
            [1_713_697_200_000, 100.0],
            [1_713_700_800_000, 103.5],
            [1_713_704_400_000, 101.25],
        ],
        "total_volumes": [
            [1_713_697_200_000, 10_000.0],
            [1_713_700_800_000, 12_000.0],
            [1_713_704_400_000, 11_500.0],
        ],
    }
    provider = CoinGeckoMarketDataProvider(http_get=lambda _url: payload)

    candles = provider.get_recent_candles(
        "BTC-USD",
        lookback_candles=2,
        end_time=datetime(2024, 4, 21, 13, 0, tzinfo=UTC),
    )

    assert len(candles) == 2
    assert candles[0].timestamp == datetime(2024, 4, 21, 12, 0, tzinfo=UTC)
    assert candles[1].timestamp == datetime(2024, 4, 21, 13, 0, tzinfo=UTC)
    assert candles[0].close == 103.5
    assert candles[1].close == 101.25
