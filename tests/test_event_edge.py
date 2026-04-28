from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from forecast_loop.cli import main
from forecast_loop.event_edge import build_event_edge_evaluations
from forecast_loop.models import CanonicalEvent, MarketCandle, MarketCandleRecord, MarketReactionCheck
from forecast_loop.storage import JsonFileRepository


def _created_at() -> datetime:
    return datetime(2026, 4, 28, 12, 0, tzinfo=UTC)


def _event(index: int, *, symbol: str = "BTC-USD") -> CanonicalEvent:
    event_time = datetime(2026, 4, 18, 10, 0, tzinfo=UTC) + timedelta(days=index * 2)
    return CanonicalEvent(
        event_id=f"canonical-event:edge-{index}",
        event_family="crypto_flow",
        event_type="CRYPTO_FLOW",
        symbol=symbol,
        title=f"Event {index}",
        summary="Historical edge fixture.",
        event_time=event_time,
        published_at=event_time,
        available_at=event_time,
        fetched_at=event_time,
        source_document_ids=[f"source-document:edge-{index}"],
        primary_document_id=f"source-document:edge-{index}",
        credibility_score=80.0,
        cross_source_count=1,
        official_source_flag=False,
        duplicate_group_id=f"duplicate-group:edge-{index}",
        status="reliable",
        created_at=event_time,
    )


def _market_reaction(event: CanonicalEvent, *, passed: bool = True) -> MarketReactionCheck:
    return MarketReactionCheck(
        check_id=f"market-reaction:{event.event_id.split(':')[-1]}",
        event_id=event.event_id,
        symbol=event.symbol,
        created_at=event.created_at or event.available_at or _created_at(),
        decision_timestamp=event.created_at or event.available_at or _created_at(),
        event_timestamp_used=event.available_at or event.fetched_at,
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


def _save_event_candles(repository: JsonFileRepository, event: CanonicalEvent, *, forward_return: float) -> None:
    event_time = event.available_at or event.fetched_at
    imported_at = _created_at()
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
                    high=close + 1,
                    low=close - 1,
                    close=close,
                    volume=1_000,
                ),
                symbol=event.symbol,
                source="fixture",
                imported_at=imported_at,
            )
        )


def _save_single_candle(
    repository: JsonFileRepository,
    *,
    symbol: str,
    timestamp: datetime,
    close: float,
    imported_at: datetime,
) -> None:
    repository.save_market_candle(
        MarketCandleRecord.from_candle(
            MarketCandle(
                timestamp=timestamp,
                open=close,
                high=close + 1,
                low=close - 1,
                close=close,
                volume=1_000,
            ),
            symbol=symbol,
            source="fixture",
            imported_at=imported_at,
        )
    )


def test_build_event_edge_passes_when_after_cost_edge_is_positive(tmp_path):
    repository = JsonFileRepository(tmp_path)
    for index, forward_return in enumerate([0.04, 0.03, 0.02], start=1):
        event = _event(index)
        repository.save_canonical_event(event)
        repository.save_market_reaction_check(_market_reaction(event, passed=True))
        _save_event_candles(repository, event, forward_return=forward_return)

    result = build_event_edge_evaluations(
        storage_dir=tmp_path,
        created_at=_created_at(),
        symbol="BTC-USD",
        horizon_hours=24,
        min_sample_size=3,
        estimated_cost_bps=10.0,
    )

    evaluations = repository.load_event_edge_evaluations()
    assert result.evaluation_count == 1
    assert len(evaluations) == 1
    assert evaluations[0].sample_n == 3
    assert evaluations[0].hit_rate == 1.0
    assert evaluations[0].average_excess_return_after_costs is not None
    assert evaluations[0].average_excess_return_after_costs > 0
    assert evaluations[0].passed is True
    assert evaluations[0].blocked_reason is None


def test_build_event_edge_blocks_when_sample_size_is_too_low(tmp_path):
    repository = JsonFileRepository(tmp_path)
    event = _event(1)
    repository.save_canonical_event(event)
    repository.save_market_reaction_check(_market_reaction(event, passed=True))
    _save_event_candles(repository, event, forward_return=0.04)

    build_event_edge_evaluations(
        storage_dir=tmp_path,
        created_at=_created_at(),
        symbol="BTC-USD",
        horizon_hours=24,
        min_sample_size=3,
        estimated_cost_bps=10.0,
    )

    evaluation = repository.load_event_edge_evaluations()[0]
    assert evaluation.sample_n == 1
    assert evaluation.passed is False
    assert evaluation.blocked_reason == "insufficient_sample_size"
    assert "insufficient_sample_size" in evaluation.flags


def test_build_event_edge_ignores_failed_market_reaction_checks(tmp_path):
    repository = JsonFileRepository(tmp_path)
    passed_event = _event(1)
    failed_event = _event(2)
    repository.save_canonical_event(passed_event)
    repository.save_canonical_event(failed_event)
    repository.save_market_reaction_check(_market_reaction(passed_event, passed=True))
    repository.save_market_reaction_check(_market_reaction(failed_event, passed=False))
    _save_event_candles(repository, passed_event, forward_return=0.04)
    _save_event_candles(repository, failed_event, forward_return=0.10)

    build_event_edge_evaluations(
        storage_dir=tmp_path,
        created_at=_created_at(),
        symbol="BTC-USD",
        horizon_hours=24,
        min_sample_size=1,
        estimated_cost_bps=10.0,
    )

    evaluation = repository.load_event_edge_evaluations()[0]
    assert evaluation.sample_n == 1
    assert evaluation.average_forward_return == pytest.approx(0.04)


def test_build_event_edge_uses_latest_market_reaction_per_event(tmp_path):
    repository = JsonFileRepository(tmp_path)
    event = _event(1)
    old_passed = _market_reaction(event, passed=True)
    old_passed.check_id = "market-reaction:old-passed"
    old_passed.created_at = event.created_at or event.available_at
    newer_failed = _market_reaction(event, passed=False)
    newer_failed.check_id = "market-reaction:newer-failed"
    newer_failed.created_at = (event.created_at or event.available_at) + timedelta(hours=1)
    repository.save_canonical_event(event)
    repository.save_market_reaction_check(old_passed)
    repository.save_market_reaction_check(newer_failed)
    _save_event_candles(repository, event, forward_return=0.04)

    result = build_event_edge_evaluations(
        storage_dir=tmp_path,
        created_at=_created_at(),
        symbol="BTC-USD",
        horizon_hours=24,
        min_sample_size=1,
    )

    assert result.evaluation_count == 0
    assert repository.load_event_edge_evaluations() == []


def test_build_event_edge_rejects_non_hour_event_timestamp_labels(tmp_path):
    repository = JsonFileRepository(tmp_path)
    event = _event(1)
    reaction = _market_reaction(event, passed=True)
    reaction.event_timestamp_used = (event.available_at or event.fetched_at) + timedelta(minutes=30)
    repository.save_canonical_event(event)
    repository.save_market_reaction_check(reaction)
    _save_event_candles(repository, event, forward_return=0.04)

    result = build_event_edge_evaluations(
        storage_dir=tmp_path,
        created_at=_created_at(),
        symbol="BTC-USD",
        horizon_hours=24,
        min_sample_size=1,
    )

    assert result.evaluation_count == 0
    assert repository.load_event_edge_evaluations() == []


def test_build_event_edge_ignores_market_reactions_created_after_build_time(tmp_path):
    repository = JsonFileRepository(tmp_path)
    event = _event(1)
    future_reaction = _market_reaction(event, passed=True)
    future_reaction.created_at = _created_at() + timedelta(minutes=5)
    repository.save_canonical_event(event)
    repository.save_market_reaction_check(future_reaction)
    _save_event_candles(repository, event, forward_return=0.04)

    result = build_event_edge_evaluations(
        storage_dir=tmp_path,
        created_at=_created_at(),
        symbol="BTC-USD",
        horizon_hours=24,
        min_sample_size=1,
    )

    assert result.evaluation_count == 0
    assert repository.load_event_edge_evaluations() == []


def test_build_event_edge_ignores_candles_imported_after_build_time(tmp_path):
    repository = JsonFileRepository(tmp_path)
    event = _event(1)
    event_time = event.available_at or event.fetched_at
    repository.save_canonical_event(event)
    repository.save_market_reaction_check(_market_reaction(event, passed=True))
    _save_single_candle(
        repository,
        symbol="BTC-USD",
        timestamp=event_time,
        close=100.0,
        imported_at=_created_at() + timedelta(minutes=5),
    )
    _save_single_candle(
        repository,
        symbol="BTC-USD",
        timestamp=event_time + timedelta(hours=24),
        close=104.0,
        imported_at=_created_at() + timedelta(minutes=5),
    )

    result = build_event_edge_evaluations(
        storage_dir=tmp_path,
        created_at=_created_at(),
        symbol="BTC-USD",
        horizon_hours=24,
        min_sample_size=1,
    )

    assert result.evaluation_count == 0
    assert repository.load_event_edge_evaluations() == []


def test_build_event_edge_requires_exact_forward_horizon_boundary(tmp_path):
    repository = JsonFileRepository(tmp_path)
    event = _event(1)
    event_time = event.available_at or event.fetched_at
    repository.save_canonical_event(event)
    repository.save_market_reaction_check(_market_reaction(event, passed=True))
    _save_single_candle(
        repository,
        symbol="BTC-USD",
        timestamp=event_time,
        close=100.0,
        imported_at=_created_at(),
    )
    _save_single_candle(
        repository,
        symbol="BTC-USD",
        timestamp=event_time + timedelta(hours=23),
        close=104.0,
        imported_at=_created_at(),
    )

    result = build_event_edge_evaluations(
        storage_dir=tmp_path,
        created_at=_created_at(),
        symbol="BTC-USD",
        horizon_hours=24,
        min_sample_size=1,
    )

    assert result.evaluation_count == 0
    assert repository.load_event_edge_evaluations() == []


def test_build_event_edge_cli_is_idempotent_and_requires_created_at(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    for index, forward_return in enumerate([0.04, 0.03, 0.02], start=1):
        event = _event(index)
        repository.save_canonical_event(event)
        repository.save_market_reaction_check(_market_reaction(event, passed=True))
        _save_event_candles(repository, event, forward_return=forward_return)

    with pytest.raises(SystemExit) as exc_info:
        main(["build-event-edge", "--storage-dir", str(tmp_path), "--symbol", "BTC-USD"])
    assert exc_info.value.code == 2
    assert "--created-at" in capsys.readouterr().err

    args = [
        "build-event-edge",
        "--storage-dir",
        str(tmp_path),
        "--symbol",
        "BTC-USD",
        "--created-at",
        _created_at().isoformat(),
        "--horizon-hours",
        "24",
        "--min-sample-size",
        "3",
    ]
    assert main(args) == 0
    first_payload = json.loads(capsys.readouterr().out)
    assert main(args) == 0
    second_payload = json.loads(capsys.readouterr().out)

    assert first_payload["evaluation_ids"] == second_payload["evaluation_ids"]
    assert first_payload["evaluation_count"] == 1
    assert len(repository.load_event_edge_evaluations()) == 1
