from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from forecast_loop.models import Forecast
from forecast_loop.storage import JsonFileRepository


@dataclass(slots=True)
class StorageRepairResult:
    storage_dir: Path
    total_forecast_count: int
    quarantined_forecast_count: int
    kept_forecast_count: int
    quarantine_path: Path
    report_path: Path
    status: str


def repair_storage(storage_dir: Path | str) -> StorageRepairResult:
    storage_dir = Path(storage_dir)
    repository = JsonFileRepository(storage_dir)
    forecasts = repository.load_forecasts()
    legacy_forecasts = [forecast for forecast in forecasts if _is_legacy_forecast(forecast)]
    current_forecasts = [forecast for forecast in forecasts if not _is_legacy_forecast(forecast)]

    quarantine_dir = storage_dir / "quarantine"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    quarantine_path = quarantine_dir / "legacy_forecasts.jsonl"
    report_path = storage_dir / "storage_repair_report.json"

    if legacy_forecasts:
        existing_ids = set()
        if quarantine_path.exists():
            for line in quarantine_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                existing_ids.add(json.loads(line)["forecast_id"])

        with quarantine_path.open("a", encoding="utf-8") as handle:
            for forecast in legacy_forecasts:
                if forecast.forecast_id in existing_ids:
                    continue
                handle.write(json.dumps(forecast.to_dict()) + "\n")

        repository.replace_forecasts(current_forecasts)
        status = "legacy_forecasts_quarantined"
    else:
        status = "no_legacy_forecasts_found"

    result = StorageRepairResult(
        storage_dir=storage_dir,
        total_forecast_count=len(forecasts),
        quarantined_forecast_count=len(legacy_forecasts),
        kept_forecast_count=len(current_forecasts),
        quarantine_path=quarantine_path,
        report_path=report_path,
        status=status,
    )
    report_path.write_text(
        json.dumps(
            {
                "storage_dir": str(storage_dir.resolve()),
                "total_forecast_count": result.total_forecast_count,
                "quarantined_forecast_count": result.quarantined_forecast_count,
                "kept_forecast_count": result.kept_forecast_count,
                "quarantine_path": str(quarantine_path.resolve()),
                "status": result.status,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return result


def _is_legacy_forecast(forecast: Forecast) -> bool:
    if not _is_hour_aligned(forecast.anchor_time):
        return True
    if forecast.target_window_start != forecast.anchor_time:
        return True
    if not _is_hour_aligned(forecast.target_window_end):
        return True
    return False


def _is_hour_aligned(value) -> bool:
    return value.minute == 0 and value.second == 0 and value.microsecond == 0
