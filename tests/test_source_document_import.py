from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from forecast_loop.cli import main
from forecast_loop.health import run_health_check
from forecast_loop.models import SourceDocument
from forecast_loop.storage import JsonFileRepository


def _write_sample_news(path) -> None:
    rows = [
        {
            "stable_source_id": "sample-news-btc-etf-flow",
            "source_url": "https://example.test/news/btc-etf-flow",
            "published_at": "2026-04-28T10:00:00+00:00",
            "available_at": "2026-04-28T10:01:00+00:00",
            "headline": "Bitcoin ETF flows accelerate",
            "summary": "Fixture news item for BTC-USD source document import.",
            "body": "Bitcoin ETF inflows accelerated during the fixture window.",
            "language": "en",
            "entities": ["Bitcoin", "ETF"],
            "symbols": ["BTC-USD"],
            "topics": ["crypto_flow"],
        }
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_import_source_documents_cli_stores_registry_documents_and_ingestion_run(tmp_path, capsys):
    input_path = tmp_path / "sample_news.jsonl"
    _write_sample_news(input_path)

    exit_code = main(
        [
            "import-source-documents",
            "--storage-dir",
            str(tmp_path),
            "--input",
            str(input_path),
            "--source",
            "sample_news",
            "--imported-at",
            "2026-04-28T10:05:00+00:00",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    repository = JsonFileRepository(tmp_path)
    registry_entries = repository.load_source_registry_entries()
    documents = repository.load_source_documents()
    ingestion_runs = repository.load_source_ingestion_runs()

    assert exit_code == 0
    assert payload["source_id"] == "sample_news"
    assert payload["fetched_count"] == 1
    assert payload["stored_count"] == 1
    assert len(registry_entries) == 1
    assert registry_entries[0].source_id == "sample_news"
    assert len(documents) == 1
    assert documents[0].source_id == "sample_news"
    assert documents[0].source_type == "news"
    assert documents[0].raw_text_hash
    assert documents[0].normalized_text_hash
    assert documents[0].ingestion_run_id == ingestion_runs[0].ingestion_run_id
    assert ingestion_runs[0].source_name == "Sample News Fixture"
    assert ingestion_runs[0].document_ids == [documents[0].document_id]


def test_source_registry_cli_lists_imported_source(tmp_path, capsys):
    input_path = tmp_path / "sample_news.jsonl"
    _write_sample_news(input_path)
    assert main(
        [
            "import-source-documents",
            "--storage-dir",
            str(tmp_path),
            "--input",
            str(input_path),
            "--source",
            "sample_news",
            "--imported-at",
            "2026-04-28T10:05:00+00:00",
        ]
    ) == 0
    capsys.readouterr()

    assert main(["source-registry", "--storage-dir", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["source_count"] == 1
    assert payload["sources"][0]["source_id"] == "sample_news"
    assert payload["sources"][0]["allowed_for_research_only"] is True


def test_import_source_documents_registry_metadata_is_authoritative(tmp_path):
    input_path = tmp_path / "sample_news.jsonl"
    row = {
        "stable_source_id": "sample-news-authority-check",
        "source_url": "https://example.test/news/authority-check",
        "published_at": "2026-04-28T10:00:00+00:00",
        "available_at": "2026-04-28T10:01:00+00:00",
        "headline": "Authority check",
        "summary": "Fixture row attempts to override registry metadata.",
        "body": "Fixture body.",
        "source_name": "Fake Official Source",
        "source_type": "official",
        "source_reliability_score": 100.0,
        "license_note": "fake unrestricted license",
    }
    input_path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    assert main(
        [
            "import-source-documents",
            "--storage-dir",
            str(tmp_path),
            "--input",
            str(input_path),
            "--source",
            "sample_news",
            "--imported-at",
            "2026-04-28T10:05:00+00:00",
        ]
    ) == 0

    document = JsonFileRepository(tmp_path).load_source_documents()[0]
    assert document.source_name == "Sample News Fixture"
    assert document.source_type == "news"
    assert document.source_reliability_score == 65.0
    assert document.license_note == "Local fixture only."


def test_import_source_documents_rejects_unknown_source(tmp_path, capsys):
    input_path = tmp_path / "sample_news.jsonl"
    _write_sample_news(input_path)

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "import-source-documents",
                "--storage-dir",
                str(tmp_path),
                "--input",
                str(input_path),
                "--source",
                "unknown_news",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "unknown source id: unknown_news" in captured.err


def test_health_check_flags_source_document_with_missing_registry_entry(tmp_path):
    repository = JsonFileRepository(tmp_path)
    document = SourceDocument.from_dict(
        {
            "document_id": "source-document:missing-registry",
            "source_id": "missing_source",
            "source_name": "Missing Source",
            "source_type": "news",
            "source_url": "https://example.test/missing",
            "stable_source_id": "missing-source-doc",
            "published_at": "2026-04-28T10:00:00+00:00",
            "available_at": "2026-04-28T10:01:00+00:00",
            "fetched_at": "2026-04-28T10:02:00+00:00",
            "processed_at": "2026-04-28T10:03:00+00:00",
            "language": "en",
            "headline": "Missing registry source",
            "summary": "Fixture document with source_id but no registry entry.",
            "raw_text_hash": "rawhash",
            "normalized_text_hash": "normalizedhash",
            "body_excerpt": "Missing registry source",
            "entities": [],
            "symbols": ["BTC-USD"],
            "topics": ["test"],
            "source_reliability_score": 50.0,
            "duplicate_group_id": None,
            "license_note": "fixture",
            "ingestion_run_id": None,
        }
    )
    repository.save_source_document(document)

    health = run_health_check(
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=datetime(2026, 4, 28, 12, 0, tzinfo=UTC),
        create_repair_request=False,
    )

    codes = {finding.code for finding in health.findings}
    assert "source_document_missing_source_registry_entry" in codes
