from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from forecast_loop.cli import main
from forecast_loop.decision_research_plan import build_decision_blocker_research_task_plan
from forecast_loop.event_edge import build_event_edge_evaluations
from forecast_loop.market_derived_events import build_market_derived_events
from forecast_loop.models import MarketCandle, MarketCandleRecord, ResearchAgenda
from forecast_loop.storage import JsonFileRepository


def _now() -> datetime:
    return datetime(2026, 5, 2, 12, 0, tzinfo=UTC)


def _save_candle(repository: JsonFileRepository, *, timestamp: datetime, close: float, volume: float = 1_000.0) -> None:
    repository.save_market_candle(
        MarketCandleRecord.from_candle(
            MarketCandle(
                timestamp=timestamp,
                open=close,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
                volume=volume,
            ),
            symbol="BTC-USD",
            source="fixture",
            imported_at=_now(),
        )
    )


def _seed_market_move(repository: JsonFileRepository) -> datetime:
    event_time = datetime(2026, 4, 29, 8, 0, tzinfo=UTC)
    closes = {
        -24: 95.0,
        -4: 96.0,
        -1: 100.0,
        0: 103.0,
        1: 103.5,
        24: 106.0,
    }
    for offset, close in closes.items():
        _save_candle(repository, timestamp=event_time + timedelta(hours=offset), close=close)
    return event_time


def _agenda(created_at: datetime) -> ResearchAgenda:
    return ResearchAgenda(
        agenda_id="research-agenda:market-derived",
        created_at=created_at,
        symbol="BTC-USD",
        title="Decision blocker agenda",
        hypothesis="Latest decision decision:blocker is HOLD because event edge 缺失.",
        priority="HIGH",
        status="OPEN",
        target_strategy_family="decision_blocker_research",
        strategy_card_ids=[],
        expected_artifacts=["strategy_decision", "event_edge_evaluation"],
        acceptance_criteria=["market-derived event edge can be evaluated"],
        blocked_actions=["directional_buy_sell_without_research_evidence"],
        decision_basis="decision_blocker_research_agenda",
    )


def test_build_market_derived_events_creates_event_source_and_reaction(tmp_path):
    repository = JsonFileRepository(tmp_path)
    event_time = _seed_market_move(repository)

    result = build_market_derived_events(
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=_now(),
        min_abs_return=0.02,
    )

    documents = repository.load_source_documents()
    events = repository.load_canonical_events()
    reactions = repository.load_market_reaction_checks()
    assert result.event_count == 1
    assert result.source_document_count == 1
    assert result.market_reaction_check_count == 1
    assert documents[0].topics == ["market_derived_move"]
    assert documents[0].symbols == ["BTC-USD"]
    assert "forward_return_24h" not in documents[0].summary
    assert "forward_return_24h" not in documents[0].body_excerpt
    assert events[0].source_document_ids == [documents[0].document_id]
    assert events[0].primary_document_id == documents[0].document_id
    assert events[0].event_time == event_time
    assert events[0].event_family == "market_derived_move"
    assert "forward_return_24h" not in events[0].summary
    assert reactions[0].event_id == events[0].event_id
    assert reactions[0].passed is True
    assert reactions[0].event_timestamp_used == event_time


def test_build_market_derived_events_is_idempotent_and_ignores_moves_without_forward_horizon(tmp_path):
    repository = JsonFileRepository(tmp_path)
    _seed_market_move(repository)
    _save_candle(repository, timestamp=_now() - timedelta(hours=1), close=100.0)
    _save_candle(repository, timestamp=_now(), close=104.0)

    first = build_market_derived_events(
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=_now(),
        min_abs_return=0.02,
    )
    second = build_market_derived_events(
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=_now(),
        min_abs_return=0.02,
    )

    assert second.event_ids == first.event_ids
    assert second.source_document_ids == first.source_document_ids
    assert len(repository.load_source_documents()) == 1
    assert len(repository.load_canonical_events()) == 1
    assert len(repository.load_market_reaction_checks()) == 1


def test_market_derived_events_unblock_event_edge_plan_and_builder(tmp_path):
    repository = JsonFileRepository(tmp_path)
    _seed_market_move(repository)
    repository.save_research_agenda(_agenda(_now() - timedelta(hours=1)))

    before_plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=_now(),
    )
    assert before_plan.task_by_id("build_event_edge_evaluation").status == "blocked"

    build_market_derived_events(
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=_now(),
        min_abs_return=0.02,
    )

    after_plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=_now(),
    )
    event_edge_task = after_plan.task_by_id("build_event_edge_evaluation")
    assert event_edge_task.status == "ready"
    assert event_edge_task.command_args is not None

    edge_result = build_event_edge_evaluations(
        storage_dir=tmp_path,
        created_at=_now(),
        symbol="BTC-USD",
        min_sample_size=3,
    )
    assert edge_result.evaluation_count == 1
    assert repository.load_event_edge_evaluations()[0].sample_n == 1


def test_build_market_derived_events_cli_outputs_json_and_requires_created_at(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    _seed_market_move(repository)

    with pytest.raises(SystemExit) as exc_info:
        main(["build-market-derived-events", "--storage-dir", str(tmp_path), "--symbol", "BTC-USD"])
    assert exc_info.value.code == 2
    assert "--created-at" in capsys.readouterr().err

    assert (
        main(
            [
                "build-market-derived-events",
                "--storage-dir",
                str(tmp_path),
                "--symbol",
                "BTC-USD",
                "--created-at",
                _now().isoformat(),
                "--min-abs-return",
                "0.02",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["event_count"] == 1
    assert payload["source_document_count"] == 1
    assert payload["market_reaction_check_count"] == 1
