from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from forecast_loop.models import Forecast, ForecastScore, ResearchDataset, ResearchDatasetRow
from forecast_loop.storage import JsonFileRepository


@dataclass(frozen=True, slots=True)
class ResearchDatasetResult:
    dataset: ResearchDataset
    storage_dir: Path

    def to_dict(self) -> dict:
        payload = self.dataset.to_dict()
        payload["storage_dir"] = str(self.storage_dir.resolve())
        return payload


def build_research_dataset(
    *,
    storage_dir: Path | str,
    symbol: str,
    created_at: datetime,
) -> ResearchDatasetResult:
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("created_at must be timezone-aware")
    storage_path = Path(storage_dir)
    if not storage_path.exists() or not storage_path.is_dir():
        raise ValueError(f"storage directory does not exist: {storage_path}")

    repository = JsonFileRepository(storage_path)
    forecasts = [forecast for forecast in repository.load_forecasts() if forecast.symbol == symbol]
    forecasts_by_id = {forecast.forecast_id: forecast for forecast in forecasts}
    scores = [
        score
        for score in repository.load_scores()
        if score.forecast_id in forecasts_by_id
    ]
    scores = sorted(scores, key=lambda item: item.target_window_end)
    rows = [_row_from_score(forecasts_by_id[score.forecast_id], score) for score in scores]
    if not rows:
        raise ValueError(f"no scored forecasts available for research dataset: {symbol}")
    leakage_findings = check_dataset_leakage(rows)
    leakage_status = "passed" if not leakage_findings else "failed"
    dataset = ResearchDataset(
        dataset_id=ResearchDataset.build_id(
            symbol=symbol,
            forecast_ids=[row.forecast_id for row in rows],
            score_ids=[row.score_id for row in rows],
            row_count=len(rows),
            leakage_status=leakage_status,
        ),
        created_at=created_at,
        symbol=symbol,
        row_count=len(rows),
        leakage_status=leakage_status,
        leakage_findings=leakage_findings,
        forecast_ids=[row.forecast_id for row in rows],
        score_ids=[row.score_id for row in rows],
        rows=rows,
        decision_basis=(
            "research dataset rows derived from scored forecasts; "
            "features are restricted to forecast-time artifacts and labels are target-window outcomes"
        ),
    )
    if leakage_findings:
        raise ValueError("research dataset leakage detected: " + "; ".join(leakage_findings))
    repository.save_research_dataset(dataset)
    return ResearchDatasetResult(dataset=dataset, storage_dir=storage_path)


def check_dataset_leakage(rows: list[ResearchDatasetRow]) -> list[str]:
    findings: list[str] = []
    for row in rows:
        if row.feature_timestamp > row.decision_timestamp:
            findings.append(
                f"{row.forecast_id}: feature_timestamp {row.feature_timestamp.isoformat()} "
                f"> decision_timestamp {row.decision_timestamp.isoformat()}"
            )
        if row.label_timestamp <= row.decision_timestamp:
            findings.append(
                f"{row.forecast_id}: label_timestamp {row.label_timestamp.isoformat()} "
                f"<= decision_timestamp {row.decision_timestamp.isoformat()}"
            )
    return findings


def _row_from_score(forecast: Forecast, score: ForecastScore) -> ResearchDatasetRow:
    decision_timestamp = forecast.anchor_time
    feature_timestamp = forecast.anchor_time
    label_timestamp = score.target_window_end
    return ResearchDatasetRow(
        forecast_id=forecast.forecast_id,
        score_id=score.score_id,
        symbol=forecast.symbol,
        decision_timestamp=decision_timestamp,
        feature_timestamp=feature_timestamp,
        label_timestamp=label_timestamp,
        features={
            "predicted_regime": forecast.predicted_regime,
            "confidence": forecast.confidence,
            "horizon_hours": int((forecast.target_window_end - forecast.anchor_time).total_seconds() // 3600),
            "expected_candle_count": forecast.expected_candle_count,
        },
        label={
            "actual_regime": score.actual_regime,
            "score": score.score,
            "observed_candle_count": score.observed_candle_count,
            "provider_data_through": score.provider_data_through.isoformat(),
        },
    )
