from datetime import UTC, datetime, timedelta
import json

import pytest

from forecast_loop.cli import main
from forecast_loop.decision_research_plan import build_decision_blocker_research_task_plan
from forecast_loop.models import (
    BacktestResult,
    CanonicalEvent,
    MarketCandle,
    MarketCandleRecord,
    MarketReactionCheck,
    ResearchAgenda,
)
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


def _event(index: int, *, symbol: str = "BTC-USD") -> CanonicalEvent:
    event_time = datetime(2026, 4, 20, 10, 0, tzinfo=UTC) + timedelta(days=index)
    return CanonicalEvent(
        event_id=f"canonical-event:plan-edge-{index}",
        event_family="crypto_flow",
        event_type="CRYPTO_FLOW",
        symbol=symbol,
        title=f"Plan Event {index}",
        summary="Planner event-edge prerequisite fixture.",
        event_time=event_time,
        published_at=event_time,
        available_at=event_time,
        fetched_at=event_time,
        source_document_ids=[f"source-document:plan-edge-{index}"],
        primary_document_id=f"source-document:plan-edge-{index}",
        credibility_score=80.0,
        cross_source_count=1,
        official_source_flag=False,
        duplicate_group_id=f"duplicate-group:plan-edge-{index}",
        status="reliable",
        created_at=event_time,
    )


def _market_reaction(event: CanonicalEvent, *, passed: bool = True) -> MarketReactionCheck:
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
        passed=passed,
        blocked_reason=None if passed else "already_priced",
        flags=[] if passed else ["already_priced"],
    )


def _save_event_candles(repository: JsonFileRepository, event: CanonicalEvent) -> None:
    event_time = event.available_at or event.fetched_at
    imported_at = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    for timestamp, close in [
        (event_time, 100.0),
        (event_time + timedelta(hours=24), 103.0),
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
                source="planner-fixture",
                imported_at=imported_at,
            )
        )


def _save_single_candle(repository: JsonFileRepository, *, timestamp: datetime, close: float = 100.0) -> None:
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
            symbol="BTC-USD",
            source="planner-fixture",
            imported_at=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        )
    )


def _save_walk_forward_candles(repository: JsonFileRepository, *, start: datetime, count: int) -> None:
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
                source="planner-walk-forward-fixture",
                imported_at=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
            )
        )


def _backtest_result(*, created_at: datetime, symbol: str = "BTC-USD") -> BacktestResult:
    return BacktestResult(
        result_id=f"backtest-result:planner-{created_at.timestamp()}",
        backtest_id=f"backtest:planner-{created_at.timestamp()}",
        created_at=created_at,
        symbol=symbol,
        start=datetime(2026, 5, 1, 0, 0, tzinfo=UTC),
        end=datetime(2026, 5, 1, 11, 0, tzinfo=UTC),
        initial_cash=10_000.0,
        final_equity=10_050.0,
        strategy_return=0.005,
        benchmark_return=0.003,
        max_drawdown=0.01,
        sharpe=None,
        turnover=1.0,
        win_rate=None,
        trade_count=1,
        equity_curve=[],
        decision_basis="planner fixture backtest",
    )


def _seed_event_edge_prerequisites(repository: JsonFileRepository) -> None:
    event = _event(1)
    repository.save_canonical_event(event)
    repository.save_market_reaction_check(_market_reaction(event))
    _save_event_candles(repository, event)


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
    _seed_event_edge_prerequisites(repository)

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


def test_decision_blocker_research_plan_blocks_event_edge_when_inputs_are_missing(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    repository.save_research_agenda(_agenda(agenda_id="research-agenda:missing-inputs", created_at=now))

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=now + timedelta(minutes=30),
    )

    assert plan.next_task_id == "build_event_edge_evaluation"
    task = plan.task_by_id("build_event_edge_evaluation")
    assert task.status == "blocked"
    assert task.command_args is None
    assert task.blocked_reason == "missing_event_edge_inputs"
    assert task.missing_inputs == ["canonical_events", "market_reaction_checks", "market_candles"]


def test_decision_blocker_research_plan_blocks_event_edge_when_latest_reaction_failed(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    repository.save_research_agenda(_agenda(agenda_id="research-agenda:failed-reaction", created_at=now))
    event = _event(1)
    old_passed = _market_reaction(event, passed=True)
    old_passed.check_id = "market-reaction:old-passed"
    newer_failed = _market_reaction(event, passed=False)
    newer_failed.check_id = "market-reaction:newer-failed"
    newer_failed.created_at = old_passed.created_at + timedelta(hours=1)
    repository.save_canonical_event(event)
    repository.save_market_reaction_check(old_passed)
    repository.save_market_reaction_check(newer_failed)
    _save_event_candles(repository, event)

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=now + timedelta(minutes=30),
    )

    task = plan.task_by_id("build_event_edge_evaluation")
    assert task.status == "blocked"
    assert task.command_args is None
    assert task.blocked_reason == "missing_event_edge_inputs"
    assert task.missing_inputs == ["market_reaction_checks"]


def test_decision_blocker_research_plan_blocks_event_edge_without_exact_horizon_candles(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    repository.save_research_agenda(_agenda(agenda_id="research-agenda:bad-candles", created_at=now))
    event = _event(1)
    repository.save_canonical_event(event)
    repository.save_market_reaction_check(_market_reaction(event))
    _save_single_candle(repository, timestamp=(event.available_at or event.fetched_at) + timedelta(hours=1))

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=now + timedelta(minutes=30),
    )

    task = plan.task_by_id("build_event_edge_evaluation")
    assert task.status == "blocked"
    assert task.command_args is None
    assert task.blocked_reason == "missing_event_edge_inputs"
    assert task.missing_inputs == ["market_candles"]


def test_decision_blocker_research_plan_blocks_backtest_without_window(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    agenda = _agenda(
        agenda_id="research-agenda:backtest-only",
        created_at=now,
        expected_artifacts=["strategy_decision", "research_dataset", "backtest_result"],
        hypothesis="Latest decision decision:blocked is HOLD because backtest 未打贏 benchmark.",
    )
    repository.save_research_agenda(agenda)

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=now,
    )

    assert plan.next_task_id == "run_backtest"
    task = plan.task_by_id("run_backtest")
    assert task.status == "blocked"
    assert task.command_args is None
    assert task.blocked_reason == "missing_backtest_window"
    assert task.missing_inputs == ["market_candles"]


def test_decision_blocker_research_plan_emits_asof_backtest_command_when_candles_cover_window(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    candle_start = datetime(2026, 5, 1, 0, 0, tzinfo=UTC)
    agenda = _agenda(
        agenda_id="research-agenda:backtest-ready",
        created_at=now,
        expected_artifacts=["strategy_decision", "research_dataset", "backtest_result"],
        hypothesis="Latest decision decision:blocked is HOLD because backtest 未打贏 benchmark.",
    )
    repository.save_research_agenda(agenda)
    _save_walk_forward_candles(repository, start=candle_start, count=12)

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=now,
    )

    assert plan.next_task_id == "run_backtest"
    task = plan.task_by_id("run_backtest")
    assert task.status == "ready"
    assert task.blocked_reason is None
    assert task.missing_inputs == []
    assert task.command_args == [
        "python",
        "run_forecast_loop.py",
        "backtest",
        "--storage-dir",
        str(tmp_path),
        "--symbol",
        "BTC-USD",
        "--start",
        "2026-05-01T00:00:00+00:00",
        "--end",
        "2026-05-01T11:00:00+00:00",
        "--created-at",
        "2026-05-02T09:00:00+00:00",
        "--as-of",
        "2026-05-02T09:00:00+00:00",
    ]


def test_decision_blocker_research_plan_marks_backtest_complete_when_recent_result_exists(tmp_path):
    repository = JsonFileRepository(tmp_path)
    agenda_created_at = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    agenda = _agenda(
        agenda_id="research-agenda:backtest-complete",
        created_at=agenda_created_at,
        expected_artifacts=["strategy_decision", "research_dataset", "backtest_result"],
        hypothesis="Latest decision decision:blocked is HOLD because backtest 未打贏 benchmark.",
    )
    repository.save_research_agenda(agenda)
    repository.save_backtest_result(_backtest_result(created_at=agenda_created_at + timedelta(minutes=5)))

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=agenda_created_at + timedelta(minutes=10),
    )

    task = plan.task_by_id("run_backtest")
    assert task.status == "completed"
    assert task.artifact_id is not None
    assert task.command_args is None
    assert plan.next_task_id is None


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
    assert task.missing_inputs == ["market_candles"]


def test_decision_blocker_research_plan_emits_walk_forward_command_when_candles_cover_window(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    candle_start = datetime(2026, 5, 1, 0, 0, tzinfo=UTC)
    agenda = _agenda(
        agenda_id="research-agenda:walk-forward-ready",
        created_at=now,
        expected_artifacts=["strategy_decision", "research_dataset", "walk_forward_validation"],
        hypothesis="Latest decision decision:blocked is HOLD because walk-forward overfit risk.",
    )
    repository.save_research_agenda(agenda)
    _save_walk_forward_candles(repository, start=candle_start, count=12)

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=now,
    )

    assert plan.next_task_id == "run_walk_forward_validation"
    task = plan.task_by_id("run_walk_forward_validation")
    assert task.status == "ready"
    assert task.blocked_reason is None
    assert task.missing_inputs == []
    assert task.command_args == [
        "python",
        "run_forecast_loop.py",
        "walk-forward",
        "--storage-dir",
        str(tmp_path),
        "--symbol",
        "BTC-USD",
        "--start",
        "2026-05-01T00:00:00+00:00",
        "--end",
        "2026-05-01T11:00:00+00:00",
        "--created-at",
        "2026-05-02T09:00:00+00:00",
        "--train-size",
        "4",
        "--validation-size",
        "3",
        "--test-size",
        "3",
        "--step-size",
        "1",
    ]


def test_decision_blocker_research_plan_cli_outputs_json(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    repository.save_research_agenda(_agenda(agenda_id="research-agenda:cli", created_at=now))
    _seed_event_edge_prerequisites(repository)

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
