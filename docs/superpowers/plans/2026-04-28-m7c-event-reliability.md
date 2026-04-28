# M7C Event Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first M7C event reliability engine that converts imported source documents into deduplicated canonical events plus auditable reliability checks.

**Architecture:** Add a focused `event_reliability.py` module that reads existing M7B source documents from `JsonFileRepository`, normalizes them into `CanonicalEvent` records, groups duplicates deterministically, and writes matching `EventReliabilityCheck` records. Expose the engine through a `build-events` CLI command and document the exact M7C boundary.

**Tech Stack:** Python dataclasses, existing JSONL repository, existing M7A models, pytest, `run_forecast_loop.py` CLI.

---

### Task 1: Failing Tests For Event Builder

**Files:**
- Create: `tests/test_event_reliability.py`
- Modify: none

- [ ] **Step 1: Write failing tests**

Create tests for:

```python
def test_build_events_deduplicates_documents_and_writes_reliability_checks(tmp_path):
    # Two source documents with the same duplicate_group_id and symbol become one CanonicalEvent.
    # The event links both document ids, has cross_source_count == 2, duplicate_count == 1,
    # and passes when the average source reliability clears the threshold.
```

```python
def test_build_events_blocks_low_reliability_source(tmp_path):
    # A low-reliability source document still becomes a canonical event, but the matching
    # EventReliabilityCheck has passed=False and blocked_reason == "source_reliability_below_threshold".
```

```python
def test_build_events_cli_outputs_counts_and_is_idempotent(tmp_path, capsys):
    # Running the CLI twice with the same created_at does not duplicate event/check artifacts.
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
python -m pytest tests\test_event_reliability.py -q
```

Expected: fail because `forecast_loop.event_reliability` or CLI `build-events` does not exist.

### Task 2: Event Reliability Engine

**Files:**
- Create: `src/forecast_loop/event_reliability.py`
- Modify: none

- [ ] **Step 1: Implement `build_event_reliability`**

Implement:

```python
def build_event_reliability(
    *,
    storage_dir: Path | str,
    created_at: datetime,
    symbol: str | None = None,
    min_reliability_score: float = 70.0,
) -> EventReliabilityBuildResult:
```

Rules:
- Reject naive `created_at`.
- Load `source_documents.jsonl`.
- Ignore documents whose `available_at` is missing or later than `created_at`.
- If `symbol` is provided, keep only documents whose `symbols` include it.
- Create one event per `(symbol, event_family, event_type, duplicate_group_id-or-hash)` group.
- `event_family` is the first topic, or `unknown`.
- `event_type` is an uppercase normalized form of the first topic, or `SOURCE_DOCUMENT`.
- `primary_document_id` is the highest-reliability document, then earliest `available_at`, then document id.
- `published_at` is the earliest source publication time.
- `available_at` and `fetched_at` are the latest included source times, so the canonical event is point-in-time safe.
- `cross_source_count` is the count of unique source identity values.
- `credibility_score` is the average source reliability plus capped cross-source/official bonuses.
- Reliability passes only if required timestamps, stable source identity, text hashes, and min reliability are present.

- [ ] **Step 2: Verify GREEN**

Run:

```powershell
python -m pytest tests\test_event_reliability.py -q
```

Expected: tests pass.

### Task 3: CLI And Documentation

**Files:**
- Modify: `src/forecast_loop/cli.py`
- Modify: `README.md`
- Create: `docs/architecture/M7C-event-reliability.md`
- Create: `docs/reviews/2026-04-28-m7c-event-reliability-review.md` after independent reviewer approval

- [ ] **Step 1: Add CLI**

Add command:

```powershell
python .\run_forecast_loop.py build-events --storage-dir .\paper_storage\m7-fixture --symbol BTC-USD --created-at 2026-04-28T10:05:00+00:00
```

It must print JSON with `event_count`, `reliability_check_count`, `event_ids`, and `check_ids`.

- [ ] **Step 2: Update docs**

Document:
- M7C implemented scope.
- M7C deferred scope: market reaction, historical edge, decision integration.
- `build-events` CLI smoke command.
- Event reliability artifacts remain research inputs until later gates pass.

- [ ] **Step 3: Final verification**

Run:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Also run the M7C smoke:

```powershell
python .\run_forecast_loop.py import-source-documents --storage-dir <temp-dir> --input .\fixtures\source_documents\sample_news.jsonl --source sample_news --imported-at 2026-04-28T10:05:00+00:00
python .\run_forecast_loop.py build-events --storage-dir <temp-dir> --symbol BTC-USD --created-at 2026-04-28T10:05:00+00:00
```

Expected: all commands pass; sample_news produces an event and a blocked reliability check because the fixture reliability score is below the default threshold.
