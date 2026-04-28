from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha1
import json
import re
from pathlib import Path

from forecast_loop.models import CanonicalEvent, EventReliabilityCheck, SourceDocument
from forecast_loop.storage import JsonFileRepository


@dataclass(slots=True)
class EventReliabilityBuildResult:
    storage_dir: Path
    created_at: datetime
    symbol: str | None
    event_ids: list[str]
    check_ids: list[str]
    event_count: int
    reliability_check_count: int

    def to_dict(self) -> dict:
        return {
            "storage_dir": str(self.storage_dir.resolve()),
            "created_at": self.created_at.isoformat(),
            "symbol": self.symbol,
            "event_count": self.event_count,
            "reliability_check_count": self.reliability_check_count,
            "event_ids": self.event_ids,
            "check_ids": self.check_ids,
        }


@dataclass(slots=True)
class _DocumentGroup:
    symbol: str
    event_family: str
    event_type: str
    dedupe_key: str
    documents: list[SourceDocument]


def build_event_reliability(
    *,
    storage_dir: Path | str,
    created_at: datetime,
    symbol: str | None = None,
    min_reliability_score: float = 70.0,
) -> EventReliabilityBuildResult:
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("created_at must be timezone-aware")
    created_at_utc = created_at.astimezone(UTC)
    repository = JsonFileRepository(storage_dir)
    documents = [
        document
        for document in repository.load_source_documents()
        if _document_is_available(document, created_at_utc)
    ]
    grouped_documents = _group_documents(documents, symbol=symbol)
    event_ids: list[str] = []
    check_ids: list[str] = []

    for group in grouped_documents:
        event, check = _build_event_and_check(
            group,
            created_at=created_at_utc,
            min_reliability_score=min_reliability_score,
        )
        _replace_unique(repository.canonical_events_path, event.to_dict(), identity_key="event_id")
        _replace_unique(repository.event_reliability_checks_path, check.to_dict(), identity_key="check_id")
        event_ids.append(event.event_id)
        check_ids.append(check.check_id)

    return EventReliabilityBuildResult(
        storage_dir=Path(storage_dir),
        created_at=created_at_utc,
        symbol=symbol,
        event_ids=event_ids,
        check_ids=check_ids,
        event_count=len(event_ids),
        reliability_check_count=len(check_ids),
    )


def _document_is_available(document: SourceDocument, created_at: datetime) -> bool:
    return (
        document.available_at is not None
        and document.available_at <= created_at
        and document.fetched_at <= created_at
        and document.processed_at <= created_at
    )


def _group_documents(documents: list[SourceDocument], *, symbol: str | None) -> list[_DocumentGroup]:
    groups: dict[tuple[str, str, str, str], list[SourceDocument]] = {}
    for document in documents:
        candidate_symbols = document.symbols or ["UNKNOWN"]
        for candidate_symbol in sorted(set(candidate_symbols)):
            if symbol is not None and candidate_symbol != symbol:
                continue
            family = _event_family(document)
            event_type = _event_type(family)
            dedupe_key = document.duplicate_group_id or _content_dedupe_key(document)
            groups.setdefault((candidate_symbol, family, event_type, dedupe_key), []).append(document)
    return [
        _DocumentGroup(
            symbol=key[0],
            event_family=key[1],
            event_type=key[2],
            dedupe_key=key[3],
            documents=groups[key],
        )
        for key in sorted(groups)
    ]


def _build_event_and_check(
    group: _DocumentGroup,
    *,
    created_at: datetime,
    min_reliability_score: float,
) -> tuple[CanonicalEvent, EventReliabilityCheck]:
    documents = sorted(group.documents, key=lambda document: document.document_id)
    primary = _primary_document(documents)
    source_ids = sorted({document.document_id for document in documents})
    cross_source_count = _cross_source_count(documents)
    duplicate_count = max(0, len(documents) - 1)
    official_source_flag = any(document.source_type == "official" for document in documents)
    reliability_score = _average(document.source_reliability_score for document in documents)
    has_stable_source = all(document.source_url or document.stable_source_id for document in documents)
    has_required_timestamps = all(document.published_at is not None and document.available_at is not None for document in documents)
    raw_hash_present = all(document.raw_text_hash and document.normalized_text_hash for document in documents)
    flags = _reliability_flags(
        reliability_score=reliability_score,
        min_reliability_score=min_reliability_score,
        has_stable_source=has_stable_source,
        has_required_timestamps=has_required_timestamps,
        raw_hash_present=raw_hash_present,
    )
    passed = not flags
    event_id = _build_event_id(
        symbol=group.symbol,
        event_family=group.event_family,
        event_type=group.event_type,
        dedupe_key=group.dedupe_key,
        created_at=created_at,
    )
    check_id = _build_check_id(event_id=event_id, created_at=created_at)
    event = CanonicalEvent(
        event_id=event_id,
        event_family=group.event_family,
        event_type=group.event_type,
        symbol=group.symbol,
        title=primary.headline or group.event_type,
        summary=primary.summary or primary.body_excerpt,
        event_time=_earliest_optional(document.published_at for document in documents),
        published_at=_earliest_optional(document.published_at for document in documents),
        available_at=_latest_optional(document.available_at for document in documents),
        fetched_at=_latest_required(document.fetched_at for document in documents),
        source_document_ids=source_ids,
        primary_document_id=primary.document_id,
        credibility_score=_credibility_score(
            reliability_score=reliability_score,
            cross_source_count=cross_source_count,
            official_source_flag=official_source_flag,
        ),
        cross_source_count=cross_source_count,
        official_source_flag=official_source_flag,
        duplicate_group_id=primary.duplicate_group_id,
        status="reliable" if passed else "blocked",
        created_at=created_at,
    )
    check = EventReliabilityCheck(
        check_id=check_id,
        event_id=event_id,
        created_at=created_at,
        symbol=group.symbol,
        source_type=_source_type(documents),
        source_reliability_score=reliability_score,
        official_source_flag=official_source_flag,
        cross_source_count=cross_source_count,
        duplicate_count=duplicate_count,
        has_stable_source=has_stable_source,
        has_required_timestamps=has_required_timestamps,
        raw_hash_present=raw_hash_present,
        passed=passed,
        blocked_reason=flags[0] if flags else None,
        flags=flags,
    )
    return event, check


def _primary_document(documents: list[SourceDocument]) -> SourceDocument:
    return sorted(
        documents,
        key=lambda document: (
            -document.source_reliability_score,
            document.available_at or datetime.max.replace(tzinfo=UTC),
            document.document_id,
        ),
    )[0]


def _event_family(document: SourceDocument) -> str:
    return _normalize_token(document.topics[0]) if document.topics else "unknown"


def _event_type(event_family: str) -> str:
    normalized = _normalize_token(event_family)
    return normalized.upper() if normalized != "unknown" else "SOURCE_DOCUMENT"


def _source_type(documents: list[SourceDocument]) -> str:
    source_types = sorted({document.source_type for document in documents})
    return source_types[0] if len(source_types) == 1 else "mixed"


def _cross_source_count(documents: list[SourceDocument]) -> int:
    identities = {
        document.source_id or document.source_name or document.stable_source_id or document.document_id
        for document in documents
    }
    return len(identities)


def _reliability_flags(
    *,
    reliability_score: float,
    min_reliability_score: float,
    has_stable_source: bool,
    has_required_timestamps: bool,
    raw_hash_present: bool,
) -> list[str]:
    flags: list[str] = []
    if reliability_score < min_reliability_score:
        flags.append("source_reliability_below_threshold")
    if not has_stable_source:
        flags.append("missing_stable_source")
    if not has_required_timestamps:
        flags.append("missing_required_timestamps")
    if not raw_hash_present:
        flags.append("missing_text_hash")
    return flags


def _credibility_score(
    *,
    reliability_score: float,
    cross_source_count: int,
    official_source_flag: bool,
) -> float:
    cross_source_bonus = min(10.0, max(0, cross_source_count - 1) * 5.0)
    official_bonus = 5.0 if official_source_flag else 0.0
    return min(100.0, reliability_score + cross_source_bonus + official_bonus)


def _average(values) -> float:
    numbers = list(values)
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)


def _earliest_optional(values) -> datetime | None:
    timestamps = [value for value in values if value is not None]
    return min(timestamps) if timestamps else None


def _latest_optional(values) -> datetime | None:
    timestamps = [value for value in values if value is not None]
    return max(timestamps) if timestamps else None


def _latest_required(values) -> datetime:
    return max(values)


def _content_dedupe_key(document: SourceDocument) -> str:
    normalized = " ".join(
        value
        for value in [
            _normalize_text(document.headline),
            _normalize_text(document.summary),
            _normalize_token(document.topics[0]) if document.topics else "",
        ]
        if value
    )
    return f"content:{sha1(normalized.encode('utf-8')).hexdigest()[:16]}"


def _build_event_id(
    *,
    symbol: str,
    event_family: str,
    event_type: str,
    dedupe_key: str,
    created_at: datetime,
) -> str:
    digest = sha1(
        json.dumps(
            {
                "symbol": symbol,
                "event_family": event_family,
                "event_type": event_type,
                "dedupe_key": dedupe_key,
                "created_at": created_at.isoformat(),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"canonical-event:{digest}"


def _build_check_id(*, event_id: str, created_at: datetime) -> str:
    digest = sha1(
        json.dumps(
            {
                "event_id": event_id,
                "created_at": created_at.isoformat(),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"event-reliability:{digest}"


def _normalize_token(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return normalized or "unknown"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _replace_unique(path: Path, payload: dict, *, identity_key: str) -> None:
    rows: list[dict] = []
    replaced = False
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            existing = json.loads(line)
            if existing.get(identity_key) == payload.get(identity_key):
                rows.append(payload)
                replaced = True
            else:
                rows.append(existing)
    if not replaced:
        rows.append(payload)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
