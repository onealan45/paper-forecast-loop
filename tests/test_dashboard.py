import json
from datetime import UTC, datetime
from pathlib import Path

from forecast_loop.cli import main
from forecast_loop.evaluation import build_evaluation_summary
from forecast_loop.models import Forecast, ForecastScore, Proposal, Review
from forecast_loop.storage import JsonFileRepository


def _write_meta(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_render_dashboard_handles_empty_storage(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)

    assert snapshot.latest_forecast is None
    assert snapshot.latest_review is None
    assert snapshot.latest_replay_summary is None
    assert "No forecasts yet" in html
    assert "No replay summary yet" in html


def test_render_dashboard_includes_latest_artifacts(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    forecast = Forecast(
        forecast_id="forecast:a",
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        anchor_time=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        target_window_start=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 21, 11, 0, tzinfo=UTC),
        candle_interval_minutes=60,
        expected_candle_count=3,
        status="resolved",
        status_reason="scored",
        predicted_regime="trend_up",
        confidence=0.55,
        provider_data_through=datetime(2026, 4, 21, 11, 0, tzinfo=UTC),
        observed_candle_count=3,
    )
    score = ForecastScore(
        score_id="score:a",
        forecast_id="forecast:a",
        scored_at=datetime(2026, 4, 21, 11, 0, tzinfo=UTC),
        predicted_regime="trend_up",
        actual_regime="trend_up",
        score=1.0,
        target_window_start=forecast.target_window_start,
        target_window_end=forecast.target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=3,
        observed_candle_count=3,
        provider_data_through=datetime(2026, 4, 21, 11, 0, tzinfo=UTC),
        scoring_basis="regime_direction_over_fully_covered_hourly_window",
    )
    review = Review(
        review_id="review:a",
        created_at=datetime(2026, 4, 21, 11, 5, tzinfo=UTC),
        score_ids=[score.score_id],
        forecast_ids=[forecast.forecast_id],
        average_score=1.0,
        threshold_used=0.6,
        decision_basis="average of last 1 valid scores",
        summary="Forecast accuracy acceptable; keep current paper-only settings.",
        proposal_recommended=False,
        proposal_reason="average_score_at_or_above_threshold",
    )
    proposal = Proposal(
        proposal_id="proposal:a",
        created_at=datetime(2026, 4, 21, 11, 6, tzinfo=UTC),
        review_id=review.review_id,
        score_ids=[score.score_id],
        proposal_type="risk_adjustment",
        changes={"max_position_pct": 0.15, "new_entry_enabled": False},
        threshold_used=0.6,
        decision_basis="average of last 1 valid scores",
        rationale="Generated because average_score_below_threshold against threshold 0.60.",
    )
    summary = build_evaluation_summary(
        replay_id="replay:btc",
        generated_at=datetime(2026, 4, 21, 12, 0, tzinfo=UTC),
        forecasts=[forecast],
        scores=[score],
        reviews=[review],
        proposals=[proposal],
    )

    repository.save_forecast(forecast)
    repository.save_score(score)
    repository.save_review(review)
    repository.save_proposal(proposal)
    repository.save_evaluation_summary(summary)

    _write_meta(
        tmp_path / "last_run_meta.json",
        {
            "provider": "sample",
            "symbol": "BTC-USD",
            "new_forecast": forecast.to_dict(),
            "score_count": 1,
            "score_ids": [score.score_id],
            "review_id": review.review_id,
            "proposal_id": proposal.proposal_id,
        },
    )
    _write_meta(
        tmp_path / "last_replay_meta.json",
        {
            "provider": "sample",
            "symbol": "BTC-USD",
            "cycles_run": 3,
            "scores_created": 1,
            "evaluation_summary": summary.to_dict(),
        },
    )

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)

    assert snapshot.latest_forecast is not None
    assert snapshot.latest_review is not None
    assert snapshot.latest_replay_summary is not None
    assert "BTC-USD" in html
    assert "scored" in html
    assert review.summary in html
    assert proposal.proposal_id in html
    assert summary.summary_id in html


def test_cli_render_dashboard_writes_html_file(tmp_path):
    exit_code = main(
        [
            "render-dashboard",
            "--storage-dir",
            str(tmp_path),
        ]
    )

    output_path = tmp_path / "dashboard.html"

    assert exit_code == 0
    assert output_path.exists()
    html = output_path.read_text(encoding="utf-8")
    assert "Paper Forecast Loop" in html
    assert "System State" in html
