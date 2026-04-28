# M7B Source Registry And Source Document Import

## Summary

M7B turns the M7A source document artifact into an importable, registry-backed
research input layer. This stage is intentionally fixture-only: it does not add
live news crawling, paid data dependencies, browser scraping, secrets, or
external API calls.

The goal is to make future event/news/macro/on-chain evidence auditable before
M7C-M7F start scoring reliability, market reaction, historical edge, and
decision integration.

## Implemented Scope

M7B adds:

- `SourceRegistryEntry` model.
- `source_registry.jsonl` JSONL artifact.
- SQLite parity for the source registry artifact.
- Built-in `sample_news` fixture source registry entry.
- Fixture JSONL source document import.
- `import-source-documents` CLI command.
- `source-registry` CLI command.
- Health-check linkage for `SourceDocument.source_id` references when the field
  is present.

## Source Registry Semantics

Each registry entry records:

- `source_id`
- `source_name`
- `source_type`
- `provider`
- `license_notes`
- `rate_limit_policy`
- `update_lag_seconds`
- `timestamp_policy`
- `point_in_time_support`
- `reliability_base_score`
- `lookahead_risk`
- `allowed_for_decision`
- `allowed_for_research_only`
- `requires_secret`
- `secret_env_vars`
- `fixture_path`

`secret_env_vars` may contain environment variable names only. Secret values or
assignments such as `API_KEY=value` are invalid and are rejected by artifact
parsing / health-check.

## CLI

Import fixture source documents:

```powershell
python .\run_forecast_loop.py import-source-documents --storage-dir .\paper_storage\m7-fixture --input .\fixtures\source_documents\sample_news.jsonl --source sample_news --imported-at 2026-04-28T10:05:00+00:00
```

List registered sources:

```powershell
python .\run_forecast_loop.py source-registry --storage-dir .\paper_storage\m7-fixture --format json
```

## Import Contract

Each fixture JSONL row may provide:

- `document_id`
- `stable_source_id`
- `source_url`
- `published_at`
- `available_at`
- `fetched_at`
- `processed_at`
- `headline`
- `summary`
- `raw_text` or `body`
- `language`
- `entities`
- `symbols`
- `topics`
- `source_reliability_score`
- `duplicate_group_id`

If text hashes are missing, import computes deterministic SHA-1 hashes from the
raw and normalized text. If `fetched_at` or `processed_at` is missing, import
uses the CLI `--imported-at` timestamp.

## Decision Boundary

M7B does not make imported documents decision-eligible by itself. Imported
documents are research inputs until later gates pass:

- M7C event reliability
- M7D market reaction / already-priced
- M7E historical edge
- M7F decision integration

The built-in `sample_news` source is explicitly `allowed_for_research_only=true`
and `allowed_for_decision=false`.

## Acceptance

M7B is complete when:

- registry entries round-trip through JSONL storage;
- registry entries migrate to SQLite;
- fixture source documents import through CLI;
- import writes `source_registry.jsonl`, `source_documents.jsonl`, and
  `source_ingestion_runs.jsonl`;
- unknown source IDs fail with argparse-style CLI error;
- health-check flags source documents that reference missing registry entries;
- no live network, real broker, real order, or secret handling path is added.
