from datetime import UTC, datetime, timedelta
import json

from forecast_loop.cli import main
from forecast_loop.models import Forecast
from forecast_loop.storage import JsonFileRepository


def _forecast(
    *,
    forecast_id: str,
    anchor_time: datetime,
    target_window_end: datetime,
) -> Forecast:
    return Forecast(
        forecast_id=forecast_id,
        symbol="BTC-USD",
        created_at=anchor_time,
        anchor_time=anchor_time,
        target_window_start=anchor_time,
        target_window_end=target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=25,
        status="pending",
        status_reason="awaiting_horizon_end",
        predicted_regime="trend_up",
        confidence=0.55,
        provider_data_through=anchor_time,
        observed_candle_count=8,
    )


def test_repair_storage_quarantines_legacy_off_boundary_forecasts(tmp_path):
    repository = JsonFileRepository(tmp_path)
    legacy = _forecast(
        forecast_id="legacy-1",
        anchor_time=datetime(2026, 4, 21, 16, 48, 13, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 22, 16, 48, 13, tzinfo=UTC),
    )
    current = _forecast(
        forecast_id="current-1",
        anchor_time=datetime(2026, 4, 22, 18, 0, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 23, 18, 0, tzinfo=UTC),
    )
    repository.save_forecast(legacy)
    repository.save_forecast(current)

    exit_code = main(
        [
            "repair-storage",
            "--storage-dir",
            str(tmp_path),
        ]
    )

    remaining = repository.load_forecasts()
    report = json.loads((tmp_path / "storage_repair_report.json").read_text(encoding="utf-8"))
    quarantine_path = tmp_path / "quarantine" / "legacy_forecasts.jsonl"

    assert exit_code == 0
    assert [forecast.forecast_id for forecast in remaining] == ["current-1"]
    assert quarantine_path.exists()
    quarantined = [json.loads(line) for line in quarantine_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert [item["forecast_id"] for item in quarantined] == ["legacy-1"]
    assert report["quarantined_forecast_count"] == 1
    assert report["kept_forecast_count"] == 1


def test_repair_storage_is_idempotent_on_second_run(tmp_path):
    repository = JsonFileRepository(tmp_path)
    legacy = _forecast(
        forecast_id="legacy-1",
        anchor_time=datetime(2026, 4, 21, 16, 48, 13, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 22, 16, 48, 13, tzinfo=UTC),
    )
    repository.save_forecast(legacy)

    first_exit = main(["repair-storage", "--storage-dir", str(tmp_path)])
    second_exit = main(["repair-storage", "--storage-dir", str(tmp_path)])

    report = json.loads((tmp_path / "storage_repair_report.json").read_text(encoding="utf-8"))
    quarantine_path = tmp_path / "quarantine" / "legacy_forecasts.jsonl"
    quarantined = [json.loads(line) for line in quarantine_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert first_exit == 0
    assert second_exit == 0
    assert repository.load_forecasts() == []
    assert len(quarantined) == 1
    assert report["quarantined_forecast_count"] == 0
    assert report["kept_forecast_count"] == 0


def test_repair_storage_reports_clean_storage_without_changes(tmp_path):
    exit_code = main(["repair-storage", "--storage-dir", str(tmp_path)])

    report = json.loads((tmp_path / "storage_repair_report.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert report["quarantined_forecast_count"] == 0
    assert report["kept_forecast_count"] == 0
    assert report["status"] == "no_legacy_forecasts_found"
