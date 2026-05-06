from datetime import UTC, datetime, timedelta
import json

import pytest

from forecast_loop.cli import main
from forecast_loop.decision_research_plan import build_decision_blocker_research_task_plan
from forecast_loop.models import (
    BacktestResult,
    BacktestRun,
    CanonicalEvent,
    EventEdgeEvaluation,
    MarketCandle,
    MarketCandleRecord,
    MarketReactionCheck,
    ResearchAgenda,
    WalkForwardValidation,
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


def _market_reaction_for_timestamp(
    event: CanonicalEvent,
    *,
    event_timestamp_used: datetime,
    created_at: datetime,
    passed: bool = True,
) -> MarketReactionCheck:
    return MarketReactionCheck(
        check_id=f"market-reaction:{event.event_id.split(':')[-1]}:{created_at.timestamp()}",
        event_id=event.event_id,
        symbol=event.symbol,
        created_at=created_at,
        decision_timestamp=created_at,
        event_timestamp_used=event_timestamp_used,
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


def _save_event_candles_for_timestamp(
    repository: JsonFileRepository,
    *,
    timestamp: datetime,
    imported_at: datetime,
) -> None:
    for candle_timestamp, close in [
        (timestamp, 100.0),
        (timestamp + timedelta(hours=24), 103.0),
    ]:
        repository.save_market_candle(
            MarketCandleRecord.from_candle(
                MarketCandle(
                    timestamp=candle_timestamp,
                    open=close,
                    high=close + 1.0,
                    low=close - 1.0,
                    close=close,
                    volume=1_000.0,
                ),
                symbol="BTC-USD",
                source="planner-fixture",
                imported_at=imported_at,
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


def _decision_blocker_backtest_run(
    *,
    created_at: datetime,
    start: datetime,
    end: datetime,
    candle_ids: list[str],
    symbol: str = "BTC-USD",
) -> BacktestRun:
    return BacktestRun(
        backtest_id=f"backtest-run:planner-{created_at.timestamp()}",
        created_at=created_at,
        symbol=symbol,
        start=start,
        end=end,
        strategy_name="moving_average_trend",
        initial_cash=10_000.0,
        fee_bps=5.0,
        slippage_bps=10.0,
        moving_average_window=3,
        candle_ids=candle_ids,
        decision_basis=(
            "paper-only moving-average trend backtest using stored candles; "
            "id_context=decision_blocker_research:run_backtest:backtest_result"
        ),
    )


def _backtest_result_for_run(run: BacktestRun, *, created_at: datetime) -> BacktestResult:
    return BacktestResult(
        result_id=f"backtest-result:planner-window-{created_at.timestamp()}",
        backtest_id=run.backtest_id,
        created_at=created_at,
        symbol=run.symbol,
        start=run.start,
        end=run.end,
        initial_cash=run.initial_cash,
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


def _event_edge_evaluation(*, evaluation_id: str, created_at: datetime, symbol: str = "BTC-USD") -> EventEdgeEvaluation:
    return EventEdgeEvaluation(
        evaluation_id=evaluation_id,
        event_family="crypto_flow",
        event_type="CRYPTO_FLOW",
        symbol=symbol,
        created_at=created_at,
        split="historical_event_sample",
        horizon_hours=24,
        sample_n=3,
        average_forward_return=0.02,
        average_benchmark_return=0.0,
        average_excess_return_after_costs=0.01,
        hit_rate=1.0,
        max_adverse_excursion_p50=-0.01,
        max_adverse_excursion_p90=-0.02,
        max_drawdown_if_traded=-0.02,
        turnover=3.0,
        estimated_cost_bps=10.0,
        dsr=None,
        white_rc_p=None,
        stability_score=None,
        passed=True,
        blocked_reason=None,
        flags=[],
    )


def _event_edge_evaluation_with_manifest(
    *,
    evaluation_id: str,
    created_at: datetime,
    input_event_ids: list[str],
    input_reaction_check_ids: list[str],
    input_candle_ids: list[str],
    input_watermark: datetime,
    symbol: str = "BTC-USD",
) -> EventEdgeEvaluation:
    evaluation = _event_edge_evaluation(evaluation_id=evaluation_id, created_at=created_at, symbol=symbol)
    evaluation.input_event_ids = input_event_ids
    evaluation.input_reaction_check_ids = input_reaction_check_ids
    evaluation.input_candle_ids = input_candle_ids
    evaluation.input_watermark = input_watermark
    return evaluation


def _walk_forward_validation(
    *,
    validation_id: str,
    created_at: datetime,
    start: datetime,
    end: datetime,
    symbol: str = "BTC-USD",
) -> WalkForwardValidation:
    return WalkForwardValidation(
        validation_id=validation_id,
        created_at=created_at,
        symbol=symbol,
        start=start,
        end=end,
        strategy_name="moving_average_trend",
        train_size=4,
        validation_size=3,
        test_size=3,
        step_size=1,
        initial_cash=10_000.0,
        fee_bps=5.0,
        slippage_bps=10.0,
        moving_average_window=3,
        window_count=1,
        average_validation_return=0.004,
        average_test_return=0.003,
        average_benchmark_return=0.002,
        average_excess_return=0.001,
        test_win_rate=1.0,
        overfit_window_count=0,
        overfit_risk_flags=[],
        backtest_result_ids=["backtest-result:planner-window"],
        windows=[],
        decision_basis=(
            "rolling walk-forward validation; "
            "id_context=decision_blocker_research:run_walk_forward_validation:walk_forward_validation"
        ),
    )


def _seed_event_edge_prerequisites(repository: JsonFileRepository) -> None:
    event = _event(1)
    repository.save_canonical_event(event)
    repository.save_market_reaction_check(_market_reaction(event))
    _save_event_candles(repository, event)


def _seeded_event_edge_manifest(repository: JsonFileRepository) -> tuple[list[str], list[str], list[str], datetime]:
    event = repository.load_canonical_events()[0]
    reaction = repository.load_market_reaction_checks()[0]
    candles = repository.load_market_candles()
    input_watermark = max(
        [
            event.available_at,
            event.fetched_at,
            event.created_at,
            reaction.created_at,
            *[max(candle.timestamp, candle.imported_at) for candle in candles],
        ]
    )
    return [event.event_id], [reaction.check_id], [candle.candle_id for candle in candles], input_watermark


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


def test_decision_blocker_research_plan_reuses_event_edge_when_inputs_are_unchanged_after_new_agenda(tmp_path):
    repository = JsonFileRepository(tmp_path)
    old_agenda_at = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    new_agenda_at = datetime(2026, 5, 2, 11, 0, tzinfo=UTC)
    repository.save_research_agenda(
        _agenda(
            agenda_id="research-agenda:old-event-edge",
            created_at=old_agenda_at,
            expected_artifacts=["strategy_decision", "event_edge_evaluation"],
        )
    )
    repository.save_research_agenda(
        _agenda(
            agenda_id="research-agenda:new-event-edge",
            created_at=new_agenda_at,
            expected_artifacts=["strategy_decision", "event_edge_evaluation"],
        )
    )
    _seed_event_edge_prerequisites(repository)
    repository.save_event_edge_evaluation(
        _event_edge_evaluation(
            evaluation_id="event-edge:already-current",
            created_at=old_agenda_at + timedelta(minutes=10),
        )
    )

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=new_agenda_at + timedelta(minutes=30),
    )

    task = plan.task_by_id("build_event_edge_evaluation")
    assert task.status == "completed"
    assert task.artifact_id == "event-edge:already-current"
    assert task.command_args is None
    assert plan.next_task_id is None


def test_decision_blocker_research_plan_reuses_event_edge_when_manifest_matches(tmp_path):
    repository = JsonFileRepository(tmp_path)
    agenda_at = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    repository.save_research_agenda(
        _agenda(
            agenda_id="research-agenda:event-manifest-match",
            created_at=agenda_at,
            expected_artifacts=["strategy_decision", "event_edge_evaluation"],
        )
    )
    _seed_event_edge_prerequisites(repository)
    event_ids, reaction_ids, candle_ids, input_watermark = _seeded_event_edge_manifest(repository)
    repository.save_event_edge_evaluation(
        _event_edge_evaluation_with_manifest(
            evaluation_id="event-edge:matching-manifest",
            created_at=agenda_at + timedelta(minutes=10),
            input_event_ids=event_ids,
            input_reaction_check_ids=reaction_ids,
            input_candle_ids=candle_ids,
            input_watermark=input_watermark,
        )
    )

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=agenda_at + timedelta(minutes=30),
    )

    task = plan.task_by_id("build_event_edge_evaluation")
    assert task.status == "completed"
    assert task.artifact_id == "event-edge:matching-manifest"
    assert task.command_args is None
    assert plan.next_task_id is None


def test_decision_blocker_research_plan_rebuilds_event_edge_when_inputs_arrive_after_evaluation(tmp_path):
    repository = JsonFileRepository(tmp_path)
    agenda_at = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    evaluation_at = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
    new_input_at = datetime(2026, 5, 2, 10, 30, tzinfo=UTC)
    repository.save_research_agenda(
        _agenda(
            agenda_id="research-agenda:stale-event-edge",
            created_at=agenda_at,
            expected_artifacts=["strategy_decision", "event_edge_evaluation"],
        )
    )
    _seed_event_edge_prerequisites(repository)
    repository.save_event_edge_evaluation(
        _event_edge_evaluation(
            evaluation_id="event-edge:stale-after-agenda",
            created_at=evaluation_at,
        )
    )
    new_event = _event(2)
    new_event.created_at = new_input_at
    new_event.available_at = new_input_at
    new_event.fetched_at = new_input_at
    repository.save_canonical_event(new_event)
    repository.save_market_reaction_check(
        _market_reaction_for_timestamp(
            new_event,
            event_timestamp_used=new_event.event_time,
            created_at=new_input_at,
        )
    )
    _save_event_candles_for_timestamp(
        repository,
        timestamp=new_event.event_time,
        imported_at=new_input_at,
    )

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=new_input_at + timedelta(minutes=30),
    )

    task = plan.task_by_id("build_event_edge_evaluation")
    assert task.status == "ready"
    assert task.artifact_id is None
    assert task.command_args is not None
    assert plan.next_task_id == "build_event_edge_evaluation"


def test_decision_blocker_research_plan_does_not_reuse_event_edge_when_manifest_mismatches(tmp_path):
    repository = JsonFileRepository(tmp_path)
    agenda_at = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    repository.save_research_agenda(
        _agenda(
            agenda_id="research-agenda:event-manifest-mismatch",
            created_at=agenda_at,
            expected_artifacts=["strategy_decision", "event_edge_evaluation"],
        )
    )
    _seed_event_edge_prerequisites(repository)
    current_candle_ids = [candle.candle_id for candle in repository.load_market_candles()]
    repository.save_event_edge_evaluation(
        _event_edge_evaluation_with_manifest(
            evaluation_id="event-edge:wrong-manifest",
            created_at=agenda_at + timedelta(minutes=10),
            input_event_ids=["canonical-event:wrong"],
            input_reaction_check_ids=["market-reaction:wrong"],
            input_candle_ids=current_candle_ids,
            input_watermark=agenda_at,
        )
    )

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=agenda_at + timedelta(minutes=30),
    )

    task = plan.task_by_id("build_event_edge_evaluation")
    assert task.status == "ready"
    assert task.artifact_id is None
    assert task.command_args is not None
    assert plan.next_task_id == "build_event_edge_evaluation"


def test_decision_blocker_research_plan_does_not_reuse_event_edge_when_manifest_watermark_is_stale(tmp_path):
    repository = JsonFileRepository(tmp_path)
    agenda_at = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    repository.save_research_agenda(
        _agenda(
            agenda_id="research-agenda:event-manifest-stale-watermark",
            created_at=agenda_at,
            expected_artifacts=["strategy_decision", "event_edge_evaluation"],
        )
    )
    _seed_event_edge_prerequisites(repository)
    event_ids, reaction_ids, candle_ids, input_watermark = _seeded_event_edge_manifest(repository)
    repository.save_event_edge_evaluation(
        _event_edge_evaluation_with_manifest(
            evaluation_id="event-edge:stale-manifest-watermark",
            created_at=agenda_at + timedelta(minutes=10),
            input_event_ids=event_ids,
            input_reaction_check_ids=reaction_ids,
            input_candle_ids=candle_ids,
            input_watermark=input_watermark - timedelta(minutes=1),
        )
    )

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=agenda_at + timedelta(minutes=30),
    )

    task = plan.task_by_id("build_event_edge_evaluation")
    assert task.status == "ready"
    assert task.artifact_id is None
    assert task.command_args is not None
    assert plan.next_task_id == "build_event_edge_evaluation"


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


def test_decision_blocker_research_plan_reuses_backtest_when_candle_window_is_unchanged_after_new_agenda(tmp_path):
    repository = JsonFileRepository(tmp_path)
    old_agenda_at = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    new_agenda_at = datetime(2026, 5, 2, 11, 0, tzinfo=UTC)
    candle_start = datetime(2026, 5, 1, 0, 0, tzinfo=UTC)
    old_agenda = _agenda(
        agenda_id="research-agenda:old-backtest",
        created_at=old_agenda_at,
        expected_artifacts=["strategy_decision", "research_dataset", "backtest_result"],
        hypothesis="Latest decision decision:old is HOLD because backtest 未打贏 benchmark.",
    )
    new_agenda = _agenda(
        agenda_id="research-agenda:new-backtest",
        created_at=new_agenda_at,
        expected_artifacts=["strategy_decision", "research_dataset", "backtest_result"],
        hypothesis="Latest decision decision:new is HOLD because backtest 未打贏 benchmark.",
    )
    repository.save_research_agenda(old_agenda)
    repository.save_research_agenda(new_agenda)
    _save_walk_forward_candles(repository, start=candle_start, count=12)
    candles = repository.load_market_candles()
    run = _decision_blocker_backtest_run(
        created_at=old_agenda_at + timedelta(minutes=10),
        start=candles[0].timestamp,
        end=candles[-1].timestamp,
        candle_ids=[candle.candle_id for candle in candles],
    )
    result = _backtest_result_for_run(run, created_at=old_agenda_at + timedelta(minutes=10))
    repository.save_backtest_run(run)
    repository.save_backtest_result(result)

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=new_agenda_at + timedelta(minutes=30),
    )

    task = plan.task_by_id("run_backtest")
    assert task.status == "completed"
    assert task.artifact_id == result.result_id
    assert task.command_args is None
    assert plan.next_task_id is None


def test_decision_blocker_research_plan_does_not_reuse_generic_backtest_after_agenda(tmp_path):
    repository = JsonFileRepository(tmp_path)
    agenda_at = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    candle_start = datetime(2026, 5, 1, 0, 0, tzinfo=UTC)
    repository.save_research_agenda(
        _agenda(
            agenda_id="research-agenda:generic-backtest",
            created_at=agenda_at,
            expected_artifacts=["strategy_decision", "research_dataset", "backtest_result"],
            hypothesis="Latest decision decision:blocked is HOLD because backtest 未打贏 benchmark.",
        )
    )
    _save_walk_forward_candles(repository, start=candle_start, count=12)
    repository.save_backtest_result(_backtest_result(created_at=agenda_at + timedelta(minutes=10)))

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=agenda_at + timedelta(minutes=30),
    )

    task = plan.task_by_id("run_backtest")
    assert task.status == "ready"
    assert task.artifact_id is None
    assert task.command_args is not None
    assert plan.next_task_id == "run_backtest"


def test_decision_blocker_research_plan_does_not_reuse_backtest_with_stale_run_and_late_result(tmp_path):
    repository = JsonFileRepository(tmp_path)
    agenda_at = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    candle_start = datetime(2026, 5, 1, 0, 0, tzinfo=UTC)
    stale_run_at = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    late_result_at = datetime(2026, 5, 2, 9, 10, tzinfo=UTC)
    repository.save_research_agenda(
        _agenda(
            agenda_id="research-agenda:stale-run-late-result",
            created_at=agenda_at,
            expected_artifacts=["strategy_decision", "research_dataset", "backtest_result"],
            hypothesis="Latest decision decision:blocked is HOLD because backtest 未打贏 benchmark.",
        )
    )
    _save_walk_forward_candles(repository, start=candle_start, count=12)
    candles = repository.load_market_candles()
    run = _decision_blocker_backtest_run(
        created_at=stale_run_at,
        start=candles[0].timestamp,
        end=candles[-1].timestamp,
        candle_ids=[candle.candle_id for candle in candles],
    )
    result = _backtest_result_for_run(run, created_at=late_result_at)
    repository.save_backtest_run(run)
    repository.save_backtest_result(result)

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=agenda_at + timedelta(minutes=30),
    )

    task = plan.task_by_id("run_backtest")
    assert task.status == "ready"
    assert task.artifact_id is None
    assert task.command_args is not None
    assert plan.next_task_id == "run_backtest"


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


def test_decision_blocker_research_plan_reuses_walk_forward_when_candle_window_is_unchanged_after_new_agenda(tmp_path):
    repository = JsonFileRepository(tmp_path)
    old_agenda_at = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    new_agenda_at = datetime(2026, 5, 2, 11, 0, tzinfo=UTC)
    candle_start = datetime(2026, 5, 1, 0, 0, tzinfo=UTC)
    repository.save_research_agenda(
        _agenda(
            agenda_id="research-agenda:old-walk-forward",
            created_at=old_agenda_at,
            expected_artifacts=["strategy_decision", "research_dataset", "walk_forward_validation"],
            hypothesis="Latest decision decision:old is HOLD because walk-forward overfit risk.",
        )
    )
    repository.save_research_agenda(
        _agenda(
            agenda_id="research-agenda:new-walk-forward",
            created_at=new_agenda_at,
            expected_artifacts=["strategy_decision", "research_dataset", "walk_forward_validation"],
            hypothesis="Latest decision decision:new is HOLD because walk-forward overfit risk.",
        )
    )
    _save_walk_forward_candles(repository, start=candle_start, count=12)
    repository.save_walk_forward_validation(
        _walk_forward_validation(
            validation_id="walk-forward:already-current",
            created_at=old_agenda_at + timedelta(minutes=10),
            start=candle_start,
            end=candle_start + timedelta(hours=11),
        )
    )

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=new_agenda_at + timedelta(minutes=30),
    )

    task = plan.task_by_id("run_walk_forward_validation")
    assert task.status == "completed"
    assert task.artifact_id == "walk-forward:already-current"
    assert task.command_args is None
    assert plan.next_task_id is None


def test_decision_blocker_research_plan_does_not_reuse_wrong_window_walk_forward_after_agenda(tmp_path):
    repository = JsonFileRepository(tmp_path)
    agenda_at = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    candle_start = datetime(2026, 5, 1, 0, 0, tzinfo=UTC)
    repository.save_research_agenda(
        _agenda(
            agenda_id="research-agenda:wrong-walk-forward",
            created_at=agenda_at,
            expected_artifacts=["strategy_decision", "research_dataset", "walk_forward_validation"],
            hypothesis="Latest decision decision:blocked is HOLD because walk-forward overfit risk.",
        )
    )
    _save_walk_forward_candles(repository, start=candle_start, count=12)
    repository.save_walk_forward_validation(
        _walk_forward_validation(
            validation_id="walk-forward:wrong-window",
            created_at=agenda_at + timedelta(minutes=10),
            start=candle_start - timedelta(hours=2),
            end=candle_start + timedelta(hours=9),
        )
    )

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=agenda_at + timedelta(minutes=30),
    )

    task = plan.task_by_id("run_walk_forward_validation")
    assert task.status == "ready"
    assert task.artifact_id is None
    assert task.command_args is not None
    assert plan.next_task_id == "run_walk_forward_validation"


def test_decision_blocker_research_plan_marks_backtest_complete_when_current_window_result_exists(tmp_path):
    repository = JsonFileRepository(tmp_path)
    agenda_created_at = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    candle_start = datetime(2026, 5, 1, 0, 0, tzinfo=UTC)
    agenda = _agenda(
        agenda_id="research-agenda:backtest-complete",
        created_at=agenda_created_at,
        expected_artifacts=["strategy_decision", "research_dataset", "backtest_result"],
        hypothesis="Latest decision decision:blocked is HOLD because backtest 未打贏 benchmark.",
    )
    repository.save_research_agenda(agenda)
    _save_walk_forward_candles(repository, start=candle_start, count=12)
    candles = repository.load_market_candles()
    run = _decision_blocker_backtest_run(
        created_at=agenda_created_at + timedelta(minutes=5),
        start=candles[0].timestamp,
        end=candles[-1].timestamp,
        candle_ids=[candle.candle_id for candle in candles],
    )
    result = _backtest_result_for_run(run, created_at=agenda_created_at + timedelta(minutes=5))
    repository.save_backtest_run(run)
    repository.save_backtest_result(result)

    plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=agenda_created_at + timedelta(minutes=10),
    )

    task = plan.task_by_id("run_backtest")
    assert task.status == "completed"
    assert task.artifact_id == result.result_id
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
        "--as-of",
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
