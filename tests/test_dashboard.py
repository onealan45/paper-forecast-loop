import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from forecast_loop.cli import main
from forecast_loop.evaluation import build_evaluation_summary
from forecast_loop.models import Forecast, ForecastScore, Proposal, Review
from forecast_loop.storage import JsonFileRepository


def _write_meta(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_automation(codex_home: Path, automation_id: str, *, status: str, updated_at: int = 1777030175608) -> None:
    automation_dir = codex_home / "automations" / automation_id
    automation_dir.mkdir(parents=True)
    (automation_dir / "automation.toml").write_text(
        "\n".join(
            [
                "version = 1",
                f'id = "{automation_id}"',
                'kind = "heartbeat"',
                f'name = "{automation_id}"',
                'prompt = "test"',
                f'status = "{status}"',
                'rrule = "FREQ=HOURLY;INTERVAL=1"',
                'target_thread_id = "test-thread"',
                "created_at = 1776961384325",
                f"updated_at = {updated_at}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_render_dashboard_handles_empty_storage(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)

    assert snapshot.latest_forecast is None
    assert snapshot.latest_review is None
    assert snapshot.latest_replay_summary is None
    assert 'lang="zh-Hant"' in html
    assert "操作摘要" in html
    assert "等待第一筆預測循環" in html
    assert html.count("等待第一筆預測循環") == 1
    assert "目前預測" in html
    assert "目前還沒有預測資料" in html
    assert "目前還沒有 replay 摘要" in html
    assert "Dashboard 產生時間" in html


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
    assert 'grid-template-columns: 190px minmax(0, 1fr);' in html
    assert 'main {\n      padding: 28px 32px 42px;\n      display: grid;\n      grid-template-columns: minmax(0, 1fr);' in html
    assert "操作摘要" in html
    assert "目前預測" in html
    assert 'nav aria-label="儀表板區段"' in html
    assert "本輪判讀與建議" in html
    assert "支撐依據" in html
    assert "歷史脈絡" in html
    assert "BTC-USD" in html
    assert "scored" in html
    assert review.summary in html
    assert proposal.proposal_id in html
    assert summary.summary_id in html
    assert 'id="decision"' in html
    assert 'class="panel half secondary-panel" id="replay"' in html
    assert 'id="evidence"' in html
    assert 'id="system"' not in html
    assert "證據快照" in html
    assert html.index('id="summary"') < html.index('id="forecast"') < html.index('id="decision"') < html.index('id="evidence"') < html.index('id="replay"') < html.index('id="raw"')
    assert html.index('class="summary-grid"') < html.index('class="summary-tags"') < html.index('class="summary-note"')
    assert "<details open>" not in html
    forecast_section = html.split('id="forecast"', 1)[1].split("</section>", 1)[0]
    forecast_surface = forecast_section.split("<details>", 1)[0]
    assert "forecast:a" not in forecast_surface
    assert "Provider Through" not in forecast_surface
    assert "Anchor" not in forecast_surface
    assert "<details>" in forecast_section
    decision_section = html.split('id="decision"', 1)[1].split("</section>", 1)[0]
    decision_surface = decision_section.split("<details>", 1)[0]
    assert review.summary in decision_surface
    assert "review:a" not in decision_surface
    assert "proposal:a" not in decision_surface
    assert "Forecast IDs" not in decision_surface
    assert "Score IDs" not in decision_surface
    replay_section = html.split('id="replay"', 1)[1].split("</section>", 1)[0]
    assert "<details>" in replay_section
    assert "Summary ID" in replay_section
    raw_section = html.split('id="raw"', 1)[1].split("</section>", 1)[0]
    assert raw_section.count("<details>") == 2
    assert "<pre>" not in raw_section.split("<details>", 1)[0]
    assert 'grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));' in html


def test_render_dashboard_uses_only_proposal_for_latest_review(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    old_review = Review(
        review_id="review:old",
        created_at=datetime(2026, 4, 21, 10, 0, tzinfo=UTC),
        score_ids=["score:old"],
        forecast_ids=["forecast:old"],
        average_score=0.2,
        threshold_used=0.6,
        decision_basis="old basis",
        summary="Old review requested a proposal.",
        proposal_recommended=True,
        proposal_reason="average_score_below_threshold",
    )
    latest_review = Review(
        review_id="review:latest",
        created_at=datetime(2026, 4, 21, 11, 0, tzinfo=UTC),
        score_ids=["score:latest"],
        forecast_ids=["forecast:latest"],
        average_score=1.0,
        threshold_used=0.6,
        decision_basis="latest basis",
        summary="Latest review keeps current settings.",
        proposal_recommended=False,
        proposal_reason="average_score_at_or_above_threshold",
    )
    old_proposal = Proposal(
        proposal_id="proposal:old",
        created_at=datetime(2026, 4, 21, 10, 5, tzinfo=UTC),
        review_id=old_review.review_id,
        score_ids=["score:old"],
        proposal_type="risk_adjustment",
        changes={"max_position_pct": 0.10},
        threshold_used=0.6,
        decision_basis="old basis",
        rationale="old proposal should not be shown as current",
    )

    repository.save_review(old_review)
    repository.save_review(latest_review)
    repository.save_proposal(old_proposal)

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)
    decision_section = html.split('id="decision"', 1)[1].split("</section>", 1)[0]

    assert snapshot.latest_review == latest_review
    assert snapshot.latest_proposal is None
    assert latest_review.summary in decision_section
    assert "proposal:old" not in decision_section
    assert "old proposal should not be shown as current" not in decision_section


def test_render_dashboard_labels_waiting_for_data_as_coverage_wait(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    repository.save_forecast(
        Forecast(
            forecast_id="forecast:waiting",
            symbol="BTC-USD",
            created_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
            anchor_time=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
            target_window_start=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
            target_window_end=datetime(2026, 4, 21, 11, 0, tzinfo=UTC),
            candle_interval_minutes=60,
            expected_candle_count=3,
            status="waiting_for_data",
            status_reason="awaiting_provider_coverage",
            predicted_regime="trend_up",
            confidence=0.55,
            provider_data_through=datetime(2026, 4, 21, 10, 0, tzinfo=UTC),
            observed_candle_count=2,
        )
    )

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert "等待資料覆蓋" in html
    assert "等待 provider 補齊目標視窗" in html
    assert '<div class="summary-value">已結束</div>' not in html


def test_render_dashboard_reports_automation_freshness(tmp_path, monkeypatch):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    codex_home = tmp_path / ".codex"
    _write_automation(codex_home, "hourly-paper-forecast", status="PAUSED")
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path / "storage"))

    assert "每小時：已暫停（PAUSED）" in html
    assert "Dashboard 產生時間" in html
    assert "Automation 狀態來源" in html
    assert "1970-" not in html


def test_render_dashboard_marks_stale_replay_context(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    latest_forecast = Forecast(
        forecast_id="forecast:live",
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 23, 13, 23, tzinfo=UTC),
        anchor_time=datetime(2026, 4, 23, 13, 0, tzinfo=UTC),
        target_window_start=datetime(2026, 4, 23, 13, 0, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 24, 13, 0, tzinfo=UTC),
        candle_interval_minutes=60,
        expected_candle_count=25,
        status="pending",
        status_reason="awaiting_horizon_end",
        predicted_regime="trend_down",
        confidence=0.55,
        provider_data_through=datetime(2026, 4, 23, 13, 0, tzinfo=UTC),
        observed_candle_count=8,
    )
    replay_forecast = Forecast(
        forecast_id="forecast:replay",
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 22, 8, 0, tzinfo=UTC),
        anchor_time=datetime(2026, 4, 22, 8, 0, tzinfo=UTC),
        target_window_start=datetime(2026, 4, 22, 8, 0, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 22, 9, 0, tzinfo=UTC),
        candle_interval_minutes=60,
        expected_candle_count=2,
        status="resolved",
        status_reason="scored",
        predicted_regime="trend_up",
        confidence=0.55,
        provider_data_through=datetime(2026, 4, 22, 9, 0, tzinfo=UTC),
        observed_candle_count=2,
    )
    repository.save_forecast(latest_forecast)
    summary = build_evaluation_summary(
        replay_id="replay:btc",
        generated_at=datetime(2026, 4, 22, 18, 40, tzinfo=UTC),
        forecasts=[replay_forecast],
        scores=[],
        reviews=[],
        proposals=[],
    )
    repository.save_evaluation_summary(summary)

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)

    assert snapshot.replay_is_stale is True
    assert "historical" in snapshot.replay_freshness_label.lower()
    assert "產生時間" in html
    assert "僅供歷史脈絡參考" in html
    assert "落後最新預測 29 小時" in html
    assert "behind latest forecast" not in html
    assert 'secondary-panel' in html


def test_render_dashboard_translates_failure_status_reasons(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    repository.save_forecast(
        Forecast(
            forecast_id="forecast:missing",
            symbol="BTC-USD",
            created_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
            anchor_time=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
            target_window_start=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
            target_window_end=datetime(2026, 4, 21, 11, 0, tzinfo=UTC),
            candle_interval_minutes=60,
            expected_candle_count=3,
            status="unscorable",
            status_reason="missing_expected_candles",
            predicted_regime="trend_up",
            confidence=0.55,
            provider_data_through=datetime(2026, 4, 21, 11, 0, tzinfo=UTC),
            observed_candle_count=2,
        )
    )

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert "無法評分（unscorable）" in html
    assert "缺少必要 K 線（missing_expected_candles）" in html
    assert '<span class="tag">missing_expected_candles</span>' not in html


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
    assert "操作摘要" in html


def test_cli_render_dashboard_rejects_missing_storage_dir_without_creating_it(tmp_path):
    missing_storage = tmp_path / "typo-storage"

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "render-dashboard",
                "--storage-dir",
                str(missing_storage),
            ]
        )

    assert exc_info.value.code == 2
    assert not missing_storage.exists()
