from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha1
import json
from pathlib import Path
import re

from forecast_loop.models import SourceDocument, SourceIngestionRun, SourceRegistryEntry
from forecast_loop.source_registry import resolve_source_registry_entry
from forecast_loop.storage import JsonFileRepository


@dataclass(slots=True)
class SourceDocumentImportResult:
    storage_dir: Path
    input_path: Path
    source_id: str
    ingestion_run_id: str
    document_ids: list[str]
    fetched_count: int
    stored_count: int
    skipped_duplicate_count: int

    def to_dict(self) -> dict:
        return {
            "storage_dir": str(self.storage_dir.resolve()),
            "input_path": str(self.input_path.resolve()),
            "source_id": self.source_id,
            "ingestion_run_id": self.ingestion_run_id,
            "document_ids": self.document_ids,
            "fetched_count": self.fetched_count,
            "stored_count": self.stored_count,
            "skipped_duplicate_count": self.skipped_duplicate_count,
        }


def import_source_documents(
    *,
    storage_dir: Path | str,
    input_path: Path | str,
    source_id: str,
    imported_at: datetime,
) -> SourceDocumentImportResult:
    if imported_at.tzinfo is None or imported_at.utcoffset() is None:
        raise ValueError("imported_at must be timezone-aware")
    input_file = Path(input_path)
    if not input_file.exists():
        raise ValueError(f"source document input does not exist: {input_file}")
    repository = JsonFileRepository(storage_dir)
    registry_entry = resolve_source_registry_entry(repository=repository, source_id=source_id)
    imported_at_utc = imported_at.astimezone(UTC)
    ingestion_run_id = _build_ingestion_run_id(
        source_id=registry_entry.source_id,
        input_path=input_file,
        imported_at=imported_at_utc,
    )
    existing_document_ids = {document.document_id for document in repository.load_source_documents()}
    document_ids: list[str] = []
    documents: list[SourceDocument] = []
    stored_count = 0
    skipped_duplicate_count = 0
    fetched_count = 0

    for line_number, line in enumerate(input_file.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        fetched_count += 1
        try:
            payload = json.loads(line)
            document = _document_from_payload(
                payload,
                source=registry_entry,
                imported_at=imported_at_utc,
                ingestion_run_id=ingestion_run_id,
            )
        except Exception as exc:
            raise ValueError(f"{input_file}:{line_number} cannot be imported: {exc}") from exc
        document_ids.append(document.document_id)
        documents.append(document)

    repository.save_source_registry_entry(registry_entry)
    for document in documents:
        if document.document_id in existing_document_ids:
            skipped_duplicate_count += 1
            continue
        repository.save_source_document(document)
        existing_document_ids.add(document.document_id)
        stored_count += 1

    ingestion_run = SourceIngestionRun(
        ingestion_run_id=ingestion_run_id,
        created_at=imported_at_utc,
        source_name=registry_entry.source_name,
        source_type=registry_entry.source_type,
        status="success",
        document_ids=document_ids,
        fetched_count=fetched_count,
        stored_count=stored_count,
        error_message=None,
        decision_basis=f"fixture_import:{registry_entry.source_id}",
    )
    repository.save_source_ingestion_run(ingestion_run)
    return SourceDocumentImportResult(
        storage_dir=Path(storage_dir),
        input_path=input_file,
        source_id=registry_entry.source_id,
        ingestion_run_id=ingestion_run_id,
        document_ids=document_ids,
        fetched_count=fetched_count,
        stored_count=stored_count,
        skipped_duplicate_count=skipped_duplicate_count,
    )


def _document_from_payload(
    payload: dict,
    *,
    source: SourceRegistryEntry,
    imported_at: datetime,
    ingestion_run_id: str,
) -> SourceDocument:
    raw_text = _raw_text(payload)
    normalized_text = _normalize_text(raw_text)
    published_at = _optional_datetime(payload.get("published_at"))
    available_at = _optional_datetime(payload.get("available_at"))
    fetched_at = _optional_datetime(payload.get("fetched_at")) or imported_at
    processed_at = _optional_datetime(payload.get("processed_at")) or imported_at
    stable_source_id = (
        payload.get("stable_source_id")
        or payload.get("external_id")
        or f"{source.source_id}:{_hash_text(raw_text)[:16]}"
    )
    document_id = payload.get("document_id") or _build_document_id(
        source_id=source.source_id,
        stable_source_id=stable_source_id,
        source_url=payload.get("source_url"),
        published_at=published_at,
        raw_text_hash=payload.get("raw_text_hash") or _hash_text(raw_text),
    )
    enriched = {
        **payload,
        "document_id": document_id,
        "source_id": source.source_id,
        "source_name": source.source_name,
        "source_type": source.source_type,
        "stable_source_id": stable_source_id,
        "published_at": published_at.isoformat() if published_at else None,
        "available_at": available_at.isoformat() if available_at else None,
        "fetched_at": fetched_at.isoformat(),
        "processed_at": processed_at.isoformat(),
        "language": payload.get("language", "unknown"),
        "headline": payload.get("headline", ""),
        "summary": payload.get("summary", ""),
        "raw_text_hash": payload.get("raw_text_hash") or _hash_text(raw_text),
        "normalized_text_hash": payload.get("normalized_text_hash") or _hash_text(normalized_text),
        "body_excerpt": payload.get("body_excerpt") or raw_text[:500],
        "entities": _string_list(payload.get("entities", [])),
        "symbols": _string_list(payload.get("symbols", [])),
        "topics": _string_list(payload.get("topics", [])),
        "source_reliability_score": source.reliability_base_score,
        "duplicate_group_id": payload.get("duplicate_group_id"),
        "license_note": source.license_notes,
        "ingestion_run_id": ingestion_run_id,
    }
    return SourceDocument.from_dict(enriched)


def _raw_text(payload: dict) -> str:
    for key in ("raw_text", "body", "body_excerpt", "summary", "headline"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise ValueError("source document row must include raw_text, body, body_excerpt, summary, or headline")


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _hash_text(value: str) -> str:
    return sha1(value.encode("utf-8")).hexdigest()


def _optional_datetime(value) -> datetime | None:
    if value in (None, ""):
        return None
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("source document timestamps must be timezone-aware")
    return parsed.astimezone(UTC)


def _string_list(value) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("entities, symbols, and topics must be lists")
    return [str(item) for item in value]


def _build_ingestion_run_id(*, source_id: str, input_path: Path, imported_at: datetime) -> str:
    digest = sha1(
        json.dumps(
            {
                "source_id": source_id,
                "input_path": str(input_path.resolve()),
                "imported_at": imported_at.isoformat(),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"source-ingestion-run:{digest}"


def _build_document_id(
    *,
    source_id: str,
    stable_source_id: str | None,
    source_url: str | None,
    published_at: datetime | None,
    raw_text_hash: str,
) -> str:
    digest = sha1(
        json.dumps(
            {
                "source_id": source_id,
                "stable_source_id": stable_source_id,
                "source_url": source_url,
                "published_at": published_at.isoformat() if published_at else None,
                "raw_text_hash": raw_text_hash,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"source-document:{digest}"
