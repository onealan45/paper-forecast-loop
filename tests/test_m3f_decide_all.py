from datetime import UTC, datetime, timedelta
import json

import pytest

from forecast_loop.cli import main
from forecast_loop.health import run_health_check
from forecast_loop.models import Forecast
from forecast_loop.storage import JsonFileRepository


def _forecast(symbol: str, forecast_id: str, now: datetime) -> Forecast:
    return Forecast(
        forecast_id=forecast_id,
        symbol=symbol,
        created_at=now,
        anchor_time=now,
        target_window_start=now,
        target_window_end=now + timedelta(hours=24),
        candle_interval_minutes=60,
        expected_candle_count=24,
        status="pending",
        status_reason="awaiting_horizon_end",
        predicted_regime="trend_up",
        confidence=0.6,
        provider_data_through=now,
        observed_candle_count=0,
    )


def test_cli_decide_all_generates_independent_per_symbol_decisions(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    for symbol in ["BTC-USD", "ETH-USD", "SPY"]:
        repository.save_forecast(_forecast(symbol, f"forecast:{symbol}", now))
    (tmp_path / "last_run_meta.json").write_text(
        json.dumps(
            {
                "symbol": "BTC-USD",
                "new_forecast": {"forecast_id": "forecast:BTC-USD", "symbol": "BTC-USD"},
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "decide-all",
            "--storage-dir",
            str(tmp_path),
            "--symbols",
            "BTC-USD,ETH-USD,SPY,BTC-USD",
            "--now",
            "2026-04-24T12:00:00+00:00",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["symbols"] == ["BTC-USD", "ETH-USD", "SPY"]
    assert payload["decision_count"] == 3
    assert [decision["symbol"] for decision in payload["decisions"]] == ["BTC-USD", "ETH-USD", "SPY"]
    assert {decision["action"] for decision in payload["decisions"]} == {"HOLD"}
    assert len(repository.load_strategy_decisions()) == 3
    assert {baseline.symbol for baseline in repository.load_baseline_evaluations()} == {
        "BTC-USD",
        "ETH-USD",
        "SPY",
    }


def test_health_check_ignores_last_run_meta_for_other_symbol(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_forecast(_forecast("ETH-USD", "forecast:eth", now))
    (tmp_path / "last_run_meta.json").write_text(
        json.dumps(
            {
                "symbol": "BTC-USD",
                "new_forecast": {"forecast_id": "forecast:btc", "symbol": "BTC-USD"},
            }
        ),
        encoding="utf-8",
    )

    result = run_health_check(storage_dir=tmp_path, symbol="ETH-USD", now=now, create_repair_request=False)

    assert "last_run_meta_mismatch" not in {finding.code for finding in result.findings}


def test_cli_decide_all_fail_closes_missing_symbol_forecast(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_forecast(_forecast("BTC-USD", "forecast:btc", now))

    exit_code = main(
        [
            "decide-all",
            "--storage-dir",
            str(tmp_path),
            "--symbols",
            "BTC-USD,SPY",
            "--now",
            "2026-04-24T12:00:00+00:00",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    decisions_by_symbol = {decision["symbol"]: decision for decision in payload["decisions"]}

    assert exit_code == 0
    assert payload["decision_count"] == 2
    assert decisions_by_symbol["BTC-USD"]["action"] == "HOLD"
    assert decisions_by_symbol["SPY"]["action"] == "STOP_NEW_ENTRIES"
    assert decisions_by_symbol["SPY"]["blocked_reason"] == "health_check_repair_required"
    assert (tmp_path / "repair_requests.jsonl").exists()


def test_cli_decide_all_rejects_unsupported_symbol_without_traceback(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "decide-all",
                "--storage-dir",
                str(tmp_path / "storage"),
                "--symbols",
                "BTC-USD,BAD",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "unsupported asset symbol(s): BAD" in captured.err
    assert "Traceback" not in captured.err
    assert not (tmp_path / "storage").exists()
