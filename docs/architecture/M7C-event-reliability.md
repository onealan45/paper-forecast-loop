# M7C Event Reliability

## Summary

M7C 將 M7B 匯入的 `source_documents.jsonl` 轉成可追溯的
`canonical_events.jsonl` 與 `event_reliability_checks.jsonl`。這一階段的
重點是事件正規化、去重、symbol linking、以及 source reliability gate。

這不是 BUY/SELL 決策整合，也不是 market reaction / already-priced gate。M7C
只回答：

- 這些 source documents 是否代表同一個 canonical event？
- 事件連到哪些 source documents？
- 事件對應哪個 symbol？
- source reliability 是否足以讓後續研究使用？
- 若不通過，阻擋原因是什麼？

## Implemented Scope

M7C adds:

- `forecast_loop.event_reliability.build_event_reliability`
- `build-events` CLI
- deterministic canonical event ids
- deterministic event reliability check ids for a fixed `created_at`
- duplicate grouping by `duplicate_group_id` or normalized content hash
- symbol filtering
- source reliability threshold gate
- timestamp / stable source / text hash reliability flags
- idempotent writes through existing JSONL repository uniqueness

## Event Builder Rules

`build_event_reliability` reads existing source documents and includes only
documents whose `available_at`, `fetched_at`, and `processed_at` are all
`<= created_at`. This keeps the generated event set point-in-time safe for the
chosen build timestamp and prevents replay/backtest lookahead from documents
that were known to exist but not yet fetched or processed by the local system.

Grouping uses:

- symbol
- first topic as `event_family`
- normalized uppercase first topic as `event_type`
- `duplicate_group_id` when present
- otherwise a deterministic content dedupe hash from headline, summary, and topic

For each group, the builder creates one `CanonicalEvent` and one
`EventReliabilityCheck`.

`CanonicalEvent.event_id` is a snapshot id. It includes the build `created_at`
as part of the deterministic identity, so a later build that sees additional
source documents creates a new event snapshot instead of mutating the event
referenced by older reliability checks. Rerunning the same input with the same
`created_at` replaces the same snapshot row and remains idempotent.

The primary document is selected by:

- highest `source_reliability_score`
- earliest `available_at`
- document id tie-break

The canonical event uses:

- earliest source `published_at` as `event_time` / `published_at`
- latest included source `available_at`
- latest included source `fetched_at`
- all linked source document ids
- cross-source count from source identity
- credibility score from average reliability plus capped cross-source and official-source bonuses

## Reliability Gate

The reliability check passes only when all of these are true:

- average source reliability is at or above `--min-reliability-score`
- all source documents have required timestamps
- all source documents have a stable source identity
- all source documents have raw and normalized text hashes

Possible blocking flags currently include:

- `source_reliability_below_threshold`
- `missing_stable_source`
- `missing_required_timestamps`
- `missing_text_hash`

## CLI

Build events and reliability checks:

```powershell
python .\run_forecast_loop.py build-events --storage-dir .\paper_storage\m7-fixture --symbol BTC-USD --created-at 2026-04-28T10:05:00+00:00
```

`--created-at` is required. It is not defaulted to wall-clock `now`, because the
same operator command must be rerunnable without creating a new reliability
check id.

Fixture smoke from M7B import to M7C event build:

```powershell
python .\run_forecast_loop.py import-source-documents --storage-dir .\paper_storage\m7-fixture --input .\fixtures\source_documents\sample_news.jsonl --source sample_news --imported-at 2026-04-28T10:05:00+00:00
python .\run_forecast_loop.py build-events --storage-dir .\paper_storage\m7-fixture --symbol BTC-USD --created-at 2026-04-28T10:05:00+00:00
```

The built-in `sample_news` source has reliability `65.0`; with the default
threshold `70.0`, it should produce a canonical event plus a blocked reliability
check. That is intentional: the sample fixture is research input, not
decision-grade evidence.

## Deferred Scope

M7C intentionally does not implement:

- live source fetching
- paid data providers
- browser scraping
- market reaction / already-priced scoring
- historical edge evaluation
- feature snapshot generation from events
- decision integration
- strategy card or leaderboard updates
- live broker or real-money execution paths

Those remain later PRs under the master decision sequence.

## Acceptance

M7C is complete when:

- source documents can be grouped into canonical events;
- duplicate source documents produce one canonical event;
- reliability checks pass for sufficiently reliable evidence;
- weak source evidence is blocked with explicit flags;
- `build-events` is idempotent for fixed input and `created_at`;
- tests, compile checks, CLI help, diff check, and M7C fixture smoke pass;
- independent reviewer subagent approves and the review is archived.
