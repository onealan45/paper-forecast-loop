from datetime import UTC, datetime, timedelta
import json

import pytest

from forecast_loop.cli import main
from forecast_loop.health import run_health_check
from forecast_loop.models import MarketCandle, MarketCandleRecord
from forecast_loop.storage import JsonFileRepository


def _raw_candle_rows(start: datetime, count: int, *, symbol: str = "BTC-USD") -> list[dict]:
    rows = []
    for index in range(count):
        timestamp = start + timedelta(hours=index)
        price = 100.0 + index
        rows.append(
            {
                "symbol": symbol,
                "timestamp": timestamp.isoformat(),
                "open": price - 0.5,
                "high": price + 0.5,
                "low": price - 1.0,
                "close": price,
                "volume": 1_000 + index,
            }
        )
    return rows


def _write_jsonl(path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_cli_import_and_export_candles_round_trip(tmp_path, capsys):
    input_path = tmp_path / "candles-input.jsonl"
    output_path = tmp_path / "candles-export.jsonl"
    _write_jsonl(input_path, _raw_candle_rows(datetime(2026, 4, 21, 0, 0, tzinfo=UTC), 3))

    assert main(
        [
            "import-candles",
            "--storage-dir",
            str(tmp_path / "storage"),
            "--input",
            str(input_path),
            "--symbol",
            "BTC-USD",
            "--source",
            "fixture",
            "--imported-at",
            "2026-04-24T12:00:00+00:00",
        ]
    ) == 0
    first_result = json.loads(capsys.readouterr().out)
    assert first_result["imported_count"] == 3

    assert main(
        [
            "import-candles",
            "--storage-dir",
            str(tmp_path / "storage"),
            "--input",
            str(input_path),
            "--symbol",
            "BTC-USD",
            "--source",
            "fixture",
            "--imported-at",
            "2026-04-24T12:00:00+00:00",
        ]
    ) == 0
    second_result = json.loads(capsys.readouterr().out)
    assert second_result["imported_count"] == 0
    assert second_result["skipped_duplicate_count"] == 3

    assert main(
        [
            "export-candles",
            "--storage-dir",
            str(tmp_path / "storage"),
            "--output",
            str(output_path),
            "--symbol",
            "BTC-USD",
        ]
    ) == 0
    export_result = json.loads(capsys.readouterr().out)

    exported_rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert export_result["exported_count"] == 3
    assert [row["symbol"] for row in exported_rows] == ["BTC-USD", "BTC-USD", "BTC-USD"]


def test_cli_import_candles_deduplicates_existing_timestamp_from_different_source(tmp_path, capsys):
    first_input = tmp_path / "candles-fixture.jsonl"
    second_input = tmp_path / "candles-provider.jsonl"
    start = datetime(2026, 4, 21, 0, 0, tzinfo=UTC)
    _write_jsonl(first_input, _raw_candle_rows(start, 2))
    _write_jsonl(second_input, _raw_candle_rows(start, 2))

    assert main(
        [
            "import-candles",
            "--storage-dir",
            str(tmp_path / "storage"),
            "--input",
            str(first_input),
            "--symbol",
            "BTC-USD",
            "--source",
            "fixture",
            "--imported-at",
            "2026-04-24T12:00:00+00:00",
        ]
    ) == 0
    capsys.readouterr()

    assert main(
        [
            "import-candles",
            "--storage-dir",
            str(tmp_path / "storage"),
            "--input",
            str(second_input),
            "--symbol",
            "BTC-USD",
            "--source",
            "provider-runtime",
            "--imported-at",
            "2026-04-24T13:00:00+00:00",
        ]
    ) == 0
    result = json.loads(capsys.readouterr().out)
    records = JsonFileRepository(tmp_path / "storage").load_market_candles()

    assert result["imported_count"] == 0
    assert result["skipped_duplicate_count"] == 2
    assert len(records) == 2
    assert [record.source for record in records] == ["fixture", "fixture"]


def test_candle_health_detects_missing_and_duplicate_timestamps(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    imported_at = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    for source, hour in [
        ("fixture-a", 0),
        ("fixture-a", 1),
        ("fixture-b", 1),
        ("fixture-a", 3),
    ]:
        timestamp = datetime(2026, 4, 21, hour, 0, tzinfo=UTC)
        repository.save_market_candle(
            MarketCandleRecord.from_candle(
                MarketCandle(
                    timestamp=timestamp,
                    open=100,
                    high=105,
                    low=99,
                    close=100 + hour,
                    volume=1_000,
                ),
                symbol="BTC-USD",
                source=source,
                imported_at=imported_at,
            )
        )

    assert main(
        [
            "candle-health",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--start",
            "2026-04-21T00:00:00+00:00",
            "--end",
            "2026-04-21T03:00:00+00:00",
        ]
    ) == 2
    result = json.loads(capsys.readouterr().out)
    codes = {finding["code"] for finding in result["findings"]}

    assert result["status"] == "unhealthy"
    assert result["missing_count"] == 1
    assert result["duplicate_count"] == 1
    assert "missing_candle_timestamp" in codes
    assert "duplicate_candle_timestamp" in codes


def test_health_check_flags_duplicate_market_candle_timestamps(tmp_path):
    repository = JsonFileRepository(tmp_path)
    timestamp = datetime(2026, 4, 21, 0, 0, tzinfo=UTC)
    for source in ("fixture", "provider-runtime"):
        repository.save_market_candle(
            MarketCandleRecord.from_candle(
                MarketCandle(
                    timestamp=timestamp,
                    open=100,
                    high=101,
                    low=99,
                    close=100,
                    volume=1_000,
                ),
                symbol="BTC-USD",
                source=source,
                imported_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
            )
        )

    health = run_health_check(
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=datetime(2026, 4, 24, 13, 0, tzinfo=UTC),
        create_repair_request=False,
    )
    codes = {finding.code for finding in health.findings}

    assert "duplicate_candle_timestamp" in codes


def test_import_candles_rejects_non_hour_aligned_rows(tmp_path, capsys):
    input_path = tmp_path / "bad-candles.jsonl"
    _write_jsonl(input_path, _raw_candle_rows(datetime(2026, 4, 21, 0, 30, tzinfo=UTC), 1))

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "import-candles",
                "--storage-dir",
                str(tmp_path / "storage"),
                "--input",
                str(input_path),
                "--symbol",
                "BTC-USD",
                "--source",
                "fixture",
                "--imported-at",
                "2026-04-24T12:00:00+00:00",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "hour-aligned" in captured.err
    assert "Traceback" not in captured.err


def test_candle_health_flags_non_hour_aligned_stored_rows(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    repository.save_market_candle(
        MarketCandleRecord.from_candle(
            MarketCandle(
                timestamp=datetime(2026, 4, 21, 0, 30, tzinfo=UTC),
                open=100,
                high=101,
                low=99,
                close=100,
                volume=1_000,
            ),
            symbol="BTC-USD",
            source="fixture",
            imported_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert main(
        [
            "candle-health",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--start",
            "2026-04-21T00:00:00+00:00",
            "--end",
            "2026-04-21T00:00:00+00:00",
        ]
    ) == 2
    result = json.loads(capsys.readouterr().out)

    assert "bad_candle_row" in {finding["code"] for finding in result["findings"]}


def test_import_candles_rejects_non_finite_values(tmp_path, capsys):
    input_path = tmp_path / "bad-candles.jsonl"
    _write_jsonl(
        input_path,
        [
            {
                "symbol": "BTC-USD",
                "timestamp": "2026-04-21T00:00:00+00:00",
                "open": 100,
                "high": float("nan"),
                "low": 99,
                "close": 100,
                "volume": 1_000,
            }
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "import-candles",
                "--storage-dir",
                str(tmp_path / "storage"),
                "--input",
                str(input_path),
                "--symbol",
                "BTC-USD",
                "--source",
                "fixture",
                "--imported-at",
                "2026-04-24T12:00:00+00:00",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "must be finite" in captured.err
    assert "Traceback" not in captured.err


def test_candle_health_flags_invalid_ohlc_stored_rows(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    repository.save_market_candle(
        MarketCandleRecord.from_candle(
            MarketCandle(
                timestamp=datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
                open=100,
                high=99,
                low=98,
                close=101,
                volume=1_000,
            ),
            symbol="BTC-USD",
            source="fixture",
            imported_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert main(
        [
            "candle-health",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--start",
            "2026-04-21T00:00:00+00:00",
            "--end",
            "2026-04-21T00:00:00+00:00",
        ]
    ) == 2
    result = json.loads(capsys.readouterr().out)

    assert "bad_candle_row" in {finding["code"] for finding in result["findings"]}


def test_candle_health_rejects_invalid_interval_without_hanging(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "candle-health",
                "--storage-dir",
                str(tmp_path),
                "--symbol",
                "BTC-USD",
                "--start",
                "2026-04-21T00:00:00+00:00",
                "--end",
                "2026-04-21T00:00:00+00:00",
                "--interval-minutes",
                "0",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "greater than 0" in captured.err
    assert "Traceback" not in captured.err


def test_cli_replay_range_can_use_stored_historical_candles(tmp_path, capsys):
    input_path = tmp_path / "stored-candles.jsonl"
    _write_jsonl(input_path, _raw_candle_rows(datetime(2026, 4, 21, 0, 0, tzinfo=UTC), 11))

    assert main(
        [
            "import-candles",
            "--storage-dir",
            str(tmp_path),
            "--input",
            str(input_path),
            "--symbol",
            "BTC-USD",
            "--source",
            "fixture",
            "--imported-at",
            "2026-04-24T12:00:00+00:00",
        ]
    ) == 0
    capsys.readouterr()

    assert main(
        [
            "replay-range",
            "--provider",
            "stored",
            "--symbol",
            "BTC-USD",
            "--storage-dir",
            str(tmp_path),
            "--start",
            "2026-04-21T04:00:00+00:00",
            "--end",
            "2026-04-21T08:00:00+00:00",
            "--horizon-hours",
            "2",
        ]
    ) == 0
    replay_result = json.loads(capsys.readouterr().out)
    meta = json.loads((tmp_path / "last_replay_meta.json").read_text(encoding="utf-8"))

    assert replay_result["cycles_run"] == 5
    assert replay_result["scores_created"] == 3
    assert meta["provider"] == "stored"
    assert meta["evaluation_summary"]["resolved_count"] == 3


def test_cli_fetch_candles_stores_provider_candles_and_deduplicates(tmp_path, capsys):
    storage_dir = tmp_path / "storage"
    args = [
        "fetch-candles",
        "--provider",
        "sample",
        "--storage-dir",
        str(storage_dir),
        "--symbol",
        "BTC-USD",
        "--lookback-candles",
        "3",
        "--now",
        "2026-04-24T12:00:00+00:00",
        "--source",
        "sample-runtime-seed",
    ]

    assert main(args) == 0
    first_result = json.loads(capsys.readouterr().out)
    first_repository = JsonFileRepository(storage_dir)
    first_records = first_repository.load_market_candles()
    first_provider_runs = first_repository.load_provider_runs()

    assert first_result["provider"] == "sample"
    assert first_result["fetched_count"] == 3
    assert first_result["stored_count"] == 3
    assert first_result["skipped_duplicate_count"] == 0
    assert first_result["latest_candle_timestamp"] == "2026-04-24T12:00:00+00:00"
    assert [record.source for record in first_records] == ["sample-runtime-seed"] * 3
    assert len(first_provider_runs) == 1
    assert first_provider_runs[0].operation == "get_recent_candles"
    assert first_provider_runs[0].candle_count == 3

    assert main(args) == 0
    second_result = json.loads(capsys.readouterr().out)
    second_repository = JsonFileRepository(storage_dir)
    second_records = second_repository.load_market_candles()
    second_provider_runs = second_repository.load_provider_runs()

    assert second_result["stored_count"] == 0
    assert second_result["skipped_duplicate_count"] == 3
    assert len(second_records) == 3
    assert len(second_provider_runs) == 2

    refetch_args = list(args)
    refetch_args[refetch_args.index("--source") + 1] = "sample-runtime-refetch"
    assert main(refetch_args) == 0
    refetch_result = json.loads(capsys.readouterr().out)
    refetch_repository = JsonFileRepository(storage_dir)

    assert refetch_result["stored_count"] == 0
    assert refetch_result["skipped_duplicate_count"] == 3
    assert len(refetch_repository.load_market_candles()) == 3
    assert [record.source for record in refetch_repository.load_market_candles()] == ["sample-runtime-seed"] * 3
