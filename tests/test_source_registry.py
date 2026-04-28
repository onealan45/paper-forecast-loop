from forecast_loop.models import SourceRegistryEntry
from forecast_loop.sqlite_repository import SQLiteRepository, migrate_jsonl_to_sqlite
from forecast_loop.storage import JsonFileRepository


def _registry_entry() -> SourceRegistryEntry:
    return SourceRegistryEntry(
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


def test_source_registry_entry_round_trips_json_repository(tmp_path):
    repository = JsonFileRepository(tmp_path)
    entry = _registry_entry()

    repository.save_source_registry_entry(entry)

    assert repository.load_source_registry_entries() == [entry]


def test_source_registry_entry_migrates_to_sqlite(tmp_path):
    repository = JsonFileRepository(tmp_path)
    entry = _registry_entry()
    repository.save_source_registry_entry(entry)

    migrate_jsonl_to_sqlite(storage_dir=tmp_path)

    sqlite_repository = SQLiteRepository(tmp_path)
    assert sqlite_repository.load_source_registry_entries() == [entry]
