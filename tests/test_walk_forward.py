from datetime import UTC, datetime, timedelta
import json

import pytest

from forecast_loop.cli import main
from forecast_loop.health import run_health_check
from forecast_loop.models import MarketCandleRecord, WalkForwardValidation, WalkForwardWindow
from forecast_loop.storage import JsonFileRepository


def _candle(index: int, close: float) -> MarketCandleRecord:
    timestamp = datetime(2026, 4, 1, tzinfo=UTC) + timedelta(days=index)
    return MarketCandleRecord(
        candle_id=f"market-candle:wf:{index}",
        symbol="BTC-USD",
        timestamp=timestamp,
        open=close - 1,
        high=close + 1,
        low=close - 2,
        close=close,
        volume=1000 + index,
        source="fixture",
        imported_at=datetime(2026, 4, 24, tzinfo=UTC),
    )


def _seed_candles(repository: JsonFileRepository, closes: list[float]) -> None:
    for index, close in enumerate(closes):
        repository.save_market_candle(_candle(index, close))


def test_cli_walk_forward_asof_uses_plan_time_candles_and_ignores_later_revisions(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    plan_time = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_candles(repository, [100, 102, 104, 101, 103, 106, 105, 107, 109])
    later_revision = _candle(8, 999)
    later_revision.candle_id = "market-candle:wf:late-revision"
    later_revision.imported_at = plan_time + timedelta(hours=1)
    repository.save_market_candle(later_revision)

    exit_code = main(
        [
            "walk-forward",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--start",
            "2026-04-01T00:00:00+00:00",
            "--end",
            "2026-04-09T00:00:00+00:00",
            "--created-at",
            "2026-04-24T12:30:00+00:00",
            "--as-of",
            "2026-04-24T12:00:00+00:00",
            "--train-size",
            "3",
            "--validation-size",
            "3",
            "--test-size",
            "3",
            "--step-size",
            "3",
            "--moving-average-window",
            "2",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["validation"]["window_count"] == 1
    assert payload["validation"]["decision_basis"].endswith("; as_of=2026-04-24T12:00:00+00:00")
    for run in repository.load_backtest_runs():
        assert "market-candle:wf:late-revision" not in run.candle_ids
        assert "as_of=2026-04-24T12:00:00+00:00" in run.decision_basis


def test_cli_walk_forward_asof_uses_latest_revision_imported_before_asof(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    plan_time = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _seed_candles(repository, [100, 102, 104, 101, 103, 106, 105, 107, 109])
    before_asof_revision = _candle(8, 111)
    before_asof_revision.candle_id = "market-candle:wf:before-asof-revision"
    before_asof_revision.imported_at = plan_time - timedelta(minutes=5)
    repository.save_market_candle(before_asof_revision)

    exit_code = main(
        [
            "walk-forward",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--start",
            "2026-04-01T00:00:00+00:00",
            "--end",
            "2026-04-09T00:00:00+00:00",
            "--created-at",
            "2026-04-24T12:30:00+00:00",
            "--as-of",
            "2026-04-24T12:00:00+00:00",
            "--train-size",
            "3",
            "--validation-size",
            "3",
            "--test-size",
            "3",
            "--step-size",
            "3",
            "--moving-average-window",
            "2",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    backtest_runs = repository.load_backtest_runs()

    assert exit_code == 0
    assert payload["validation"]["window_count"] == 1
    assert any("market-candle:wf:before-asof-revision" in run.candle_ids for run in backtest_runs)
    assert not any("market-candle:wf:8" in run.candle_ids for run in backtest_runs)


def test_cli_walk_forward_asof_rejects_window_after_asof(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    _seed_candles(repository, [100, 102, 104, 101, 103, 106])

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "walk-forward",
                "--storage-dir",
                str(tmp_path),
                "--start",
                "2026-04-01T00:00:00+00:00",
                "--end",
                "2026-04-06T00:00:00+00:00",
                "--as-of",
                "2026-04-05T00:00:00+00:00",
                "--train-size",
                "2",
                "--validation-size",
                "2",
                "--test-size",
                "2",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "walk-forward end must be <= as_of" in captured.err
    assert "Traceback" not in captured.err


def test_cli_walk_forward_writes_windows_metrics_and_artifacts(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    _seed_candles(repository, [100, 102, 104, 101, 103, 106, 105, 107, 109, 108, 110, 111])

    exit_code = main(
        [
            "walk-forward",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--start",
            "2026-04-01T00:00:00+00:00",
            "--end",
            "2026-04-12T00:00:00+00:00",
            "--created-at",
            "2026-04-24T12:00:00+00:00",
            "--train-size",
            "3",
            "--validation-size",
            "3",
            "--test-size",
            "3",
            "--step-size",
            "2",
            "--moving-average-window",
            "2",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    validation = payload["validation"]

    assert exit_code == 0
    assert validation["strategy_name"] == "moving_average_trend"
    assert validation["window_count"] == 2
    assert validation["train_size"] == 3
    assert validation["validation_size"] == 3
    assert validation["test_size"] == 3
    assert validation["step_size"] == 2
    assert validation["moving_average_window"] == 2
    assert len(validation["backtest_result_ids"]) == 4
    assert validation["windows"][0]["train_end"] < validation["windows"][0]["validation_start"]
    assert validation["windows"][0]["validation_end"] < validation["windows"][0]["test_start"]
    assert "average_test_return" in validation
    assert "average_benchmark_return" in validation
    assert "average_excess_return" in validation
    assert len(repository.load_walk_forward_validations()) == 1
    assert len(repository.load_backtest_results()) == 4


def test_cli_walk_forward_requires_enough_candles(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    _seed_candles(repository, [100, 102, 104, 101])

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "walk-forward",
                "--storage-dir",
                str(tmp_path),
                "--start",
                "2026-04-01T00:00:00+00:00",
                "--end",
                "2026-04-04T00:00:00+00:00",
                "--train-size",
                "2",
                "--validation-size",
                "2",
                "--test-size",
                "2",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "walk-forward requires at least 6 candles" in captured.err
    assert "Traceback" not in captured.err


def test_cli_walk_forward_rejects_duplicate_timestamps(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    for index, close in enumerate([100, 101, 102, 103, 104, 105]):
        candle = _candle(index, close)
        if index == 3:
            candle.timestamp = _candle(2, 102).timestamp
            candle.candle_id = "market-candle:wf:duplicate"
        repository.save_market_candle(candle)

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "walk-forward",
                "--storage-dir",
                str(tmp_path),
                "--start",
                "2026-04-01T00:00:00+00:00",
                "--end",
                "2026-04-06T00:00:00+00:00",
                "--train-size",
                "2",
                "--validation-size",
                "2",
                "--test-size",
                "2",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "strictly increasing timestamps" in captured.err
    assert "Traceback" not in captured.err


def test_health_check_detects_walk_forward_missing_backtest_result(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, tzinfo=UTC)
    window = WalkForwardWindow(
        window_id="walk-forward-window:broken",
        train_start=now,
        train_end=now + timedelta(days=1),
        validation_start=now + timedelta(days=2),
        validation_end=now + timedelta(days=3),
        test_start=now + timedelta(days=4),
        test_end=now + timedelta(days=5),
        train_candle_count=2,
        validation_candle_count=2,
        test_candle_count=2,
        validation_backtest_result_id="backtest-result:missing-validation",
        test_backtest_result_id="backtest-result:missing-test",
        validation_return=0.01,
        test_return=-0.01,
        benchmark_return=0.0,
        excess_return=-0.01,
        overfit_flags=["validation_positive_test_nonpositive"],
        decision_basis="test",
    )
    repository.save_walk_forward_validation(
        WalkForwardValidation(
            validation_id="walk-forward:broken",
            created_at=now,
            symbol="BTC-USD",
            start=now,
            end=now + timedelta(days=5),
            strategy_name="moving_average_trend",
            train_size=2,
            validation_size=2,
            test_size=2,
            step_size=1,
            initial_cash=10_000,
            fee_bps=5,
            slippage_bps=10,
            moving_average_window=2,
            window_count=1,
            average_validation_return=0.01,
            average_test_return=-0.01,
            average_benchmark_return=0.0,
            average_excess_return=-0.01,
            test_win_rate=0.0,
            overfit_window_count=1,
            overfit_risk_flags=["validation_positive_test_nonpositive"],
            backtest_result_ids=["backtest-result:missing-validation", "backtest-result:missing-test"],
            windows=[window],
            decision_basis="test",
        )
    )

    result = run_health_check(storage_dir=tmp_path, symbol="BTC-USD", now=now, create_repair_request=False)

    assert "walk_forward_missing_backtest_result" in {finding.code for finding in result.findings}
