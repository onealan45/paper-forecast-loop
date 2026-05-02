from datetime import UTC, datetime, timedelta
import json

from forecast_loop.cli import main
from forecast_loop.health import run_health_check
from forecast_loop.models import (
    BacktestResult,
    BacktestRun,
    ExperimentTrial,
    Forecast,
    WalkForwardValidation,
)
from forecast_loop.revision_retest import RETEST_PROTOCOL_VERSION
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


def _jsonl_payloads(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _backtest_run(*, backtest_id: str, context: str) -> BacktestRun:
    return BacktestRun(
        backtest_id=backtest_id,
        created_at=datetime(2026, 5, 1, 10, tzinfo=UTC),
        symbol="BTC-USD",
        start=datetime(2026, 1, 8, tzinfo=UTC),
        end=datetime(2026, 1, 10, tzinfo=UTC),
        strategy_name="moving_average_trend",
        initial_cash=10000,
        fee_bps=5,
        slippage_bps=5,
        moving_average_window=3,
        candle_ids=[],
        decision_basis=f"test; id_context={context}",
    )


def _backtest_result(*, result_id: str, backtest_id: str) -> BacktestResult:
    return BacktestResult(
        result_id=result_id,
        backtest_id=backtest_id,
        created_at=datetime(2026, 5, 1, 10, 30, tzinfo=UTC),
        symbol="BTC-USD",
        start=datetime(2026, 1, 8, tzinfo=UTC),
        end=datetime(2026, 1, 10, tzinfo=UTC),
        initial_cash=10000,
        final_equity=10100,
        strategy_return=0.01,
        benchmark_return=0.005,
        max_drawdown=0.02,
        sharpe=None,
        turnover=1.0,
        win_rate=None,
        trade_count=1,
        equity_curve=[],
        decision_basis="test",
    )


def _walk_forward(
    *,
    validation_id: str,
    backtest_result_id: str,
    context: str,
) -> WalkForwardValidation:
    return WalkForwardValidation(
        validation_id=validation_id,
        created_at=datetime(2026, 5, 1, 11, tzinfo=UTC),
        symbol="BTC-USD",
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 1, 10, tzinfo=UTC),
        strategy_name="moving_average_trend",
        train_size=3,
        validation_size=2,
        test_size=2,
        step_size=1,
        initial_cash=10000,
        fee_bps=5,
        slippage_bps=5,
        moving_average_window=3,
        window_count=0,
        average_validation_return=0,
        average_test_return=0,
        average_benchmark_return=0,
        average_excess_return=0,
        test_win_rate=0,
        overfit_window_count=0,
        overfit_risk_flags=[],
        backtest_result_ids=[backtest_result_id],
        windows=[],
        decision_basis=f"test; id_context={context}",
    )


def _retest_trial(
    *,
    trial_id: str,
    strategy_card_id: str,
    source_outcome_id: str,
    backtest_result_id: str,
    walk_forward_validation_id: str,
) -> ExperimentTrial:
    return ExperimentTrial(
        trial_id=trial_id,
        created_at=datetime(2026, 5, 1, 12, tzinfo=UTC),
        strategy_card_id=strategy_card_id,
        trial_index=1,
        status="PASSED",
        symbol="BTC-USD",
        seed=7,
        dataset_id="research-dataset:retest",
        backtest_result_id=backtest_result_id,
        walk_forward_validation_id=walk_forward_validation_id,
        event_edge_evaluation_id=None,
        prompt_hash=None,
        code_hash=None,
        parameters={
            "revision_retest_protocol": RETEST_PROTOCOL_VERSION,
            "revision_retest_source_card_id": strategy_card_id,
            "revision_source_outcome_id": source_outcome_id,
        },
        metric_summary={},
        failure_reason=None,
        started_at=datetime(2026, 5, 1, 9, tzinfo=UTC),
        completed_at=datetime(2026, 5, 1, 12, tzinfo=UTC),
        decision_basis="test",
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
    quarantined = _jsonl_payloads(quarantine_path)
    assert [item["forecast_id"] for item in quarantined] == ["legacy-1"]
    assert report["quarantined_forecast_count"] == 1
    assert report["kept_forecast_count"] == 1
    assert datetime.fromisoformat(report["generated_at_utc"]).tzinfo is not None
    assert report["active_forecast_count"] == 1
    assert report["latest_forecast_id"] == "current-1"


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
    quarantined = _jsonl_payloads(quarantine_path)

    assert first_exit == 0
    assert second_exit == 0
    assert repository.load_forecasts() == []
    assert len(quarantined) == 1
    assert report["quarantined_forecast_count"] == 0
    assert report["kept_forecast_count"] == 0
    assert report["active_forecast_count"] == 0
    assert report["latest_forecast_id"] is None


def test_repair_storage_reports_clean_storage_without_changes(tmp_path):
    exit_code = main(["repair-storage", "--storage-dir", str(tmp_path)])

    report = json.loads((tmp_path / "storage_repair_report.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert report["quarantined_forecast_count"] == 0
    assert report["kept_forecast_count"] == 0
    assert report["active_forecast_count"] == 0
    assert report["latest_forecast_id"] is None
    assert datetime.fromisoformat(report["generated_at_utc"]).tzinfo is not None
    assert report["status"] == "no_legacy_forecasts_found"


def test_repair_storage_quarantines_bad_retest_context_trials(tmp_path):
    repository = JsonFileRepository(tmp_path)
    good_context = "revision_retest:strategy-card:good:experiment-trial:good:paper-shadow-outcome:good"
    bad_context = "revision_retest:strategy-card:other:experiment-trial:other:paper-shadow-outcome:other"
    repository.save_backtest_run(_backtest_run(backtest_id="backtest-run:good", context=good_context))
    repository.save_backtest_result(_backtest_result(result_id="backtest-result:good", backtest_id="backtest-run:good"))
    repository.save_walk_forward_validation(
        _walk_forward(
            validation_id="walk-forward:good",
            backtest_result_id="backtest-result:good",
            context=good_context,
        )
    )
    repository.save_backtest_run(_backtest_run(backtest_id="backtest-run:bad", context=bad_context))
    repository.save_backtest_result(_backtest_result(result_id="backtest-result:bad", backtest_id="backtest-run:bad"))
    repository.save_walk_forward_validation(
        _walk_forward(
            validation_id="walk-forward:bad",
            backtest_result_id="backtest-result:bad",
            context=bad_context,
        )
    )
    good_trial = _retest_trial(
        trial_id="experiment-trial:good",
        strategy_card_id="strategy-card:good",
        source_outcome_id="paper-shadow-outcome:good",
        backtest_result_id="backtest-result:good",
        walk_forward_validation_id="walk-forward:good",
    )
    bad_trial = _retest_trial(
        trial_id="experiment-trial:bad",
        strategy_card_id="strategy-card:bad",
        source_outcome_id="paper-shadow-outcome:bad",
        backtest_result_id="backtest-result:bad",
        walk_forward_validation_id="walk-forward:bad",
    )
    repository.save_experiment_trial(good_trial)
    repository.save_experiment_trial(bad_trial)

    exit_code = main(["repair-storage", "--storage-dir", str(tmp_path)])

    report = json.loads((tmp_path / "storage_repair_report.json").read_text(encoding="utf-8"))
    quarantine_path = tmp_path / "quarantine" / "retest_context_experiment_trials.jsonl"
    remaining_trials = JsonFileRepository(tmp_path).load_experiment_trials()
    quarantined = _jsonl_payloads(quarantine_path)
    health = run_health_check(
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=datetime(2026, 5, 1, 13, tzinfo=UTC),
        create_repair_request=False,
    )
    codes = {finding.code for finding in health.findings}

    assert exit_code == 0
    assert [trial.trial_id for trial in remaining_trials] == ["experiment-trial:good"]
    assert [trial["trial_id"] for trial in quarantined] == ["experiment-trial:bad"]
    assert report["quarantined_retest_trial_count"] == 1
    assert report["active_experiment_trial_count"] == 1
    assert report["latest_experiment_trial_id"] == "experiment-trial:good"
    assert report["status"] == "retest_context_trials_quarantined"
    assert "revision_retest_passed_trial_backtest_context_mismatch" not in codes
    assert "revision_retest_passed_trial_walk_forward_context_mismatch" not in codes


def test_repair_storage_retest_context_quarantine_is_idempotent(tmp_path):
    repository = JsonFileRepository(tmp_path)
    repository.save_backtest_run(_backtest_run(backtest_id="backtest-run:bad", context="revision_retest:other"))
    repository.save_backtest_result(_backtest_result(result_id="backtest-result:bad", backtest_id="backtest-run:bad"))
    repository.save_walk_forward_validation(
        _walk_forward(
            validation_id="walk-forward:bad",
            backtest_result_id="backtest-result:bad",
            context="revision_retest:other",
        )
    )
    repository.save_experiment_trial(
        _retest_trial(
            trial_id="experiment-trial:bad",
            strategy_card_id="strategy-card:bad",
            source_outcome_id="paper-shadow-outcome:bad",
            backtest_result_id="backtest-result:bad",
            walk_forward_validation_id="walk-forward:bad",
        )
    )

    first_exit = main(["repair-storage", "--storage-dir", str(tmp_path)])
    second_exit = main(["repair-storage", "--storage-dir", str(tmp_path)])

    report = json.loads((tmp_path / "storage_repair_report.json").read_text(encoding="utf-8"))
    quarantine_path = tmp_path / "quarantine" / "retest_context_experiment_trials.jsonl"
    quarantined = _jsonl_payloads(quarantine_path)

    assert first_exit == 0
    assert second_exit == 0
    assert JsonFileRepository(tmp_path).load_experiment_trials() == []
    assert [trial["trial_id"] for trial in quarantined] == ["experiment-trial:bad"]
    assert report["quarantined_retest_trial_count"] == 0
    assert report["active_experiment_trial_count"] == 0
    assert report["latest_experiment_trial_id"] is None
