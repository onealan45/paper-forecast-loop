from datetime import UTC, datetime, timedelta
import json

import pytest

from forecast_loop.cli import main
from forecast_loop.health import run_health_check
from forecast_loop.models import Forecast, ForecastScore, ResearchDataset, ResearchDatasetRow
from forecast_loop.research_dataset import check_dataset_leakage
from forecast_loop.storage import JsonFileRepository


def _forecast(
    forecast_id: str,
    now: datetime,
    *,
    provider_data_through: datetime | None = None,
) -> Forecast:
    return Forecast(
        forecast_id=forecast_id,
        symbol="BTC-USD",
        created_at=now,
        anchor_time=now,
        target_window_start=now,
        target_window_end=now + timedelta(hours=24),
        candle_interval_minutes=60,
        expected_candle_count=24,
        status="resolved",
        status_reason="scored",
        predicted_regime="trend_up",
        confidence=0.7,
        provider_data_through=provider_data_through or now,
        observed_candle_count=24,
    )


def _score(score_id: str, forecast: Forecast) -> ForecastScore:
    return ForecastScore(
        score_id=score_id,
        forecast_id=forecast.forecast_id,
        scored_at=forecast.target_window_end,
        predicted_regime=forecast.predicted_regime or "unknown",
        actual_regime="trend_up",
        score=1.0,
        target_window_start=forecast.target_window_start,
        target_window_end=forecast.target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=24,
        observed_candle_count=24,
        provider_data_through=forecast.target_window_end,
        scoring_basis="test",
    )


def test_cli_build_research_dataset_writes_no_lookahead_rows(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    start = datetime(2026, 4, 20, 0, 0, tzinfo=UTC)
    for index in range(2):
        forecast = _forecast(f"forecast:{index}", start + timedelta(days=index))
        repository.save_forecast(forecast)
        repository.save_score(_score(f"score:{index}", forecast))

    exit_code = main(
        [
            "build-research-dataset",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--created-at",
            "2026-04-24T12:00:00+00:00",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["row_count"] == 2
    assert payload["leakage_status"] == "passed"
    for row in payload["rows"]:
        assert row["feature_timestamp"] <= row["decision_timestamp"]
        assert row["label_timestamp"] > row["decision_timestamp"]
    assert len(repository.load_research_datasets()) == 1


def test_cli_build_research_dataset_ignores_scoring_time_provider_coverage(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 20, 0, 0, tzinfo=UTC)
    forecast = _forecast("forecast:resolved", now, provider_data_through=now + timedelta(hours=24))
    repository.save_forecast(forecast)
    repository.save_score(_score("score:resolved", forecast))

    exit_code = main(
        [
            "build-research-dataset",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    row = payload["rows"][0]
    assert row["feature_timestamp"] == now.isoformat()
    assert "provider_data_through" not in row["features"]
    assert row["label"]["provider_data_through"] == forecast.target_window_end.isoformat()


def test_check_dataset_leakage_rejects_label_at_decision_time():
    now = datetime(2026, 4, 20, 0, 0, tzinfo=UTC)
    row = ResearchDatasetRow(
        forecast_id="forecast:label",
        score_id="score:label",
        symbol="BTC-USD",
        decision_timestamp=now,
        feature_timestamp=now,
        label_timestamp=now,
        features={},
        label={},
    )

    findings = check_dataset_leakage([row])

    assert findings
    assert "label_timestamp" in findings[0]


def test_research_dataset_round_trips_rows():
    now = datetime(2026, 4, 20, 0, 0, tzinfo=UTC)
    dataset = ResearchDataset(
        dataset_id="research-dataset:test",
        created_at=now,
        symbol="BTC-USD",
        row_count=1,
        leakage_status="passed",
        leakage_findings=[],
        forecast_ids=["forecast:1"],
        score_ids=["score:1"],
        rows=[
            ResearchDatasetRow(
                forecast_id="forecast:1",
                score_id="score:1",
                symbol="BTC-USD",
                decision_timestamp=now,
                feature_timestamp=now,
                label_timestamp=now + timedelta(hours=24),
                features={"confidence": 0.7},
                label={"score": 1.0},
            )
        ],
        decision_basis="test",
    )

    assert ResearchDataset.from_dict(dataset.to_dict()) == dataset


def test_cli_build_research_dataset_missing_storage_fails_without_creating_path(tmp_path, capsys):
    missing = tmp_path / "missing-storage"

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "build-research-dataset",
                "--storage-dir",
                str(missing),
                "--symbol",
                "BTC-USD",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "storage directory does not exist" in captured.err
    assert "Traceback" not in captured.err
    assert not missing.exists()


def test_cli_build_research_dataset_requires_scored_forecasts(tmp_path, capsys):
    JsonFileRepository(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "build-research-dataset",
                "--storage-dir",
                str(tmp_path),
                "--symbol",
                "BTC-USD",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "no scored forecasts available" in captured.err
    assert "Traceback" not in captured.err


def test_health_check_detects_research_dataset_broken_links(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 20, 0, 0, tzinfo=UTC)
    forecast = _forecast("forecast:1", now)
    repository.save_forecast(forecast)
    repository.save_research_dataset(
        ResearchDataset(
            dataset_id="research-dataset:broken",
            created_at=now,
            symbol="BTC-USD",
            row_count=1,
            leakage_status="passed",
            leakage_findings=[],
            forecast_ids=[forecast.forecast_id],
            score_ids=["score:missing"],
            rows=[
                ResearchDatasetRow(
                    forecast_id=forecast.forecast_id,
                    score_id="score:missing",
                    symbol="BTC-USD",
                    decision_timestamp=now,
                    feature_timestamp=now,
                    label_timestamp=now + timedelta(hours=24),
                    features={},
                    label={},
                )
            ],
            decision_basis="test",
        )
    )

    result = run_health_check(storage_dir=tmp_path, symbol="BTC-USD", now=now, create_repair_request=False)

    assert "research_dataset_missing_score" in {finding.code for finding in result.findings}


def test_health_check_detects_research_dataset_leakage(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 20, 0, 0, tzinfo=UTC)
    forecast = _forecast("forecast:1", now)
    score = _score("score:1", forecast)
    repository.save_forecast(forecast)
    repository.save_score(score)
    repository.save_research_dataset(
        ResearchDataset(
            dataset_id="research-dataset:leak",
            created_at=now,
            symbol="BTC-USD",
            row_count=1,
            leakage_status="failed",
            leakage_findings=["manual leakage flag"],
            forecast_ids=[forecast.forecast_id],
            score_ids=[score.score_id],
            rows=[
                ResearchDatasetRow(
                    forecast_id=forecast.forecast_id,
                    score_id=score.score_id,
                    symbol="BTC-USD",
                    decision_timestamp=now,
                    feature_timestamp=now + timedelta(minutes=1),
                    label_timestamp=now + timedelta(hours=24),
                    features={},
                    label={},
                )
            ],
            decision_basis="test",
        )
    )

    result = run_health_check(storage_dir=tmp_path, symbol="BTC-USD", now=now, create_repair_request=False)

    assert "research_dataset_leakage" in {finding.code for finding in result.findings}
