from datetime import UTC, datetime, timedelta
import json

import pytest

from forecast_loop.baselines import build_baseline_evaluation
from forecast_loop.broker import BrokerMode, PaperBrokerAdapter, build_broker_adapter
from forecast_loop.cli import main
from forecast_loop.decision import generate_strategy_decision
from forecast_loop.health import run_health_check
from forecast_loop.models import (
    BaselineEvaluation,
    EvaluationSummary,
    Forecast,
    ForecastScore,
    PaperPosition,
    PaperPortfolioSnapshot,
    Review,
    RiskSnapshot,
)
from forecast_loop.storage import JsonFileRepository


def _forecast(
    forecast_id: str,
    *,
    anchor_time: datetime,
    predicted_regime: str = "trend_up",
    status: str = "resolved",
) -> Forecast:
    return Forecast(
        forecast_id=forecast_id,
        symbol="BTC-USD",
        created_at=anchor_time,
        anchor_time=anchor_time,
        target_window_start=anchor_time,
        target_window_end=anchor_time + timedelta(hours=2),
        candle_interval_minutes=60,
        expected_candle_count=3,
        status=status,
        status_reason="scored" if status == "resolved" else "awaiting_horizon_end",
        predicted_regime=predicted_regime,
        confidence=0.72,
        provider_data_through=anchor_time + timedelta(hours=2),
        observed_candle_count=3,
    )


def _score(score_id: str, forecast: Forecast, *, actual_regime: str, hit: bool, scored_at: datetime) -> ForecastScore:
    return ForecastScore(
        score_id=score_id,
        forecast_id=forecast.forecast_id,
        scored_at=scored_at,
        predicted_regime=forecast.predicted_regime or "unknown",
        actual_regime=actual_regime,
        score=1.0 if hit else 0.0,
        target_window_start=forecast.target_window_start,
        target_window_end=forecast.target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=3,
        observed_candle_count=3,
        provider_data_through=forecast.target_window_end,
        scoring_basis="test",
    )


def _seed_scores(repository: JsonFileRepository, *, actuals: list[str], hits: list[bool]) -> list[ForecastScore]:
    scores = []
    start = datetime(2026, 4, 21, 0, 0, tzinfo=UTC)
    for index, (actual, hit) in enumerate(zip(actuals, hits, strict=True)):
        forecast = _forecast(
            f"forecast:{index}",
            anchor_time=start + timedelta(hours=index),
            predicted_regime=actual if hit else ("trend_down" if actual == "trend_up" else "trend_up"),
        )
        score = _score(
            f"score:{index}",
            forecast,
            actual_regime=actual,
            hit=hit,
            scored_at=forecast.target_window_end,
        )
        repository.save_forecast(forecast)
        repository.save_score(score)
        scores.append(score)
    return scores


def _ok_risk(now: datetime, *, created_at: datetime | None = None) -> RiskSnapshot:
    return RiskSnapshot(
        risk_id=f"risk:{(created_at or now).isoformat()}",
        created_at=created_at or now,
        symbol="BTC-USD",
        status="OK",
        severity="none",
        current_drawdown_pct=0.0,
        max_drawdown_pct=0.0,
        gross_exposure_pct=0.0,
        net_exposure_pct=0.0,
        position_pct=0.0,
        max_position_pct=0.15,
        max_gross_exposure_pct=0.20,
        reduce_risk_drawdown_pct=0.05,
        stop_new_entries_drawdown_pct=0.10,
        findings=[],
        recommended_action="HOLD",
        decision_basis="test",
    )


def test_repository_round_trips_m1_artifacts(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    forecast = _forecast("forecast:latest", anchor_time=now)
    score = _score("score:latest", forecast, actual_regime="trend_up", hit=True, scored_at=now)
    repository.save_forecast(forecast)
    repository.save_score(score)
    baseline = build_baseline_evaluation(
        symbol="BTC-USD",
        generated_at=now,
        forecasts=repository.load_forecasts(),
        scores=repository.load_scores(),
    )
    snapshot = PaperPortfolioSnapshot(
        snapshot_id="portfolio:test",
        created_at=now,
        equity=10_000,
        cash=8_000,
        gross_exposure_pct=0.2,
        net_exposure_pct=0.2,
        max_drawdown_pct=None,
        positions=[
            PaperPosition(
                symbol="BTC-USD",
                quantity=0.1,
                avg_price=100,
                market_price=120,
                market_value=12,
                unrealized_pnl=2,
                position_pct=0.2,
            )
        ],
    )
    repository.save_baseline_evaluation(baseline)
    repository.save_baseline_evaluation(baseline)
    repository.save_portfolio_snapshot(snapshot)

    assert repository.load_baseline_evaluations() == [baseline]
    assert repository.load_portfolio_snapshots() == [snapshot]


def test_strategy_decision_holds_when_evidence_is_insufficient(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    forecast = _forecast("forecast:latest", anchor_time=now, status="pending")
    repository.save_forecast(forecast)

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
        risk_snapshot=_ok_risk(now),
    )

    assert decision.action == "HOLD"
    assert decision.evidence_grade == "INSUFFICIENT"
    assert decision.tradeable is False
    assert decision.blocked_reason == "insufficient_evidence"
    assert decision.forecast_ids == [forecast.forecast_id]
    assert repository.load_strategy_decisions() == [decision]


def test_strategy_decision_blocks_buy_sell_when_model_does_not_beat_baseline(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_scores(repository, actuals=["trend_up"] * 5, hits=[True] * 5)
    latest = _forecast("forecast:latest", anchor_time=now, predicted_regime="trend_up", status="pending")
    repository.save_forecast(latest)

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
    )

    assert decision.action == "HOLD"
    assert decision.blocked_reason == "model_not_beating_baseline"
    assert decision.tradeable is False


def test_strategy_decision_reduces_risk_when_recent_score_is_poor(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_scores(
        repository,
        actuals=["trend_up", "trend_down", "trend_up", "trend_down", "trend_up"],
        hits=[True, False, False, False, False],
    )
    repository.save_portfolio_snapshot(
        PaperPortfolioSnapshot(
            snapshot_id="portfolio:risk",
            created_at=now,
            equity=10_000,
            cash=9_000,
            gross_exposure_pct=0.10,
            net_exposure_pct=0.10,
            max_drawdown_pct=None,
            positions=[
                PaperPosition(
                    symbol="BTC-USD",
                    quantity=1,
                    avg_price=100,
                    market_price=100,
                    market_value=1_000,
                    unrealized_pnl=0,
                    position_pct=0.10,
                )
            ],
        )
    )
    latest = _forecast("forecast:latest", anchor_time=now, predicted_regime="trend_up", status="pending")
    repository.save_forecast(latest)

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
    )

    assert decision.action == "REDUCE_RISK"
    assert decision.risk_level == "HIGH"
    assert decision.recommended_position_pct == 0.05


def test_strategy_decision_buys_only_when_evidence_beats_baseline(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_scores(
        repository,
        actuals=["trend_up", "trend_up", "trend_down", "trend_up", "trend_down", "trend_down"],
        hits=[True, True, True, True, True, True],
    )
    latest = _forecast("forecast:latest", anchor_time=now, predicted_regime="trend_up", status="pending")
    repository.save_forecast(latest)

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
        risk_snapshot=_ok_risk(now),
    )

    assert decision.action == "HOLD"
    assert decision.evidence_grade == "B"
    assert decision.tradeable is False
    assert decision.blocked_reason == "research_backtest_missing"
    assert decision.baseline_ids
    assert decision.score_ids


def test_strategy_decision_blocks_directional_buy_without_risk_snapshot(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_scores(
        repository,
        actuals=["trend_up", "trend_up", "trend_down", "trend_up", "trend_down", "trend_down"],
        hits=[True, True, True, True, True, True],
    )
    latest = _forecast("forecast:latest", anchor_time=now, predicted_regime="trend_up", status="pending")
    repository.save_forecast(latest)

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
    )

    assert decision.action == "HOLD"
    assert decision.tradeable is False
    assert decision.blocked_reason == "research_backtest_missing"
    assert "risk=none" in decision.decision_basis


def test_strategy_decision_blocks_directional_buy_with_stale_risk_snapshot(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_scores(
        repository,
        actuals=["trend_up", "trend_up", "trend_down", "trend_up", "trend_down", "trend_down"],
        hits=[True, True, True, True, True, True],
    )
    latest = _forecast("forecast:latest", anchor_time=now, predicted_regime="trend_up", status="pending")
    repository.save_forecast(latest)
    repository.save_risk_snapshot(_ok_risk(now, created_at=now - timedelta(hours=3)))

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
    )

    assert decision.action == "HOLD"
    assert decision.tradeable is False
    assert decision.blocked_reason == "research_backtest_missing"


def test_strategy_decision_stops_new_entries_when_health_requires_repair(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    health = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now)

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
        health_result=health,
    )

    assert health.repair_required is True
    assert decision.action == "STOP_NEW_ENTRIES"
    assert decision.blocked_reason == "health_check_repair_required"
    assert (tmp_path / ".codex" / "repair_requests" / "pending").exists()


def test_strategy_decision_fail_closed_does_not_read_corrupt_storage_after_blocking_health(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    storage.mkdir()
    (storage / "forecasts.jsonl").write_text("{bad json\n", encoding="utf-8")
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    health = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now)

    decision = generate_strategy_decision(
        repository=repository,
        symbol="BTC-USD",
        horizon_hours=24,
        now=now,
        health_result=health,
    )

    assert decision.action == "STOP_NEW_ENTRIES"
    assert decision.blocked_reason == "health_check_repair_required"
    assert repository.load_strategy_decisions() == [decision]


def test_paper_broker_is_only_available_mode():
    broker = build_broker_adapter("paper")
    snapshot = broker.get_account_snapshot(now=datetime(2026, 4, 24, 12, 0, tzinfo=UTC))
    order = broker.submit_order(symbol="BTC-USD", side="BUY", quantity=1)
    health = broker.health_check(now=datetime(2026, 4, 24, 12, 0, tzinfo=UTC))

    assert isinstance(broker, PaperBrokerAdapter)
    assert broker.mode == BrokerMode.INTERNAL_PAPER
    assert snapshot.equity == 10_000
    assert broker.get_positions(now=datetime(2026, 4, 24, 12, 0, tzinfo=UTC)) == []
    assert broker.get_fills() == []
    assert broker.get_order_status(order_id="paper-order:test")["status"] == "unavailable"
    assert broker.cancel_order(order_id="paper-order:test")["status"] == "blocked"
    assert order["status"] == "blocked"
    assert order["mode"] == "INTERNAL_PAPER"
    assert health["live_trading_available"] is False
    assert health["external_submit_available"] is False
    assert build_broker_adapter("INTERNAL_PAPER").mode == BrokerMode.INTERNAL_PAPER
    with pytest.raises(ValueError, match="only INTERNAL_PAPER"):
        build_broker_adapter("EXTERNAL_PAPER")
    with pytest.raises(ValueError, match="only INTERNAL_PAPER"):
        build_broker_adapter("SANDBOX")
    with pytest.raises(ValueError, match="live mode is unsupported"):
        build_broker_adapter("live")


def test_health_check_detects_bad_json_and_writes_repair_request(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    storage.mkdir()
    (storage / "forecasts.jsonl").write_text("{bad json\n", encoding="utf-8")

    result = run_health_check(
        storage_dir=storage,
        symbol="BTC-USD",
        now=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
    )

    assert result.status == "unhealthy"
    assert result.severity == "blocking"
    assert result.repair_required is True
    assert result.repair_request_id is not None
    assert (storage / "repair_requests.jsonl").exists()
    assert next(iter((tmp_path / ".codex" / "repair_requests" / "pending").glob("*.md"))).exists()


def test_health_check_detects_duplicate_forecast_and_meta_mismatch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    forecast = _forecast("forecast:dup", anchor_time=now, status="pending")
    with (storage / "forecasts.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(forecast.to_dict()) + "\n")
        handle.write(json.dumps(forecast.to_dict()) + "\n")
    (storage / "last_run_meta.json").write_text(
        json.dumps({"new_forecast": {"forecast_id": "forecast:other"}}),
        encoding="utf-8",
    )

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now)
    codes = {finding.code for finding in result.findings}

    assert repository.root.exists()
    assert "duplicate_forecast_id" in codes
    assert "last_run_meta_mismatch" in codes
    assert result.repair_required is True


def test_health_check_detects_score_pointing_to_missing_forecast(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    storage.mkdir()
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    valid_forecast = _forecast("forecast:valid", anchor_time=now, status="pending")
    missing_forecast = _forecast("forecast:missing", anchor_time=now)
    bad_score = _score(
        "score:bad",
        missing_forecast,
        actual_regime="trend_up",
        hit=True,
        scored_at=now,
    )
    (storage / "forecasts.jsonl").write_text(json.dumps(valid_forecast.to_dict()) + "\n", encoding="utf-8")
    (storage / "scores.jsonl").write_text(json.dumps(bad_score.to_dict()) + "\n", encoding="utf-8")

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now)

    assert "score_missing_forecast" in {finding.code for finding in result.findings}
    assert result.repair_required is True


def test_health_check_detects_baseline_pointing_to_missing_artifacts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    valid_forecast = _forecast("forecast:valid", anchor_time=now, status="pending")
    repository.save_forecast(valid_forecast)
    repository.save_baseline_evaluation(
        BaselineEvaluation(
            baseline_id="baseline:broken",
            created_at=now,
            symbol="BTC-USD",
            sample_size=1,
            directional_accuracy=None,
            baseline_accuracy=None,
            model_edge=None,
            recent_score=None,
            evidence_grade="INSUFFICIENT",
            forecast_ids=["forecast:missing"],
            score_ids=["score:missing"],
            decision_basis="test broken links",
        )
    )

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now)
    codes = {finding.code for finding in result.findings}

    assert "baseline_missing_forecast" in codes
    assert "baseline_missing_score" in codes
    assert result.repair_required is True


def test_health_check_detects_non_replay_evaluation_summary_broken_links(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_forecast(_forecast("forecast:valid", anchor_time=now, status="pending"))
    repository.save_evaluation_summary(
        EvaluationSummary(
            summary_id="summary:ignored-by-from-dict",
            replay_id="current-summary",
            generated_at=now,
            forecast_ids=["forecast:missing"],
            scored_forecast_ids=["forecast:missing-scored"],
            replay_window_start=None,
            replay_window_end=None,
            anchor_time_start=None,
            anchor_time_end=None,
            forecast_count=1,
            resolved_count=0,
            waiting_for_data_count=0,
            unscorable_count=0,
            average_score=None,
            score_ids=["score:missing"],
            review_ids=["review:missing"],
            proposal_ids=["proposal:missing"],
        )
    )

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now)
    codes = {finding.code for finding in result.findings}

    assert "evaluation_summary_missing_forecast" in codes
    assert "evaluation_summary_missing_score" in codes
    assert "evaluation_summary_missing_review" in codes
    assert "evaluation_summary_missing_proposal" in codes
    assert result.repair_required is True


def test_health_check_allows_replay_scoped_evaluation_summary_links(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_forecast(_forecast("forecast:valid", anchor_time=now, status="pending"))
    repository.save_evaluation_summary(
        EvaluationSummary(
            summary_id="summary:replay",
            replay_id="replay:sample:BTC-USD",
            generated_at=now,
            forecast_ids=["forecast:replay-only"],
            scored_forecast_ids=["forecast:replay-only"],
            replay_window_start=now,
            replay_window_end=now,
            anchor_time_start=now,
            anchor_time_end=now,
            forecast_count=1,
            resolved_count=1,
            waiting_for_data_count=0,
            unscorable_count=0,
            average_score=1.0,
            score_ids=["score:replay-only"],
            review_ids=[],
            proposal_ids=[],
        )
    )

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now)

    assert result.repair_required is False


def test_cli_decide_fail_closed_on_corrupt_portfolio_snapshot(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_forecast(_forecast("forecast:latest", anchor_time=now, status="pending"))
    (storage / "portfolio_snapshots.jsonl").write_text("{bad json\n", encoding="utf-8")

    exit_code = main(
        [
            "decide",
            "--storage-dir",
            str(storage),
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-24T12:00:00+00:00",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    health = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now)

    assert exit_code == 0
    assert payload["action"] == "STOP_NEW_ENTRIES"
    assert payload["blocked_reason"] == "health_check_repair_required"
    assert "bad_json_row" in {finding.code for finding in health.findings}
    assert health.repair_required is True


def test_health_check_can_create_repair_request_when_repair_log_is_corrupt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    repository = JsonFileRepository(storage)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_forecast(_forecast("forecast:latest", anchor_time=now, status="pending"))
    (storage / "repair_requests.jsonl").write_text("{bad json\n", encoding="utf-8")

    result = run_health_check(storage_dir=storage, symbol="BTC-USD", now=now)
    lines = (storage / "repair_requests.jsonl").read_text(encoding="utf-8").splitlines()

    assert result.repair_required is True
    assert result.repair_request_id is not None
    assert "bad_json_row" in {finding.code for finding in result.findings}
    assert len(lines) == 2
    assert json.loads(lines[-1])["repair_request_id"] == result.repair_request_id


def test_missing_storage_health_check_can_use_corrupt_global_repair_log(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    global_log = tmp_path / ".codex" / "repair_requests" / "repair_requests.jsonl"
    global_log.parent.mkdir(parents=True)
    global_log.write_text("{bad json\n", encoding="utf-8")
    missing = tmp_path / "missing-storage"

    result = run_health_check(
        storage_dir=missing,
        symbol="BTC-USD",
        now=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
    )
    lines = global_log.read_text(encoding="utf-8").splitlines()

    assert result.repair_required is True
    assert result.repair_request_id is not None
    assert not missing.exists()
    assert len(lines) == 2
    assert json.loads(lines[-1])["repair_request_id"] == result.repair_request_id


def test_health_check_existing_file_storage_path_uses_global_repair_request(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage_file = tmp_path / "storage-is-file"
    storage_file.write_text("not a directory", encoding="utf-8")

    result = run_health_check(
        storage_dir=storage_file,
        symbol="BTC-USD",
        now=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
    )

    assert result.repair_required is True
    assert "storage_path_not_directory" in {finding.code for finding in result.findings}
    assert storage_file.is_file()
    assert (tmp_path / ".codex" / "repair_requests" / "repair_requests.jsonl").exists()


def test_cli_decide_writes_strategy_decision(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    forecast = _forecast("forecast:latest", anchor_time=now, status="pending")
    repository.save_forecast(forecast)

    exit_code = main(
        [
            "decide",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-24T12:00:00+00:00",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["action"] == "HOLD"
    assert (tmp_path / "strategy_decisions.jsonl").exists()


def test_cli_decide_fail_closed_on_corrupt_storage(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    storage = tmp_path / "storage"
    storage.mkdir()
    (storage / "forecasts.jsonl").write_text("{bad json\n", encoding="utf-8")

    exit_code = main(
        [
            "decide",
            "--storage-dir",
            str(storage),
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-24T12:00:00+00:00",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["action"] == "STOP_NEW_ENTRIES"
    assert payload["blocked_reason"] == "health_check_repair_required"
    assert (storage / "strategy_decisions.jsonl").exists()
    assert (storage / "repair_requests.jsonl").exists()


def test_cli_decide_missing_storage_does_not_create_typo_path(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    missing = tmp_path / "missing-decide-storage"

    exit_code = main(
        [
            "decide",
            "--storage-dir",
            str(missing),
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-24T12:00:00+00:00",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["action"] == "STOP_NEW_ENTRIES"
    assert payload["blocked_reason"] == "health_check_repair_required"
    assert not missing.exists()
    assert (tmp_path / ".codex" / "repair_requests" / "repair_requests.jsonl").exists()


def test_cli_decide_file_storage_path_fails_closed_without_traceback(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    storage_file = tmp_path / "storage-is-file"
    storage_file.write_text("not a directory", encoding="utf-8")

    exit_code = main(
        [
            "decide",
            "--storage-dir",
            str(storage_file),
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-24T12:00:00+00:00",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["action"] == "STOP_NEW_ENTRIES"
    assert payload["blocked_reason"] == "health_check_repair_required"
    assert storage_file.is_file()
    assert (tmp_path / ".codex" / "repair_requests" / "repair_requests.jsonl").exists()


def test_cli_run_once_also_decide_writes_one_command_strategy_decision(tmp_path, capsys):
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
            "2026-04-24T12:00:00+00:00",
            "--also-decide",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["decision_action"] == "HOLD"
    assert payload["automation_run_id"].startswith("automation-run:")
    assert payload["notification_count"] >= 1
    assert (tmp_path / "forecasts.jsonl").exists()
    assert (tmp_path / "strategy_decisions.jsonl").exists()
    assert (tmp_path / "notification_artifacts.jsonl").exists()
    notifications = JsonFileRepository(tmp_path).load_notification_artifacts()
    notification_types = {notification.notification_type for notification in notifications}
    assert "NEW_DECISION" in notification_types
    assert "BUY_SELL_BLOCKED" in notification_types
    automation_runs = JsonFileRepository(tmp_path).load_automation_runs()
    assert len(automation_runs) == 1
    run = automation_runs[0]
    assert run.status == "completed"
    assert run.symbol == "BTC-USD"
    assert run.provider == "sample"
    assert run.command == "run-once"
    assert run.health_check_id is not None
    assert run.decision_id == payload["decision_id"]
    assert run.repair_request_id is None
    step_names = [step["name"] for step in run.steps]
    assert step_names == [
        "forecast",
        "score",
        "review",
        "proposal",
        "health_check",
        "risk_check",
        "decide",
        "notifications",
    ]


def test_health_check_audits_bad_and_duplicate_automation_runs(tmp_path):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_forecast(_forecast("forecast:latest", anchor_time=now, status="pending"))
    main(
        [
            "run-once",
            "--provider",
            "sample",
            "--symbol",
            "BTC-USD",
            "--storage-dir",
            str(tmp_path),
            "--now",
            now.isoformat(),
            "--also-decide",
        ]
    )
    run_payload = JsonFileRepository(tmp_path).load_automation_runs()[0].to_dict()
    (tmp_path / "automation_runs.jsonl").write_text(
        "\n".join([json.dumps(run_payload), json.dumps(run_payload), "{bad json"]) + "\n",
        encoding="utf-8",
    )

    result = run_health_check(
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=now,
        create_repair_request=False,
    )
    codes = {finding.code for finding in result.findings}

    assert result.repair_required is True
    assert "bad_json_row" in codes
    assert "duplicate_automation_run_id" in codes


def test_health_check_audits_bad_and_duplicate_notification_artifacts(tmp_path):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_forecast(_forecast("forecast:latest", anchor_time=now, status="pending"))
    main(
        [
            "run-once",
            "--provider",
            "sample",
            "--symbol",
            "BTC-USD",
            "--storage-dir",
            str(tmp_path),
            "--now",
            now.isoformat(),
            "--also-decide",
        ]
    )
    notification_payload = JsonFileRepository(tmp_path).load_notification_artifacts()[0].to_dict()
    (tmp_path / "notification_artifacts.jsonl").write_text(
        "\n".join([json.dumps(notification_payload), json.dumps(notification_payload), "{bad json"]) + "\n",
        encoding="utf-8",
    )

    result = run_health_check(
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=now,
        create_repair_request=False,
    )
    codes = {finding.code for finding in result.findings}

    assert result.repair_required is True
    assert "bad_json_row" in codes
    assert "duplicate_notification_id" in codes


def test_cli_health_check_reports_missing_storage_without_creating_it(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    missing = tmp_path / "missing-storage"

    exit_code = main(
        [
            "health-check",
            "--storage-dir",
            str(missing),
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-24T12:00:00+00:00",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["repair_required"] is True
    assert payload["repair_request_id"] is not None
    assert not missing.exists()
