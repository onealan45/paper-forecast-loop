from datetime import UTC, datetime
import json

import pytest

from forecast_loop.cli import main
from forecast_loop.models import RepairRequest
from forecast_loop.storage import JsonFileRepository


def _repair_request(now: datetime) -> RepairRequest:
    return RepairRequest(
        repair_request_id="repair:test",
        created_at=now,
        status="pending",
        severity="blocking",
        observed_failure="Latest forecast is stale.",
        reproduction_command=(
            "python .\\run_forecast_loop.py health-check --storage-dir storage --symbol BTC-USD"
        ),
        expected_behavior="Health check should return healthy after refresh.",
        affected_artifacts=["forecasts.jsonl"],
        recommended_tests=["python -m pytest -q"],
        safety_boundary="no real orders; no real capital",
        acceptance_criteria=["health-check returns healthy"],
        finding_codes=["stale_latest_forecast"],
        prompt_path=".codex/repair_requests/pending/repair_test.md",
    )


def test_cli_marks_repair_request_resolved_with_audit_reason(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    repository.save_repair_request(_repair_request(datetime(2026, 5, 1, 8, 0, tzinfo=UTC)))

    assert (
        main(
            [
                "repair-request",
                "--storage-dir",
                str(tmp_path),
                "--repair-request-id",
                "repair:test",
                "--status",
                "resolved",
                "--reason",
                "health-check returned healthy after runtime refresh",
                "--updated-at",
                "2026-05-01T08:30:00+00:00",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    updated = repository.load_repair_requests()[0]
    assert payload["repair_request"]["repair_request_id"] == "repair:test"
    assert payload["repair_request"]["status"] == "resolved"
    assert payload["repair_request"]["status_reason"] == "health-check returned healthy after runtime refresh"
    assert updated.status == "resolved"
    assert updated.status_updated_at == datetime(2026, 5, 1, 8, 30, tzinfo=UTC)
    assert updated.status_reason == "health-check returned healthy after runtime refresh"


def test_cli_rejects_unknown_repair_request_without_mutating_queue(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    repository.save_repair_request(_repair_request(datetime(2026, 5, 1, 8, 0, tzinfo=UTC)))

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "repair-request",
                "--storage-dir",
                str(tmp_path),
                "--repair-request-id",
                "repair:missing",
                "--status",
                "ignored",
                "--reason",
                "operator decided this request is obsolete",
                "--updated-at",
                "2026-05-01T08:30:00+00:00",
            ]
        )

    updated = repository.load_repair_requests()[0]
    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert updated.status == "pending"
    assert "repair request not found: repair:missing" in captured.err
    assert "Traceback" not in captured.err
