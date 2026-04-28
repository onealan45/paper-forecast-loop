# M7A Three Evidence Gates Foundation

## Summary

M7A starts the Alpha Factory event-evidence layer. This stage does not make
news, macro, fundamentals, or LLM summaries directly drive BUY/SELL. It creates
the artifact contracts and integrity checks needed before later PRs can build
source reliability, already-priced, historical-edge, and feature generation
engines.

The current execution boundary remains unchanged: no real orders, no real
capital movement, and no committed secrets. This is the current
research/simulation boundary, not a permanent statement about future automated
trading design.

The post-M7A execution contract is now
[`autonomous-alpha-factory-master-decision.md`](autonomous-alpha-factory-master-decision.md).
That decision makes PR0 Reviewability And Formatting Gate the next required
step before additional strategy intelligence, then prioritizes M7B-M7F source
registry, event reliability, market reaction, historical edge, and decision
integration work.

## Artifact Contracts

M7A adds append-only JSONL and SQLite-compatible artifacts:

- `source_documents.jsonl`: raw or normalized external information with source,
  timestamps, hashes, entities, symbols, topics, reliability score, and
  ingestion lineage.
- `source_ingestion_runs.jsonl`: ingestion run summaries and linked document
  ids.
- `canonical_events.jsonl`: deduplicated event candidates linked to source
  documents.
- `event_reliability_checks.jsonl`: source reliability gate outputs.
- `market_reaction_checks.jsonl`: already-priced / market reaction gate
  outputs.
- `event_edge_evaluations.jsonl`: historical edge gate outputs.
- `feature_snapshots.jsonl`: point-in-time feature values linked back to
  source documents and canonical events.

These artifacts are stored through the same repository pattern as previous M1
through M6 artifacts. JSONL remains the append-only audit/export surface, while
SQLite stores the same payloads through the generic `artifacts` table.

## Health Semantics

`health-check` now audits the new evidence artifacts for the minimum safety and
research-integrity constraints needed by later M7 work:

- malformed JSON rows;
- duplicate artifact ids;
- source documents missing `published_at`, `available_at`, stable source
  identity, or text hashes;
- invalid source timestamp order;
- canonical events referencing missing source documents;
- reliability and reaction checks referencing missing canonical events;
- feature snapshots referencing missing source documents or events;
- feature snapshots where `feature_timestamp` or `training_cutoff` is after
  `decision_timestamp`;
- feature snapshots marked `leakage_safe=false`;
- feature snapshots using source documents fetched after the decision time.

Any blocking finding keeps the artifact as research-only evidence and creates a
repair-required health state when repair requests are enabled.

## Deferred Work

This PR intentionally does not implement:

- external source fetching or source-watch commands;
- source reliability scoring logic;
- canonical event aggregation logic;
- market reaction / already-priced calculations;
- historical-edge calculations;
- integration into `decision.py` or `research_gates.py`;
- strategy skill generation or leaderboard updates.

Those are planned for the following M7 PRs. Until those engines exist, the new
artifacts are contract and audit surfaces only.

## Acceptance

M7A is complete when:

- all new artifacts round-trip through `JsonFileRepository`;
- migration to SQLite preserves the new artifacts;
- `db-health` recognizes the new artifact types;
- `health-check` flags missing timestamps, missing links, and feature
  lookahead;
- tests and compile checks pass.
