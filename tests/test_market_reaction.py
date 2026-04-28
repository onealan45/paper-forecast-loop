from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from forecast_loop.cli import main
from forecast_loop.market_reaction import build_market_reactions
from forecast_loop.models import (
    CanonicalEvent,
    EventReliabilityCheck,
    MarketCandle,
    MarketCandleRecord,
)
from forecast_loop.storage import JsonFileRepository


def _now() -> datetime:
    return datetime(2026, 4, 28, 12, 0, tzinfo=UTC)


def _event(*, event_id: str = "canonical-event:reaction", created_at: datetime | None = None) -> CanonicalEvent:
    now = _now()
    return CanonicalEvent(
        event_id=event_id,
        event_family="crypto_flow",
        event_type="CRYPTO_FLOW",
        symbol="BTC-USD",
        title="ETF flows accelerate",
        summary="Fixture event.",
        event_time=now - timedelta(hours=1),
        published_at=now - timedelta(hours=1),
        available_at=now - timedelta(hours=1),
        fetched_at=now - timedelta(minutes=50),
        source_document_ids=["source-document:reaction"],
        primary_document_id="source-document:reaction",
        credibility_score=85.0,
        cross_source_count=2,
        official_source_flag=False,
        duplicate_group_id="duplicate-group:reaction",
        status="reliable",
        created_at=created_at or now - timedelta(minutes=45),
    )


def _reliability_check(event_id: str, *, passed: bool = True) -> EventReliabilityCheck:
    return EventReliabilityCheck(
        check_id=f"event-reliability:{event_id.split(':')[-1]}",
        event_id=event_id,
        created_at=_now() - timedelta(minutes=45),
        symbol="BTC-USD",
        source_type="news",
        source_reliability_score=85.0 if passed else 65.0,
        official_source_flag=False,
        cross_source_count=2,
        duplicate_count=1,
        has_stable_source=True,
        has_required_timestamps=True,
        raw_hash_present=True,
        passed=passed,
        blocked_reason=None if passed else "source_reliability_below_threshold",
        flags=[] if passed else ["source_reliability_below_threshold"],
    )


def _save_hourly_candles(
    repository: JsonFileRepository,
    closes: dict[int, float],
    *,
    base_volume: float = 1_000,
    imported_at: datetime | None = None,
) -> None:
    event_time = _now() - timedelta(hours=1)
    candle_imported_at = imported_at or _now()
    for hour_offset, close in closes.items():
        timestamp = event_time + timedelta(hours=hour_offset)
        repository.save_market_candle(
            MarketCandleRecord.from_candle(
                MarketCandle(
                    timestamp=timestamp,
                    open=close,
                    high=close + 1,
                    low=close - 1,
                    close=close,
                    volume=base_volume + hour_offset,
                ),
                symbol="BTC-USD",
                source="fixture",
                imported_at=candle_imported_at,
            )
        )


def test_build_market_reactions_passes_when_pre_event_drift_is_small(tmp_path):
    repository = JsonFileRepository(tmp_path)
    event = _event()
    repository.save_canonical_event(event)
    repository.save_event_reliability_check(_reliability_check(event.event_id, passed=True))
    _save_hourly_candles(
        repository,
        {
            -4: 100.0,
            -1: 100.4,
            0: 100.5,
            1: 100.8,
        },
    )

    result = build_market_reactions(
        storage_dir=tmp_path,
        created_at=_now(),
        symbol="BTC-USD",
        already_priced_return_threshold=0.03,
    )

    checks = repository.load_market_reaction_checks()
    assert result.market_reaction_check_count == 1
    assert len(checks) == 1
    assert checks[0].event_id == event.event_id
    assert checks[0].passed is True
    assert checks[0].already_priced is False
    assert checks[0].blocked_reason is None
    assert checks[0].pre_event_ret_4h is not None
    assert abs(checks[0].pre_event_ret_4h) < 0.03


def test_build_market_reactions_blocks_already_priced_event(tmp_path):
    repository = JsonFileRepository(tmp_path)
    event = _event()
    repository.save_canonical_event(event)
    repository.save_event_reliability_check(_reliability_check(event.event_id, passed=True))
    _save_hourly_candles(
        repository,
        {
            -4: 100.0,
            -1: 110.0,
            0: 112.0,
            1: 113.0,
        },
    )

    build_market_reactions(
        storage_dir=tmp_path,
        created_at=_now(),
        symbol="BTC-USD",
        already_priced_return_threshold=0.03,
    )

    check = repository.load_market_reaction_checks()[0]
    assert check.passed is False
    assert check.already_priced is True
    assert check.blocked_reason == "already_priced"
    assert "already_priced" in check.flags


def test_build_market_reactions_blocks_unreliable_event_before_price_gate(tmp_path):
    repository = JsonFileRepository(tmp_path)
    event = _event()
    repository.save_canonical_event(event)
    repository.save_event_reliability_check(_reliability_check(event.event_id, passed=False))
    _save_hourly_candles(
        repository,
        {
            -4: 100.0,
            -1: 100.2,
            0: 100.3,
        },
    )

    build_market_reactions(storage_dir=tmp_path, created_at=_now(), symbol="BTC-USD")

    check = repository.load_market_reaction_checks()[0]
    assert check.passed is False
    assert check.already_priced is False
    assert check.blocked_reason == "event_reliability_not_passed"
    assert "event_reliability_not_passed" in check.flags


def test_build_market_reactions_ignores_candles_imported_after_created_at(tmp_path):
    repository = JsonFileRepository(tmp_path)
    event = _event()
    repository.save_canonical_event(event)
    repository.save_event_reliability_check(_reliability_check(event.event_id, passed=True))
    _save_hourly_candles(
        repository,
        {
            -4: 100.0,
            -1: 100.2,
            0: 100.3,
        },
        imported_at=_now() + timedelta(minutes=5),
    )

    build_market_reactions(storage_dir=tmp_path, created_at=_now(), symbol="BTC-USD")

    check = repository.load_market_reaction_checks()[0]
    assert check.passed is False
    assert check.pre_event_ret_4h is None
    assert check.blocked_reason == "insufficient_pre_event_coverage"


def test_build_market_reactions_ignores_reliability_checks_created_after_build_time(tmp_path):
    repository = JsonFileRepository(tmp_path)
    event = _event()
    future_reliability = _reliability_check(event.event_id, passed=True)
    future_reliability.created_at = _now() + timedelta(minutes=5)
    repository.save_canonical_event(event)
    repository.save_event_reliability_check(future_reliability)
    _save_hourly_candles(
        repository,
        {
            -4: 100.0,
            -1: 100.2,
            0: 100.3,
        },
    )

    build_market_reactions(storage_dir=tmp_path, created_at=_now(), symbol="BTC-USD")

    check = repository.load_market_reaction_checks()[0]
    assert check.passed is False
    assert check.blocked_reason == "event_reliability_not_passed"


def test_build_market_reactions_requires_exact_pre_event_4h_boundary(tmp_path):
    repository = JsonFileRepository(tmp_path)
    event = _event()
    repository.save_canonical_event(event)
    repository.save_event_reliability_check(_reliability_check(event.event_id, passed=True))
    _save_hourly_candles(
        repository,
        {
            -5: 95.0,
            -1: 100.2,
            0: 100.3,
        },
    )

    build_market_reactions(storage_dir=tmp_path, created_at=_now(), symbol="BTC-USD")

    check = repository.load_market_reaction_checks()[0]
    assert check.passed is False
    assert check.pre_event_ret_4h is None
    assert check.blocked_reason == "insufficient_pre_event_coverage"


def test_build_market_reactions_cli_is_idempotent_and_requires_created_at(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    event = _event()
    repository.save_canonical_event(event)
    repository.save_event_reliability_check(_reliability_check(event.event_id, passed=True))
    _save_hourly_candles(
        repository,
        {
            -4: 100.0,
            -1: 100.2,
            0: 100.3,
        },
    )

    with pytest.raises(SystemExit) as exc_info:
        main(["build-market-reactions", "--storage-dir", str(tmp_path), "--symbol", "BTC-USD"])
    assert exc_info.value.code == 2
    assert "--created-at" in capsys.readouterr().err

    args = [
        "build-market-reactions",
        "--storage-dir",
        str(tmp_path),
        "--symbol",
        "BTC-USD",
        "--created-at",
        _now().isoformat(),
    ]
    assert main(args) == 0
    first_payload = json.loads(capsys.readouterr().out)
    assert main(args) == 0
    second_payload = json.loads(capsys.readouterr().out)

    assert first_payload["check_ids"] == second_payload["check_ids"]
    assert first_payload["market_reaction_check_count"] == 1
    assert len(repository.load_market_reaction_checks()) == 1
