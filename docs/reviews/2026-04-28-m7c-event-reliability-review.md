# M7C Event Reliability Review

## Summary

Review target: `codex/m7c-event-reliability`

Milestone: PR2 / M7C Event Reliability

Reviewer: independent Codex reviewer subagent `Schrodinger`

Result: `APPROVED`

## Reviewed Scope

M7C adds:

- `forecast_loop.event_reliability.build_event_reliability`
- `build-events` CLI
- source-document to canonical-event grouping
- deterministic reliability checks
- source reliability threshold blocking
- point-in-time filtering
- event snapshot versioning by build `created_at`
- tests and architecture documentation

The review explicitly checked that this PR does not add live fetching, secret
handling, broker paths, real orders, or decision integration.

## Review Findings And Resolution

Initial review found three blockers:

- `[P1] Future-fetched documents can enter a past build`
  - Fix: source documents are included only when `available_at`, `fetched_at`,
    and `processed_at` are all `<= created_at`.
  - Regression: `test_build_events_excludes_documents_fetched_after_created_at`.

- `[P2] Incremental duplicate groups leave canonical events stale`
  - Fix: rerunning the same `created_at` replaces the matching event/check row.
  - Regression: `test_build_events_refreshes_existing_duplicate_group_event`.

- `[P2] build-events is not idempotent with default CLI arguments`
  - Fix: `build-events --created-at` is required and no longer defaults to
    wall-clock `now`.
  - Regression: `test_build_events_cli_requires_created_at`.

Second-pass review found one cross-time blocker:

- `[P1] Later build-events runs can mutate the event snapshot referenced by older checks`
  - Fix: `CanonicalEvent.created_at` was added, and `event_id` now includes the
    build `created_at`, so different build times create different immutable
    event snapshots.
  - Regression: `test_build_events_versions_canonical_events_across_created_at`.

Third-pass review result:

> APPROVED

The reviewer confirmed:

- different `created_at` values produce different `canonical-event:*` snapshots;
- old `EventReliabilityCheck.event_id` values still point to old snapshots;
- same-`created_at` reruns remain idempotent;
- future-fetched documents are excluded;
- weak or incomplete source evidence remains blocked;
- no new blocking finding was found.

## Reviewer Commands

The reviewer reported running:

```powershell
python -m pytest tests\test_event_reliability.py -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python -m pytest -q
git diff --check
python .\run_forecast_loop.py --help
python .\run_forecast_loop.py build-events --help
```

Reported results:

- `tests\test_event_reliability.py`: `8 passed`
- full pytest: `236 passed`
- compileall: passed
- diff check: passed with LF/CRLF warnings only
- CLI help: passed
- `build-events --help`: passed and shows `--created-at` required
- M7C smoke import -> build-events: passed; event has `created_at`, check links
  the same `event_id`, and `sample_news` is blocked by
  `source_reliability_below_threshold`

## Automation / Merge Gate

This review does not approve any live trading or real execution path.

M7C may proceed to PR/merge only if the local and GitHub machine gates pass:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

M7C-specific smoke must also pass:

```powershell
python .\run_forecast_loop.py import-source-documents --storage-dir <temp-dir> --input .\fixtures\source_documents\sample_news.jsonl --source sample_news --imported-at 2026-04-28T10:05:00+00:00
python .\run_forecast_loop.py build-events --storage-dir <temp-dir> --symbol BTC-USD --created-at 2026-04-28T10:05:00+00:00
```
