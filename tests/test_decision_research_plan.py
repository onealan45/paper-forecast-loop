from datetime import UTC, datetime, timedelta
import json

import pytest

from forecast_loop.cli import main
from forecast_loop.decision_research_plan import build_decision_blocker_research_task_plan
from forecast_loop.models import ResearchAgenda
from forecast_loop.storage import JsonFileRepository


def _agenda(
    *,
    agenda_id: str,
    created_at: datetime,
    symbol: str = "BTC-USD",
    expected_artifacts: list[str] | None = None,
    hypothesis: str | None = None,
) -> ResearchAgenda:
    return ResearchAgenda(
        agenda_id=agenda_id,
        created_at=created_at,
        symbol=symbol,
        title=f"Decision blocker agenda {agenda_id}",
        hypothesis=hypothesis
        or "Latest decision decision:blocked is HOLD because event edge 缺失, walk-forward overfit risk.",
        priority="HIGH",
        status="OPEN",
        target_strategy_family="decision_blocker_research",
        strategy_card_ids=[],
        expected_artifacts=expected_artifacts
        or ["strategy_decision", "research_dataset", "event_edge_evaluation", "walk_forward_validation"],
        acceptance_criteria=[
            "BUY/SELL gate must remain blocked until blockers improve",
            "updated strategy decision links the new evidence artifacts",
        ],
        blocked_actions=["directional_buy_sell_without_research_evidence"],
        decision_basis="decision_blocker_research_agenda",
    )


def test_decision_blocker_research_plan_prioritizes_event_edge_command(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    old_agenda = _agenda(
        agenda_id="research-agenda:old",
        created_at=now - timedelta(hours=1),
        expected_artifacts=["strategy_decision", "backtest_result"],
    )
    latest_agenda = _agenda(agenda_id="research-agenda:latest", created_at=now)
    eth_agenda = _agenda(
        agenda_id="research-agenda:eth",
        created_at=now + timedelta(minutes=5),
        symbol="ETH-USD",
    )
    repository.save_research_agenda(old_agenda)
    repository.save_research_agenda(latest_agenda)
    repository.save_research_agenda(eth_agenda)

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=now + timedelta(minutes=30),
    )

    assert plan.agenda_id == latest_agenda.agenda_id
    assert plan.next_task_id == "build_event_edge_evaluation"
    assert plan.blockers == ["event edge 缺失", "walk-forward overfit risk"]
    agenda_task = plan.task_by_id("resolve_decision_blocker_research_agenda")
    assert agenda_task.status == "completed"
    next_task = plan.task_by_id("build_event_edge_evaluation")
    assert next_task.status == "ready"
    assert next_task.required_artifact == "event_edge_evaluation"
    assert next_task.command_args == [
        "python",
        "run_forecast_loop.py",
        "build-event-edge",
        "--storage-dir",
        str(tmp_path),
        "--symbol",
        "BTC-USD",
        "--created-at",
        "2026-05-02T09:30:00+00:00",
    ]
    assert "event edge 缺失" in next_task.worker_prompt
    assert "walk-forward overfit risk" in next_task.worker_prompt


def test_decision_blocker_research_plan_blocks_walk_forward_without_window(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    agenda = _agenda(
        agenda_id="research-agenda:walk-forward-only",
        created_at=now,
        expected_artifacts=["strategy_decision", "research_dataset", "walk_forward_validation"],
        hypothesis="Latest decision decision:blocked is HOLD because walk-forward overfit risk.",
    )
    repository.save_research_agenda(agenda)

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=now,
    )

    assert plan.next_task_id == "run_walk_forward_validation"
    task = plan.task_by_id("run_walk_forward_validation")
    assert task.status == "blocked"
    assert task.command_args is None
    assert task.blocked_reason == "missing_walk_forward_window"
    assert task.missing_inputs == ["start", "end"]


def test_decision_blocker_research_plan_cli_outputs_json(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    repository.save_research_agenda(_agenda(agenda_id="research-agenda:cli", created_at=now))

    assert (
        main(
            [
                "decision-blocker-research-plan",
                "--storage-dir",
                str(tmp_path),
                "--symbol",
                "BTC-USD",
                "--now",
                "2026-05-02T09:30:00+00:00",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    plan = payload["decision_blocker_research_task_plan"]
    assert plan["agenda_id"] == "research-agenda:cli"
    assert plan["next_task_id"] == "build_event_edge_evaluation"
    assert plan["tasks"][1]["command_args"][2] == "build-event-edge"


def test_decision_blocker_research_plan_cli_rejects_missing_agenda(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["decision-blocker-research-plan", "--storage-dir", str(tmp_path), "--symbol", "BTC-USD"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "decision blocker research agenda not found for symbol: BTC-USD" in captured.err
    assert "Traceback" not in captured.err
