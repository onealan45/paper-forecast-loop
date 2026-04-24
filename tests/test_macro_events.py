from datetime import UTC, datetime
import json

import pytest

from forecast_loop.cli import main
from forecast_loop.storage import JsonFileRepository


def _write_jsonl(path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _macro_row(event_type: str, scheduled_at: str, *, name: str | None = None) -> dict:
    return {
        "event_type": event_type,
        "name": name or f"US {event_type}",
        "region": "US",
        "scheduled_at": scheduled_at,
        "actual_value": None,
        "consensus_value": 3.1,
        "previous_value": 3.0,
        "unit": "percent",
        "importance": "high",
        "notes": "fixture",
    }


def test_import_macro_events_and_calendar_filters(tmp_path, capsys):
    input_path = tmp_path / "macro.jsonl"
    _write_jsonl(
        input_path,
        [
            _macro_row("CPI", "2026-04-10T12:30:00+00:00"),
            _macro_row("FOMC", "2026-04-29T18:00:00+00:00"),
            _macro_row("NFP", "2026-05-01T12:30:00+00:00"),
        ],
    )

    assert main(
        [
            "import-macro-events",
            "--storage-dir",
            str(tmp_path / "storage"),
            "--input",
            str(input_path),
            "--source",
            "fixture",
            "--imported-at",
            "2026-04-24T12:00:00+00:00",
        ]
    ) == 0
    import_result = json.loads(capsys.readouterr().out)

    assert import_result["imported_count"] == 3
    assert len(JsonFileRepository(tmp_path / "storage").load_macro_events()) == 3

    assert main(
        [
            "macro-calendar",
            "--storage-dir",
            str(tmp_path / "storage"),
            "--start",
            "2026-04-01T00:00:00+00:00",
            "--end",
            "2026-04-30T23:59:00+00:00",
            "--event-type",
            "FOMC",
            "--region",
            "US",
        ]
    ) == 0
    calendar_result = json.loads(capsys.readouterr().out)

    assert calendar_result["event_count"] == 1
    assert calendar_result["events"][0]["event_type"] == "FOMC"
    assert calendar_result["events"][0]["scheduled_at"] == "2026-04-29T18:00:00+00:00"


def test_import_macro_events_is_idempotent(tmp_path, capsys):
    input_path = tmp_path / "macro.jsonl"
    _write_jsonl(input_path, [_macro_row("PCE", "2026-04-30T12:30:00+00:00")])

    args = [
        "import-macro-events",
        "--storage-dir",
        str(tmp_path / "storage"),
        "--input",
        str(input_path),
        "--source",
        "fixture",
        "--imported-at",
        "2026-04-24T12:00:00+00:00",
    ]
    assert main(args) == 0
    capsys.readouterr()
    assert main(args) == 0
    result = json.loads(capsys.readouterr().out)

    assert result["imported_count"] == 0
    assert result["skipped_duplicate_count"] == 1


def test_import_macro_events_rejects_unsupported_type(tmp_path, capsys):
    input_path = tmp_path / "macro.jsonl"
    _write_jsonl(input_path, [_macro_row("RETAIL_SALES", "2026-04-15T12:30:00+00:00")])

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "import-macro-events",
                "--storage-dir",
                str(tmp_path / "storage"),
                "--input",
                str(input_path),
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "unsupported macro event type" in captured.err
    assert "Traceback" not in captured.err


def test_import_macro_events_rejects_naive_schedule(tmp_path, capsys):
    input_path = tmp_path / "macro.jsonl"
    _write_jsonl(input_path, [_macro_row("GDP", "2026-04-30T12:30:00")])

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "import-macro-events",
                "--storage-dir",
                str(tmp_path / "storage"),
                "--input",
                str(input_path),
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "scheduled_at must be timezone-aware" in captured.err
    assert "Traceback" not in captured.err


def test_import_macro_events_rejects_non_finite_numeric_value(tmp_path, capsys):
    input_path = tmp_path / "macro.jsonl"
    row = _macro_row("CPI", "2026-04-10T12:30:00+00:00")
    row["consensus_value"] = "NaN"
    _write_jsonl(input_path, [row])

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "import-macro-events",
                "--storage-dir",
                str(tmp_path / "storage"),
                "--input",
                str(input_path),
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "numeric field must be finite" in captured.err
    assert "Traceback" not in captured.err


def test_macro_calendar_requires_existing_storage_dir(tmp_path, capsys):
    missing_storage = tmp_path / "missing-storage"

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "macro-calendar",
                "--storage-dir",
                str(missing_storage),
                "--start",
                "2026-04-01T00:00:00+00:00",
                "--end",
                "2026-04-30T23:59:00+00:00",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "storage directory does not exist" in captured.err
    assert not missing_storage.exists()
    assert "Traceback" not in captured.err


def test_macro_calendar_requires_valid_type(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "macro-calendar",
                "--storage-dir",
                str(tmp_path),
                "--start",
                "2026-04-01T00:00:00+00:00",
                "--end",
                "2026-04-30T23:59:00+00:00",
                "--event-type",
                "BAD",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "unsupported macro event type" in captured.err
    assert "Traceback" not in captured.err
