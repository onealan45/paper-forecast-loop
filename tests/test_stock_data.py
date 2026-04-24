from datetime import UTC, datetime
import csv
import json

import pytest

from forecast_loop.cli import main
from forecast_loop.models import MarketCandle, MarketCandleRecord
from forecast_loop.stock_data import StockCsvFixtureProvider
from forecast_loop.storage import JsonFileRepository


def _write_stock_csv(path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["date", "open", "high", "low", "close", "adjusted_close", "volume"],
        )
        writer.writeheader()
        writer.writerows(rows)


def _stock_row(trading_date: str, close: float, adjusted_close: float | None = None) -> dict:
    return {
        "date": trading_date,
        "open": close - 1,
        "high": close + 1,
        "low": close - 2,
        "close": close,
        "adjusted_close": adjusted_close if adjusted_close is not None else close,
        "volume": 1_000,
    }


def test_market_calendar_skips_weekends_and_us_holiday(capsys):
    assert main(
        [
            "market-calendar",
            "--market",
            "US",
            "--start-date",
            "2026-04-02",
            "--end-date",
            "2026-04-06",
        ]
    ) == 0
    result = json.loads(capsys.readouterr().out)

    assert result["session_count"] == 2
    assert [session["trading_date"] for session in result["sessions"]] == ["2026-04-02", "2026-04-06"]
    assert result["sessions"][0]["close_utc"] == "2026-04-02T20:00:00+00:00"


def test_import_stock_csv_skips_non_trading_days_and_preserves_adjusted_close(tmp_path, capsys):
    csv_path = tmp_path / "spy.csv"
    _write_stock_csv(
        csv_path,
        [
            _stock_row("2026-04-02", close=105, adjusted_close=100),
            _stock_row("2026-04-03", close=106, adjusted_close=101),
            _stock_row("2026-04-06", close=107, adjusted_close=102),
        ],
    )

    assert main(
        [
            "import-stock-csv",
            "--storage-dir",
            str(tmp_path / "storage"),
            "--input",
            str(csv_path),
            "--symbol",
            "SPY",
            "--source",
            "fixture",
            "--imported-at",
            "2026-04-24T12:00:00+00:00",
        ]
    ) == 0
    result = json.loads(capsys.readouterr().out)
    records = JsonFileRepository(tmp_path / "storage").load_market_candles()

    assert result["imported_count"] == 2
    assert result["skipped_non_trading_day_count"] == 1
    assert [record.timestamp.isoformat() for record in records] == [
        "2026-04-02T20:00:00+00:00",
        "2026-04-06T20:00:00+00:00",
    ]
    assert records[0].adjusted_close == 100
    assert records[0].to_candle().close == 100


def test_stock_candle_health_ignores_holiday_gap_but_flags_missing_trading_day(tmp_path, capsys):
    csv_path = tmp_path / "spy.csv"
    _write_stock_csv(
        csv_path,
        [
            _stock_row("2026-04-02", close=105, adjusted_close=100),
            _stock_row("2026-04-03", close=106, adjusted_close=101),
        ],
    )
    assert main(
        [
            "import-stock-csv",
            "--storage-dir",
            str(tmp_path / "storage"),
            "--input",
            str(csv_path),
            "--symbol",
            "SPY",
            "--source",
            "fixture",
            "--imported-at",
            "2026-04-24T12:00:00+00:00",
        ]
    ) == 0
    capsys.readouterr()

    assert main(
        [
            "stock-candle-health",
            "--storage-dir",
            str(tmp_path / "storage"),
            "--symbol",
            "SPY",
            "--start-date",
            "2026-04-02",
            "--end-date",
            "2026-04-06",
        ]
    ) == 2
    result = json.loads(capsys.readouterr().out)
    codes = {finding["code"] for finding in result["findings"]}

    assert result["missing_session_count"] == 1
    assert result["missing_session_closes_utc"] == ["2026-04-06T20:00:00+00:00"]
    assert "missing_stock_session" in codes


def test_stock_candle_health_is_healthy_when_trading_days_are_covered(tmp_path, capsys):
    csv_path = tmp_path / "spy.csv"
    _write_stock_csv(
        csv_path,
        [
            _stock_row("2026-04-02", close=105, adjusted_close=100),
            _stock_row("2026-04-03", close=106, adjusted_close=101),
            _stock_row("2026-04-06", close=107, adjusted_close=102),
        ],
    )
    assert main(
        [
            "import-stock-csv",
            "--storage-dir",
            str(tmp_path / "storage"),
            "--input",
            str(csv_path),
            "--symbol",
            "SPY",
            "--source",
            "fixture",
            "--imported-at",
            "2026-04-24T12:00:00+00:00",
        ]
    ) == 0
    capsys.readouterr()

    assert main(
        [
            "stock-candle-health",
            "--storage-dir",
            str(tmp_path / "storage"),
            "--symbol",
            "SPY",
            "--start-date",
            "2026-04-02",
            "--end-date",
            "2026-04-06",
        ]
    ) == 0
    result = json.loads(capsys.readouterr().out)

    assert result["status"] == "healthy"
    assert result["candle_count"] == 2


def test_stock_csv_fixture_provider_uses_adjusted_close_and_calendar(tmp_path):
    csv_path = tmp_path / "spy.csv"
    _write_stock_csv(
        csv_path,
        [
            _stock_row("2026-04-02", close=105, adjusted_close=100),
            _stock_row("2026-04-03", close=106, adjusted_close=101),
            _stock_row("2026-04-06", close=107, adjusted_close=102),
        ],
    )
    provider = StockCsvFixtureProvider(csv_path, symbol="SPY")

    candles = provider.get_recent_candles(
        "SPY",
        lookback_candles=10,
        end_time=datetime(2026, 4, 6, 21, 0, tzinfo=UTC),
    )

    assert [candle.timestamp.isoformat() for candle in candles] == [
        "2026-04-02T20:00:00+00:00",
        "2026-04-06T20:00:00+00:00",
    ]
    assert [candle.close for candle in candles] == [100, 102]


def test_stock_candle_health_flags_missing_adjusted_close(tmp_path, capsys):
    JsonFileRepository(tmp_path).save_market_candle(
        MarketCandleRecord.from_candle(
            MarketCandle(
                timestamp=datetime(2026, 4, 2, 20, 0, tzinfo=UTC),
                open=100,
                high=101,
                low=99,
                close=100,
                volume=1_000,
            ),
            symbol="SPY",
            source="fixture",
            imported_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert main(
        [
            "stock-candle-health",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "SPY",
            "--start-date",
            "2026-04-02",
            "--end-date",
            "2026-04-02",
        ]
    ) == 2
    result = json.loads(capsys.readouterr().out)

    assert "missing_adjusted_close" in {finding["code"] for finding in result["findings"]}


def test_import_stock_csv_rejects_unsupported_symbol(tmp_path, capsys):
    csv_path = tmp_path / "bad.csv"
    _write_stock_csv(csv_path, [_stock_row("2026-04-02", close=105)])

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "import-stock-csv",
                "--storage-dir",
                str(tmp_path / "storage"),
                "--input",
                str(csv_path),
                "--symbol",
                "0050.TW",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "SPY" in captured.err
    assert "Traceback" not in captured.err
