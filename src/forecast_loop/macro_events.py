from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path

from forecast_loop.models import MacroEvent
from forecast_loop.storage import JsonFileRepository


@dataclass(slots=True)
class MacroImportResult:
    storage_dir: Path
    input_path: Path
    imported_count: int
    skipped_duplicate_count: int
    total_rows: int

    def to_dict(self) -> dict:
        return {
            "storage_dir": str(self.storage_dir.resolve()),
            "input_path": str(self.input_path.resolve()),
            "imported_count": self.imported_count,
            "skipped_duplicate_count": self.skipped_duplicate_count,
            "total_rows": self.total_rows,
        }


def import_macro_events(
    *,
    storage_dir: Path | str,
    input_path: Path | str,
    source: str,
    imported_at: datetime,
) -> MacroImportResult:
    if imported_at.tzinfo is None or imported_at.utcoffset() is None:
        raise ValueError("imported_at must be timezone-aware")
    input_file = Path(input_path)
    if not input_file.exists():
        raise ValueError(f"macro event input does not exist: {input_file}")
    repository = JsonFileRepository(storage_dir)
    existing_ids = {event.event_id for event in repository.load_macro_events()}
    imported_count = 0
    skipped_duplicate_count = 0
    total_rows = 0

    for line_number, line in enumerate(input_file.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        total_rows += 1
        try:
            payload = json.loads(line)
            event = _event_from_payload(payload, source=source, imported_at=imported_at.astimezone(UTC))
        except Exception as exc:
            raise ValueError(f"{input_file}:{line_number} cannot be imported: {exc}") from exc
        if event.event_id in existing_ids:
            skipped_duplicate_count += 1
            continue
        repository.save_macro_event(event)
        existing_ids.add(event.event_id)
        imported_count += 1

    return MacroImportResult(
        storage_dir=Path(storage_dir),
        input_path=input_file,
        imported_count=imported_count,
        skipped_duplicate_count=skipped_duplicate_count,
        total_rows=total_rows,
    )


def macro_calendar(
    *,
    storage_dir: Path | str,
    start: datetime,
    end: datetime,
    event_type: str | None = None,
    region: str | None = None,
) -> dict:
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("macro-calendar start must be timezone-aware")
    if end.tzinfo is None or end.utcoffset() is None:
        raise ValueError("macro-calendar end must be timezone-aware")
    if start > end:
        raise ValueError("macro-calendar start must be <= end")
    normalized_type = event_type.upper() if event_type else None
    if normalized_type and normalized_type not in MacroEvent.ALLOWED_TYPES:
        raise ValueError(f"unsupported macro event type: {normalized_type}")
    normalized_region = region.upper() if region else None
    storage_path = Path(storage_dir)
    if not storage_path.exists() or not storage_path.is_dir():
        raise ValueError(f"storage directory does not exist: {storage_path}")

    events = []
    for event in JsonFileRepository(storage_path).load_macro_events():
        if not (start <= event.scheduled_at <= end):
            continue
        if normalized_type and event.event_type != normalized_type:
            continue
        if normalized_region and event.region != normalized_region:
            continue
        events.append(event)
    events.sort(key=lambda item: item.scheduled_at)
    return {
        "storage_dir": str(Path(storage_dir).resolve()),
        "start": start.astimezone(UTC).isoformat(),
        "end": end.astimezone(UTC).isoformat(),
        "event_type": normalized_type,
        "region": normalized_region,
        "event_count": len(events),
        "events": [event.to_dict() for event in events],
    }


def _event_from_payload(payload: dict, *, source: str, imported_at: datetime) -> MacroEvent:
    enriched = dict(payload)
    enriched.setdefault("source", source)
    enriched.setdefault("imported_at", imported_at.isoformat())
    scheduled_at = datetime.fromisoformat(enriched["scheduled_at"])
    if scheduled_at.tzinfo is None or scheduled_at.utcoffset() is None:
        raise ValueError("scheduled_at must be timezone-aware")
    enriched["scheduled_at"] = scheduled_at.astimezone(UTC).isoformat()
    event_type = str(enriched["event_type"]).upper()
    region = str(enriched["region"]).upper()
    enriched["event_id"] = enriched.get("event_id") or MacroEvent.build_id(
        event_type=event_type,
        region=region,
        scheduled_at=scheduled_at.astimezone(UTC),
        source=enriched["source"],
    )
    enriched["event_type"] = event_type
    enriched["region"] = region
    return MacroEvent.from_dict(enriched)
