from datetime import UTC, datetime, timedelta
import json

from forecast_loop.config import LoopConfig
from forecast_loop.cli import main
from forecast_loop.models import Forecast, MarketCandle
from forecast_loop.pipeline import ForecastingLoop
from forecast_loop.providers import CoinGeckoMarketDataProvider, InMemoryMarketDataProvider
from forecast_loop.storage import JsonFileRepository


def test_run_cycle_records_pending_forecast_for_public_market_snapshot(tmp_path):
    now = datetime(2026, 4, 21, 12, 0, tzinfo=UTC)
    candles = [
        MarketCandle(
            timestamp=now - timedelta(hours=hour),
            open=100 + hour,
            high=101 + hour,
            low=99 + hour,
            close=100 + hour,
            volume=1_000 + hour,
        )
        for hour in range(8, 0, -1)
    ]
    provider = InMemoryMarketDataProvider({"BTC-USD": candles})
    repository = JsonFileRepository(tmp_path)
    loop = ForecastingLoop(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=4),
        data_provider=provider,
        repository=repository,
    )

    result = loop.run_cycle(now=now)

    assert result.new_forecast is not None
    assert result.new_forecast.symbol == "BTC-USD"
    assert result.new_forecast.horizon_end == now + timedelta(hours=4)
    assert result.new_forecast.status == "pending"
    assert result.score is None

    stored_forecasts = repository.load_forecasts()
    assert len(stored_forecasts) == 1
    assert stored_forecasts[0].forecast_id == result.new_forecast.forecast_id


def test_run_cycle_scores_matured_forecast_and_creates_review_and_proposal(tmp_path):
    now = datetime(2026, 4, 21, 12, 0, tzinfo=UTC)
    created_at = now - timedelta(hours=6)
    horizon_end = now - timedelta(hours=2)
    repository = JsonFileRepository(tmp_path)
    repository.save_forecast(
        Forecast(
            forecast_id="fc-matured-1",
            symbol="BTC-USD",
            created_at=created_at,
            horizon_end=horizon_end,
            status="pending",
            predicted_regime="trend_up",
            confidence=0.82,
        )
    )
    candles = [
        MarketCandle(
            timestamp=created_at + timedelta(hours=index),
            open=100 - (index * 4),
            high=101 - (index * 4),
            low=99 - (index * 4),
            close=100 - (index * 4),
            volume=2_000 + index,
        )
        for index in range(7)
    ]
    provider = InMemoryMarketDataProvider({"BTC-USD": candles})
    loop = ForecastingLoop(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=4),
        data_provider=provider,
        repository=repository,
    )

    result = loop.run_cycle(now=now)

    stored_forecasts = repository.load_forecasts()
    resolved_forecast = next(item for item in stored_forecasts if item.forecast_id == "fc-matured-1")
    assert resolved_forecast.status == "resolved"

    stored_scores = repository.load_scores()
    assert len(stored_scores) == 1
    assert stored_scores[0].forecast_id == "fc-matured-1"
    assert stored_scores[0].actual_regime == "volatile_bear"
    assert stored_scores[0].score == 0.0

    stored_reviews = repository.load_reviews()
    assert len(stored_reviews) == 1
    assert stored_reviews[0].average_score == 0.0
    assert "below threshold" in stored_reviews[0].summary

    stored_proposals = repository.load_proposals()
    assert len(stored_proposals) == 1
    assert stored_proposals[0].proposal_type == "risk_adjustment"
    assert stored_proposals[0].changes["max_position_pct"] == 0.15
    assert stored_proposals[0].changes["new_entry_enabled"] is False

    assert result.review is not None
    assert result.proposal is not None


def test_cli_run_once_with_sample_provider_writes_forecast_artifacts(tmp_path, capsys):
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
    assert '"new_forecast_status": "pending"' in captured.out


def test_coingecko_provider_maps_public_prices_to_candles():
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
    assert candles[0].close == 103.5
    assert candles[1].close == 101.25
    assert all(candle.open == candle.close for candle in candles)
