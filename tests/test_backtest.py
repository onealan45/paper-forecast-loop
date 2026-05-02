from datetime import UTC, datetime, timedelta
import json
from hashlib import sha1

import pytest

from forecast_loop.cli import main
from forecast_loop.health import run_health_check
from forecast_loop.models import BacktestResult, BacktestRun, MarketCandleRecord
from forecast_loop.storage import JsonFileRepository


def _candle(index: int, close: float) -> MarketCandleRecord:
    timestamp = datetime(2026, 4, 1, tzinfo=UTC) + timedelta(days=index)
    return MarketCandleRecord(
        candle_id=f"market-candle:bt:{index}",
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


def test_cli_backtest_asof_uses_plan_time_candles_and_ignores_later_revisions(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    plan_time = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    for index, close in enumerate([100, 102, 104]):
        repository.save_market_candle(_candle(index, close))
    later_revision = _candle(1, 999)
    later_revision.candle_id = "market-candle:bt:late-revision"
    later_revision.imported_at = plan_time + timedelta(hours=1)
    repository.save_market_candle(later_revision)

    exit_code = main(
        [
            "backtest",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--start",
            "2026-04-01T00:00:00+00:00",
            "--end",
            "2026-04-03T00:00:00+00:00",
            "--created-at",
            "2026-04-24T12:30:00+00:00",
            "--as-of",
            "2026-04-24T12:00:00+00:00",
            "--moving-average-window",
            "2",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["run"]["candle_ids"] == [
        "market-candle:bt:0",
        "market-candle:bt:1",
        "market-candle:bt:2",
    ]
    assert payload["run"]["decision_basis"].endswith("; as_of=2026-04-24T12:00:00+00:00")
    assert abs(payload["result"]["benchmark_return"] - 0.04) < 1e-12


def test_cli_backtest_asof_rejects_window_after_asof(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    _seed_candles(repository, [100, 102, 104])

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "backtest",
                "--storage-dir",
                str(tmp_path),
                "--symbol",
                "BTC-USD",
                "--start",
                "2026-04-01T00:00:00+00:00",
                "--end",
                "2026-04-03T00:00:00+00:00",
                "--as-of",
                "2026-04-02T00:00:00+00:00",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "backtest end must be <= as_of" in captured.err
    assert "Traceback" not in captured.err


def test_cli_backtest_writes_metrics_and_artifacts(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    _seed_candles(repository, [100, 102, 104, 101, 103, 106])

    exit_code = main(
        [
            "backtest",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--start",
            "2026-04-01T00:00:00+00:00",
            "--end",
            "2026-04-06T00:00:00+00:00",
            "--created-at",
            "2026-04-24T12:00:00+00:00",
            "--initial-cash",
            "10000",
            "--fee-bps",
            "5",
            "--slippage-bps",
            "10",
            "--moving-average-window",
            "2",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    result = payload["result"]

    assert exit_code == 0
    assert payload["run"]["strategy_name"] == "moving_average_trend"
    assert payload["run"]["moving_average_window"] == 2
    assert result["trade_count"] >= 1
    assert result["final_equity"] > 0
    assert abs(result["benchmark_return"] - 0.06) < 1e-12
    assert result["max_drawdown"] >= 0
    assert result["turnover"] > 0
    assert len(result["equity_curve"]) == 6
    assert len(repository.load_backtest_runs()) == 1
    assert len(repository.load_backtest_results()) == 1


def test_backtest_window_is_part_of_artifact_identity(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    _seed_candles(repository, [100, 102, 104, 101, 103, 106])

    common_args = [
        "backtest",
        "--storage-dir",
        str(tmp_path),
        "--symbol",
        "BTC-USD",
        "--start",
        "2026-04-01T00:00:00+00:00",
        "--end",
        "2026-04-06T00:00:00+00:00",
        "--created-at",
        "2026-04-24T12:00:00+00:00",
    ]

    assert main([*common_args, "--moving-average-window", "2"]) == 0
    first_payload = json.loads(capsys.readouterr().out)
    assert main([*common_args, "--moving-average-window", "4"]) == 0
    second_payload = json.loads(capsys.readouterr().out)

    assert first_payload["run"]["moving_average_window"] == 2
    assert second_payload["run"]["moving_average_window"] == 4
    assert first_payload["run"]["backtest_id"] != second_payload["run"]["backtest_id"]
    assert len(repository.load_backtest_runs()) == 2


def test_backtest_run_id_preserves_generic_identity_without_context():
    payload = {
        "symbol": "BTC-USD",
        "start": "2026-04-01T00:00:00+00:00",
        "end": "2026-04-06T00:00:00+00:00",
        "strategy_name": "moving_average_trend",
        "initial_cash": 10000.0,
        "fee_bps": 5.0,
        "slippage_bps": 10.0,
        "moving_average_window": 2,
        "candle_ids": ["market-candle:bt:0", "market-candle:bt:1"],
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = sha1(serialized).hexdigest()[:16]

    assert BacktestRun.build_id(
        symbol="BTC-USD",
        start=datetime(2026, 4, 1, tzinfo=UTC),
        end=datetime(2026, 4, 6, tzinfo=UTC),
        strategy_name="moving_average_trend",
        initial_cash=10000.0,
        fee_bps=5.0,
        slippage_bps=10.0,
        moving_average_window=2,
        candle_ids=["market-candle:bt:1", "market-candle:bt:0"],
    ) == f"backtest-run:{digest}"


def test_cli_backtest_missing_storage_is_operator_friendly(tmp_path, capsys):
    missing = tmp_path / "missing-storage"

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "backtest",
                "--storage-dir",
                str(missing),
                "--start",
                "2026-04-01T00:00:00+00:00",
                "--end",
                "2026-04-06T00:00:00+00:00",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "storage directory does not exist" in captured.err
    assert "Traceback" not in captured.err
    assert not missing.exists()


def test_cli_backtest_requires_enough_candles(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    repository.save_market_candle(_candle(0, 100))

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "backtest",
                "--storage-dir",
                str(tmp_path),
                "--start",
                "2026-04-01T00:00:00+00:00",
                "--end",
                "2026-04-06T00:00:00+00:00",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "at least 2 candles" in captured.err
    assert "Traceback" not in captured.err


def test_cli_backtest_rejects_duplicate_timestamps(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    first = _candle(0, 100)
    duplicate = _candle(0, 101)
    duplicate.candle_id = "market-candle:duplicate"
    duplicate.source = "fixture-secondary"
    repository.save_market_candle(first)
    repository.save_market_candle(duplicate)

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "backtest",
                "--storage-dir",
                str(tmp_path),
                "--start",
                "2026-04-01T00:00:00+00:00",
                "--end",
                "2026-04-01T00:00:00+00:00",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "strictly increasing timestamps" in captured.err
    assert "Traceback" not in captured.err


def test_health_check_detects_backtest_result_missing_run(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, tzinfo=UTC)
    repository.save_backtest_result(
        BacktestResult(
            result_id="backtest-result:broken",
            backtest_id="backtest-run:missing",
            created_at=now,
            symbol="BTC-USD",
            start=now,
            end=now + timedelta(days=1),
            initial_cash=10_000,
            final_equity=10_100,
            strategy_return=0.01,
            benchmark_return=0.02,
            max_drawdown=0.0,
            sharpe=None,
            turnover=1.0,
            win_rate=None,
            trade_count=1,
            equity_curve=[],
            decision_basis="test",
        )
    )

    result = run_health_check(storage_dir=tmp_path, symbol="BTC-USD", now=now, create_repair_request=False)

    assert "backtest_result_missing_run" in {finding.code for finding in result.findings}


def test_health_check_detects_backtest_run_missing_candle(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, tzinfo=UTC)
    repository.save_market_candle(_candle(0, 100))
    repository.save_backtest_run(
        BacktestRun(
            backtest_id="backtest-run:broken",
            created_at=now,
            symbol="BTC-USD",
            start=now,
            end=now + timedelta(days=1),
            strategy_name="moving_average_trend",
            initial_cash=10_000,
            fee_bps=5,
            slippage_bps=10,
            moving_average_window=3,
            candle_ids=["market-candle:missing"],
            decision_basis="test",
        )
    )

    result = run_health_check(storage_dir=tmp_path, symbol="BTC-USD", now=now, create_repair_request=False)

    assert "backtest_run_missing_candle" in {finding.code for finding in result.findings}
