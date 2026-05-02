from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from forecast_loop.cli import main
from forecast_loop.decision_research_executor import execute_decision_blocker_research_next_task
from forecast_loop.models import CanonicalEvent, MarketCandle, MarketCandleRecord, MarketReactionCheck, ResearchAgenda
from forecast_loop.storage import JsonFileRepository


def _agenda(
    *,
    agenda_id: str = "research-agenda:decision-blocker",
    created_at: datetime,
    expected_artifacts: list[str] | None = None,
    hypothesis: str | None = None,
) -> ResearchAgenda:
    return ResearchAgenda(
        agenda_id=agenda_id,
        created_at=created_at,
        symbol="BTC-USD",
        title="Decision blocker agenda",
        hypothesis=hypothesis
        or "Latest decision decision:blocker is HOLD because event edge 缺失, walk-forward overfit risk.",
        priority="HIGH",
        status="OPEN",
        target_strategy_family="decision_blocker_research",
        strategy_card_ids=[],
        expected_artifacts=expected_artifacts
        or ["strategy_decision", "event_edge_evaluation", "walk_forward_validation"],
        acceptance_criteria=[
            "event edge evidence exists before BUY/SELL confidence increases",
            "walk-forward remains blocked until explicit windows exist",
        ],
        blocked_actions=["directional_buy_sell_without_research_evidence"],
        decision_basis="decision_blocker_research_agenda",
    )


def _event(index: int) -> CanonicalEvent:
    event_time = datetime(2026, 4, 20, 10, 0, tzinfo=UTC) + timedelta(days=index * 2)
    return CanonicalEvent(
        event_id=f"canonical-event:executor-edge-{index}",
        event_family="crypto_flow",
        event_type="CRYPTO_FLOW",
        symbol="BTC-USD",
        title=f"Executor Event {index}",
        summary="Historical event-edge executor fixture.",
        event_time=event_time,
        published_at=event_time,
        available_at=event_time,
        fetched_at=event_time,
        source_document_ids=[f"source-document:executor-edge-{index}"],
        primary_document_id=f"source-document:executor-edge-{index}",
        credibility_score=85.0,
        cross_source_count=1,
        official_source_flag=False,
        duplicate_group_id=f"duplicate-group:executor-edge-{index}",
        status="reliable",
        created_at=event_time,
    )


def _market_reaction(event: CanonicalEvent) -> MarketReactionCheck:
    event_time = event.available_at or event.fetched_at
    return MarketReactionCheck(
        check_id=f"market-reaction:{event.event_id.split(':')[-1]}",
        event_id=event.event_id,
        symbol=event.symbol,
        created_at=event_time,
        decision_timestamp=event_time,
        event_timestamp_used=event_time,
        pre_event_ret_1h=0.001,
        pre_event_ret_4h=0.002,
        pre_event_ret_24h=0.003,
        post_event_ret_15m=None,
        post_event_ret_1h=0.004,
        pre_event_drift_z=0.1,
        volume_shock_z=0.1,
        priced_in_ratio=0.1,
        already_priced=False,
        passed=True,
        blocked_reason=None,
        flags=[],
    )


def _save_event_candles(repository: JsonFileRepository, event: CanonicalEvent, *, forward_return: float) -> None:
    event_time = event.available_at or event.fetched_at
    imported_at = datetime(2026, 4, 29, 12, 0, tzinfo=UTC)
    start_price = 100.0
    end_price = start_price * (1.0 + forward_return)
    for timestamp, close in [
        (event_time, start_price),
        (event_time + timedelta(hours=24), end_price),
    ]:
        repository.save_market_candle(
            MarketCandleRecord.from_candle(
                MarketCandle(
                    timestamp=timestamp,
                    open=close,
                    high=close + 1.0,
                    low=close - 1.0,
                    close=close,
                    volume=1_000.0,
                ),
                symbol=event.symbol,
                source="executor-fixture",
                imported_at=imported_at,
            )
        )


def _save_walk_forward_candles(repository: JsonFileRepository, *, start: datetime, count: int) -> None:
    imported_at = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    for index in range(count):
        close = 100.0 + index
        repository.save_market_candle(
            MarketCandleRecord.from_candle(
                MarketCandle(
                    timestamp=start + timedelta(hours=index),
                    open=close,
                    high=close + 1.0,
                    low=close - 1.0,
                    close=close,
                    volume=1_000.0 + index,
                ),
                symbol="BTC-USD",
                source="executor-walk-forward-fixture",
                imported_at=imported_at,
            )
        )


def _seed_event_edge_inputs(repository: JsonFileRepository) -> None:
    for index, forward_return in enumerate([0.04, 0.03, 0.02], start=1):
        event = _event(index)
        repository.save_canonical_event(event)
        repository.save_market_reaction_check(_market_reaction(event))
        _save_event_candles(repository, event, forward_return=forward_return)


def test_execute_decision_blocker_research_next_task_builds_event_edge_and_records_run(tmp_path):
    repository = JsonFileRepository(tmp_path)
    created_at = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
    repository.save_research_agenda(_agenda(created_at=created_at - timedelta(hours=1)))
    _seed_event_edge_inputs(repository)

    result = execute_decision_blocker_research_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=created_at,
    )

    assert result.executed_task_id == "build_event_edge_evaluation"
    assert result.before_plan.next_task_id == "build_event_edge_evaluation"
    assert len(result.created_artifact_ids) == 1
    assert result.created_artifact_ids[0].startswith("event-edge:")
    event_edge_task = result.after_plan.task_by_id("build_event_edge_evaluation")
    assert event_edge_task.status == "completed"
    assert event_edge_task.artifact_id == result.created_artifact_ids[0]
    assert result.after_plan.next_task_id == "run_walk_forward_validation"
    assert result.automation_run.command == "execute-decision-blocker-research-next-task"
    assert result.automation_run.decision_basis == "decision_blocker_research_task_execution"
    assert result.automation_run.steps[-1] == {
        "name": "build_event_edge_evaluation",
        "status": "executed",
        "artifact_id": result.created_artifact_ids[0],
    }
    assert repository.load_automation_runs()[-1].automation_run_id == result.automation_run.automation_run_id


def test_execute_decision_blocker_research_next_task_rejects_blocked_walk_forward(tmp_path):
    repository = JsonFileRepository(tmp_path)
    created_at = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
    repository.save_research_agenda(
        _agenda(
            created_at=created_at,
            expected_artifacts=["strategy_decision", "walk_forward_validation"],
            hypothesis="Latest decision decision:blocker is HOLD because walk-forward overfit risk.",
        )
    )

    with pytest.raises(ValueError, match="decision_blocker_research_next_task_not_ready"):
        execute_decision_blocker_research_next_task(
            repository=repository,
            storage_dir=tmp_path,
            symbol="BTC-USD",
            created_at=created_at,
        )


def test_execute_decision_blocker_research_next_task_rejects_ready_but_unsupported_walk_forward(tmp_path):
    repository = JsonFileRepository(tmp_path)
    created_at = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
    repository.save_research_agenda(
        _agenda(
            created_at=created_at,
            expected_artifacts=["strategy_decision", "walk_forward_validation"],
            hypothesis="Latest decision decision:blocker is HOLD because walk-forward overfit risk.",
        )
    )
    _save_walk_forward_candles(repository, start=datetime(2026, 5, 1, 0, 0, tzinfo=UTC), count=12)

    with pytest.raises(ValueError, match="unsupported_decision_blocker_research_task_execution:run_walk_forward_validation"):
        execute_decision_blocker_research_next_task(
            repository=repository,
            storage_dir=tmp_path,
            symbol="BTC-USD",
            created_at=created_at,
        )

    assert repository.load_automation_runs() == []


def test_execute_decision_blocker_research_next_task_rejects_execution_before_agenda(tmp_path):
    repository = JsonFileRepository(tmp_path)
    agenda_created_at = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
    repository.save_research_agenda(_agenda(created_at=agenda_created_at))
    _seed_event_edge_inputs(repository)

    with pytest.raises(ValueError, match="decision_blocker_research_execution_before_agenda"):
        execute_decision_blocker_research_next_task(
            repository=repository,
            storage_dir=tmp_path,
            symbol="BTC-USD",
            created_at=agenda_created_at - timedelta(hours=1),
        )

    assert repository.load_event_edge_evaluations() == []
    assert repository.load_automation_runs() == []


def test_execute_decision_blocker_research_next_task_cli_rejects_execution_before_agenda(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    agenda_created_at = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
    repository.save_research_agenda(_agenda(created_at=agenda_created_at))
    _seed_event_edge_inputs(repository)

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "execute-decision-blocker-research-next-task",
                "--storage-dir",
                str(tmp_path),
                "--symbol",
                "BTC-USD",
                "--now",
                (agenda_created_at - timedelta(hours=1)).isoformat(),
            ]
        )

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "decision_blocker_research_execution_before_agenda" in captured.err
    assert "Traceback" not in captured.err
    assert repository.load_event_edge_evaluations() == []
    assert repository.load_automation_runs() == []


def test_execute_decision_blocker_research_next_task_cli_outputs_json(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    created_at = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
    repository.save_research_agenda(_agenda(created_at=created_at - timedelta(hours=1)))
    _seed_event_edge_inputs(repository)

    assert (
        main(
            [
                "execute-decision-blocker-research-next-task",
                "--storage-dir",
                str(tmp_path),
                "--symbol",
                "BTC-USD",
                "--now",
                created_at.isoformat(),
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["executed_task_id"] == "build_event_edge_evaluation"
    assert payload["after_plan"]["next_task_id"] == "run_walk_forward_validation"
    assert payload["created_artifact_ids"][0].startswith("event-edge:")
