from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from forecast_loop.models import SourceRegistryEntry
from forecast_loop.storage import JsonFileRepository


BUILTIN_SOURCE_REGISTRY: dict[str, SourceRegistryEntry] = {
    "sample_news": SourceRegistryEntry(
        source_id="sample_news",
        source_name="Sample News Fixture",
        source_type="news",
        provider="fixture",
        license_notes="Local fixture only.",
        rate_limit_policy="offline fixture; no network calls",
        update_lag_seconds=None,
        timestamp_policy={
            "event_time_field": "published_at",
            "published_at_required": True,
            "available_at_required": True,
            "fetched_at_required": True,
            "timezone": "UTC",
        },
        point_in_time_support="full",
        reliability_base_score=65.0,
        lookahead_risk="low",
        allowed_for_decision=False,
        allowed_for_research_only=True,
        requires_secret=False,
        secret_env_vars=[],
        fixture_path="fixtures/source_documents/sample_news.jsonl",
    )
}


@dataclass(slots=True)
class SourceRegistryPayload:
    storage_dir: Path
    sources: list[SourceRegistryEntry]

    def to_dict(self) -> dict:
        return {
            "storage_dir": str(self.storage_dir.resolve()),
            "source_count": len(self.sources),
            "sources": [source.to_dict() for source in self.sources],
        }


def resolve_source_registry_entry(
    *,
    repository: JsonFileRepository,
    source_id: str,
) -> SourceRegistryEntry:
    for entry in repository.load_source_registry_entries():
        if entry.source_id == source_id:
            return entry
    if source_id in BUILTIN_SOURCE_REGISTRY:
        return BUILTIN_SOURCE_REGISTRY[source_id]
    supported = ", ".join(sorted(BUILTIN_SOURCE_REGISTRY))
    raise ValueError(f"unknown source id: {source_id}; supported built-in sources: {supported}")


def ensure_source_registry_entry(
    *,
    repository: JsonFileRepository,
    source_id: str,
) -> SourceRegistryEntry:
    entry = resolve_source_registry_entry(repository=repository, source_id=source_id)
    repository.save_source_registry_entry(entry)
    return entry


def source_registry_payload(*, storage_dir: Path | str) -> SourceRegistryPayload:
    storage_path = Path(storage_dir)
    if not storage_path.exists() or not storage_path.is_dir():
        raise ValueError(f"storage directory does not exist: {storage_path}")
    repository = JsonFileRepository(storage_path)
    sources = sorted(repository.load_source_registry_entries(), key=lambda source: source.source_id)
    return SourceRegistryPayload(storage_dir=storage_path, sources=sources)
