from datetime import UTC, datetime, timedelta
import json

from forecast_loop.cli import main
from forecast_loop.health import run_health_check
from forecast_loop.models import Forecast, MarketCandle, ProviderRun
from forecast_loop.pipeline import ForecastingLoop
from forecast_loop.config import LoopConfig
from forecast_loop.provider_audit import AuditedMarketDataProvider
from forecast_loop.providers import InMemoryMarketDataProvider
from forecast_loop.storage import JsonFileRepository


def _candles(start: datetime, count: int) -> list[MarketCandle]:
    return [
        MarketCandle(
            timestamp=start + timedelta(hours=index),
            open=100.0 + index,
            high=101.0 + index,
            low=99.0 + index,
            close=100.0 + index,
            volume=1_000.0 + index,
        )
        for index in range(count)
    ]


def test_audited_provider_records_successful_fetches(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    provider = AuditedMarketDataProvider(
        provider=InMemoryMarketDataProvider({"BTC-USD": _candles(now - timedelta(hours=3), 4)}),
        provider_name="sample",
        repository=repository,
    )

    recent = provider.get_recent_candles("BTC-USD", lookback_candles=2, end_time=now)

    runs = repository.load_provider_runs()
    assert len(recent) == 2
    assert len(runs) == 1
    assert runs[0].status == "success"
    assert runs[0].candle_count == 2
    assert runs[0].schema_version == "market_candles_v1"


def test_run_once_writes_provider_audit_runs(tmp_path, capsys):
    assert main(
        [
            "run-once",
            "--provider",
            "sample",
            "--symbol",
            "BTC-USD",
            "--storage-dir",
            str(tmp_path),
            "--now",
            "2026-04-24T12:00:00+00:00",
        ]
    ) == 0
    capsys.readouterr()

    runs = JsonFileRepository(tmp_path).load_provider_runs()
    assert runs
    assert any(run.operation == "get_latest_candle_boundary" for run in runs)
    assert any(run.operation == "get_recent_candles" for run in runs)


def test_health_check_flags_latest_provider_failure(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_provider_run(
        ProviderRun(
            provider_run_id="provider-run:error",
            created_at=now,
            provider="sample",
            symbol="BTC-USD",
            operation="get_recent_candles",
            status="error",
            started_at=now,
            completed_at=now,
            candle_count=0,
            data_start=None,
            data_end=None,
            schema_version="market_candles_v1",
            error_type="RuntimeError",
            error_message="provider down",
        )
    )
    (tmp_path / "dashboard.html").write_text("Dashboard 產生時間：test", encoding="utf-8")

    result = run_health_check(storage_dir=tmp_path, symbol="BTC-USD", now=now, create_repair_request=False)

    assert result.repair_required is True
    assert "provider_failure" in {finding.code for finding in result.findings}


def test_health_check_flags_provider_empty_and_schema_drift(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_provider_run(
        ProviderRun(
            provider_run_id="provider-run:empty",
            created_at=now,
            provider="sample",
            symbol="BTC-USD",
            operation="get_recent_candles",
            status="empty",
            started_at=now,
            completed_at=now,
            candle_count=0,
            data_start=None,
            data_end=None,
            schema_version="unexpected",
        )
    )
    (tmp_path / "dashboard.html").write_text("Dashboard 產生時間：test", encoding="utf-8")

    result = run_health_check(storage_dir=tmp_path, symbol="BTC-USD", now=now, create_repair_request=False)
    codes = {finding.code for finding in result.findings}

    assert "provider_empty_data" in codes
    assert "provider_schema_drift" in codes


def test_health_check_flags_stale_provider_run_as_warning(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_forecast(
        Forecast(
            forecast_id="forecast:provider-stale",
            symbol="BTC-USD",
            created_at=now,
            anchor_time=now,
            target_window_start=now,
            target_window_end=now + timedelta(hours=24),
            candle_interval_minutes=60,
            expected_candle_count=25,
            status="pending",
            status_reason="awaiting_horizon_end",
            predicted_regime="trend_up",
            confidence=0.55,
            provider_data_through=now,
            observed_candle_count=0,
        )
    )
    repository.save_provider_run(
        ProviderRun(
            provider_run_id="provider-run:stale",
            created_at=now - timedelta(hours=30),
            provider="sample",
            symbol="BTC-USD",
            operation="get_recent_candles",
            status="success",
            started_at=now - timedelta(hours=30),
            completed_at=now - timedelta(hours=30),
            candle_count=2,
            data_start=now - timedelta(hours=31),
            data_end=now - timedelta(hours=30),
            schema_version="market_candles_v1",
        )
    )
    (tmp_path / "dashboard.html").write_text("Dashboard 產生時間：test", encoding="utf-8")

    result = run_health_check(storage_dir=tmp_path, symbol="BTC-USD", now=now, create_repair_request=False)

    assert result.status == "degraded"
    assert result.repair_required is False
    assert "provider_stale" in {finding.code for finding in result.findings}


def test_health_check_flags_malformed_provider_run_row(tmp_path):
    (tmp_path / "provider_runs.jsonl").write_text(
        json.dumps(
            {
                "provider_run_id": "provider-run:bad",
                "created_at": "2026-04-24T12:00:00+00:00",
                "provider": "sample",
                "symbol": "BTC-USD",
                "operation": "get_recent_candles",
                "started_at": "2026-04-24T12:00:00+00:00",
                "candle_count": 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_health_check(
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
        create_repair_request=False,
    )

    assert result.repair_required is True
    assert "bad_json_row" in {finding.code for finding in result.findings}


def test_dashboard_renders_provider_health(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_provider_run(
        ProviderRun(
            provider_run_id="provider-run:dashboard",
            created_at=now,
            provider="sample",
            symbol="BTC-USD",
            operation="get_recent_candles",
            status="success",
            started_at=now,
            completed_at=now,
            candle_count=2,
            data_start=now - timedelta(hours=1),
            data_end=now,
            schema_version="market_candles_v1",
        )
    )

    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert 'id="provider"' in html
    assert "Provider Audit" in html
    assert "正常（success）" in html
    assert "sample" in html


def test_cli_run_once_records_provider_failure_before_returning_error(tmp_path, capsys):
    class FailingProvider:
        candle_interval_minutes = 60

        def get_latest_candle_boundary(self, symbol, end_time=None):
            raise RuntimeError("boom")

    repository = JsonFileRepository(tmp_path)
    provider = AuditedMarketDataProvider(provider=FailingProvider(), provider_name="sample", repository=repository)
    loop = ForecastingLoop(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=2, lookback_candles=2),
        data_provider=provider,
        repository=repository,
    )

    try:
        loop.run_cycle(now=datetime(2026, 4, 24, 12, 0, tzinfo=UTC))
    except RuntimeError:
        pass

    runs = repository.load_provider_runs()
    assert runs[-1].status == "error"
    assert runs[-1].error_type == "RuntimeError"
