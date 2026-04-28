from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from forecast_loop.cli import main
from forecast_loop.event_reliability import build_event_reliability
from forecast_loop.models import SourceDocument
from forecast_loop.storage import JsonFileRepository


def _now() -> datetime:
    return datetime(2026, 4, 28, 12, 0, tzinfo=UTC)


def _source_document(
    *,
    document_id: str,
    source_id: str,
    source_name: str,
    source_type: str,
    reliability_score: float,
    duplicate_group_id: str | None,
    symbol: str = "BTC-USD",
    minutes_offset: int = 0,
) -> SourceDocument:
    now = _now()
    return SourceDocument(
        document_id=document_id,
        source_id=source_id,
        source_name=source_name,
        source_type=source_type,
        source_url=f"https://example.test/{document_id}",
        stable_source_id=f"{source_id}:{document_id}",
        published_at=now - timedelta(minutes=30 - minutes_offset),
        available_at=now - timedelta(minutes=29 - minutes_offset),
        fetched_at=now - timedelta(minutes=20 - minutes_offset),
        processed_at=now - timedelta(minutes=10 - minutes_offset),
        language="en",
        headline="Bitcoin ETF flows accelerate",
        summary="ETF flow fixture for event reliability.",
        raw_text_hash=f"rawhash-{document_id}",
        normalized_text_hash=f"normalizedhash-{document_id}",
        body_excerpt="Bitcoin ETF inflows accelerated during the fixture window.",
        entities=["Bitcoin", "ETF"],
        symbols=[symbol],
        topics=["crypto_flow"],
        source_reliability_score=reliability_score,
        duplicate_group_id=duplicate_group_id,
        license_note="fixture",
        ingestion_run_id="source-ingestion-run:test",
    )


def test_build_events_deduplicates_documents_and_writes_reliability_checks(tmp_path):
    repository = JsonFileRepository(tmp_path)
    official = _source_document(
        document_id="source-document:official-flow",
        source_id="official_feed",
        source_name="Official Feed",
        source_type="official",
        reliability_score=95.0,
        duplicate_group_id="duplicate-group:btc-etf-flow",
    )
    secondary = _source_document(
        document_id="source-document:secondary-flow",
        source_id="secondary_news",
        source_name="Secondary News",
        source_type="news",
        reliability_score=80.0,
        duplicate_group_id="duplicate-group:btc-etf-flow",
        minutes_offset=1,
    )
    repository.save_source_document(official)
    repository.save_source_document(secondary)

    result = build_event_reliability(
        storage_dir=tmp_path,
        created_at=_now(),
        symbol="BTC-USD",
        min_reliability_score=70.0,
    )

    events = repository.load_canonical_events()
    checks = repository.load_event_reliability_checks()
    assert result.event_count == 1
    assert result.reliability_check_count == 1
    assert len(events) == 1
    assert len(checks) == 1
    assert set(events[0].source_document_ids) == {official.document_id, secondary.document_id}
    assert events[0].primary_document_id == official.document_id
    assert events[0].event_family == "crypto_flow"
    assert events[0].event_type == "CRYPTO_FLOW"
    assert events[0].symbol == "BTC-USD"
    assert events[0].cross_source_count == 2
    assert events[0].duplicate_group_id == "duplicate-group:btc-etf-flow"
    assert events[0].status == "reliable"
    assert checks[0].event_id == events[0].event_id
    assert checks[0].passed is True
    assert checks[0].duplicate_count == 1
    assert checks[0].blocked_reason is None


def test_build_events_blocks_low_reliability_source(tmp_path):
    repository = JsonFileRepository(tmp_path)
    low_reliability = _source_document(
        document_id="source-document:low-reliability",
        source_id="sample_news",
        source_name="Sample News Fixture",
        source_type="news",
        reliability_score=65.0,
        duplicate_group_id=None,
    )
    repository.save_source_document(low_reliability)

    result = build_event_reliability(
        storage_dir=tmp_path,
        created_at=_now(),
        symbol="BTC-USD",
        min_reliability_score=70.0,
    )

    event = repository.load_canonical_events()[0]
    check = repository.load_event_reliability_checks()[0]
    assert result.event_count == 1
    assert event.status == "blocked"
    assert check.passed is False
    assert check.source_reliability_score == 65.0
    assert check.blocked_reason == "source_reliability_below_threshold"
    assert "source_reliability_below_threshold" in check.flags


def test_build_events_preserves_requested_symbol_for_multi_symbol_document(tmp_path):
    repository = JsonFileRepository(tmp_path)
    document = _source_document(
        document_id="source-document:multi-symbol",
        source_id="official_feed",
        source_name="Official Feed",
        source_type="official",
        reliability_score=95.0,
        duplicate_group_id="duplicate-group:multi-symbol",
        symbol="BTC-USD",
    )
    document.symbols = ["BTC-USD", "ETH-USD"]
    repository.save_source_document(document)

    result = build_event_reliability(
        storage_dir=tmp_path,
        created_at=_now(),
        symbol="ETH-USD",
        min_reliability_score=70.0,
    )

    event = repository.load_canonical_events()[0]
    check = repository.load_event_reliability_checks()[0]
    assert result.event_count == 1
    assert event.symbol == "ETH-USD"
    assert check.symbol == "ETH-USD"


def test_build_events_excludes_documents_fetched_after_created_at(tmp_path):
    repository = JsonFileRepository(tmp_path)
    document = _source_document(
        document_id="source-document:future-fetched",
        source_id="official_feed",
        source_name="Official Feed",
        source_type="official",
        reliability_score=95.0,
        duplicate_group_id="duplicate-group:future-fetched",
    )
    document.fetched_at = _now() + timedelta(minutes=5)
    document.processed_at = _now() + timedelta(minutes=6)
    repository.save_source_document(document)

    result = build_event_reliability(
        storage_dir=tmp_path,
        created_at=_now(),
        symbol="BTC-USD",
        min_reliability_score=70.0,
    )

    assert result.event_count == 0
    assert result.reliability_check_count == 0
    assert repository.load_canonical_events() == []
    assert repository.load_event_reliability_checks() == []


def test_build_events_refreshes_existing_duplicate_group_event(tmp_path):
    repository = JsonFileRepository(tmp_path)
    low_reliability = _source_document(
        document_id="source-document:first-low",
        source_id="sample_news",
        source_name="Sample News Fixture",
        source_type="news",
        reliability_score=65.0,
        duplicate_group_id="duplicate-group:incremental",
    )
    high_reliability = _source_document(
        document_id="source-document:second-official",
        source_id="official_feed",
        source_name="Official Feed",
        source_type="official",
        reliability_score=95.0,
        duplicate_group_id="duplicate-group:incremental",
        minutes_offset=1,
    )
    repository.save_source_document(low_reliability)
    first_result = build_event_reliability(
        storage_dir=tmp_path,
        created_at=_now(),
        symbol="BTC-USD",
        min_reliability_score=70.0,
    )
    first_event = repository.load_canonical_events()[0]
    assert first_event.status == "blocked"

    repository.save_source_document(high_reliability)
    second_result = build_event_reliability(
        storage_dir=tmp_path,
        created_at=_now(),
        symbol="BTC-USD",
        min_reliability_score=70.0,
    )

    events = repository.load_canonical_events()
    checks = repository.load_event_reliability_checks()
    assert second_result.event_ids == first_result.event_ids
    assert len(events) == 1
    assert len(checks) == 1
    assert set(events[0].source_document_ids) == {
        low_reliability.document_id,
        high_reliability.document_id,
    }
    assert events[0].primary_document_id == high_reliability.document_id
    assert events[0].status == "reliable"
    assert checks[0].passed is True


def test_build_events_versions_canonical_events_across_created_at(tmp_path):
    repository = JsonFileRepository(tmp_path)
    first_document = _source_document(
        document_id="source-document:first-version",
        source_id="sample_news",
        source_name="Sample News Fixture",
        source_type="news",
        reliability_score=65.0,
        duplicate_group_id="duplicate-group:versioned",
    )
    second_document = _source_document(
        document_id="source-document:second-version",
        source_id="official_feed",
        source_name="Official Feed",
        source_type="official",
        reliability_score=95.0,
        duplicate_group_id="duplicate-group:versioned",
        minutes_offset=1,
    )
    first_created_at = _now()
    second_created_at = _now() + timedelta(minutes=10)
    repository.save_source_document(first_document)
    first_result = build_event_reliability(
        storage_dir=tmp_path,
        created_at=first_created_at,
        symbol="BTC-USD",
        min_reliability_score=70.0,
    )
    first_event_id = first_result.event_ids[0]

    repository.save_source_document(second_document)
    second_result = build_event_reliability(
        storage_dir=tmp_path,
        created_at=second_created_at,
        symbol="BTC-USD",
        min_reliability_score=70.0,
    )

    events = {event.event_id: event for event in repository.load_canonical_events()}
    checks = repository.load_event_reliability_checks()
    assert second_result.event_ids != first_result.event_ids
    assert len(events) == 2
    assert len(checks) == 2
    assert events[first_event_id].source_document_ids == [first_document.document_id]
    assert checks[0].event_id == first_result.event_ids[0]
    assert checks[1].event_id == second_result.event_ids[0]


def test_build_events_cli_outputs_counts_and_is_idempotent(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    document = _source_document(
        document_id="source-document:cli-flow",
        source_id="official_feed",
        source_name="Official Feed",
        source_type="official",
        reliability_score=95.0,
        duplicate_group_id="duplicate-group:cli-flow",
    )
    repository.save_source_document(document)

    args = [
        "build-events",
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

    assert first_payload["event_count"] == 1
    assert first_payload["reliability_check_count"] == 1
    assert second_payload["event_ids"] == first_payload["event_ids"]
    assert len(repository.load_canonical_events()) == 1
    assert len(repository.load_event_reliability_checks()) == 1


def test_build_events_cli_requires_created_at(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "build-events",
                "--storage-dir",
                str(tmp_path),
                "--symbol",
                "BTC-USD",
            ]
        )

    assert exc_info.value.code == 2
    assert "--created-at" in capsys.readouterr().err
