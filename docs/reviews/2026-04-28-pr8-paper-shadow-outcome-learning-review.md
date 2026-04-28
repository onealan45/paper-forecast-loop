# PR8 Paper-Shadow Outcome Learning Review

## Reviewer

- Reviewer: Zeno subagent
- Role: `docs/roles/reviewer.md`
- Scope: PR8 paper-shadow outcome model, service, CLI, JSONL/SQLite storage parity, health-check links, docs, and tests.
- Date: 2026-04-28

## Initial Findings

### P1: Blocked leaderboard artifacts can become promotion-ready

The initial implementation only blocked paper-shadow promotion when
`entry.rankable` was false. A malformed or manually imported leaderboard entry
with `rankable=true`, `promotion_stage=BLOCKED`, and populated
`blocked_reasons` could still classify as `PASS` and `PROMOTION_READY`.

### P2: Health-check misses mismatched existing outcome links

The initial health-check verified that linked paper-shadow outcome artifacts
existed, but did not verify that an outcome's evaluation, strategy card, and
trial ids matched the linked leaderboard entry and locked evaluation.

### P3: Bad CLI input creates a storage directory

`record-paper-shadow-outcome` constructed `JsonFileRepository` before checking
whether the storage path existed. A typo path could exit with an argparse error
but leave an empty runtime directory behind.

Initial recommendation: **NOT APPROVED**.

## Fix Summary

- Added `test_paper_shadow_malformed_blocked_entry_fails_closed`.
- Added `test_health_check_flags_paper_shadow_mismatched_existing_links`.
- Added `test_cli_record_paper_shadow_rejects_missing_storage_without_creating_it`.
- Updated `paper_shadow.py` to fail closed on:
  - non-rankable leaderboard entry;
  - `promotion_stage=BLOCKED`;
  - missing leaderboard alpha score;
  - leaderboard blocked reasons;
  - locked evaluation not passed;
  - locked evaluation not rankable;
  - missing locked-evaluation alpha score;
  - locked-evaluation blocked reasons.
- Updated health-check to validate paper-shadow outcome consistency against
  both the linked leaderboard entry and linked locked evaluation.
- Updated CLI to validate storage path existence before constructing
  `JsonFileRepository`.

## Re-Review Result

The reviewer confirmed prior P1/P2/P3 findings are closed and found no blocking
findings.

Final recommendation: **APPROVED**.

## Verification

- `python -m pytest tests\test_paper_shadow.py -q` -> passed
- `python -m pytest tests\test_paper_shadow.py tests\test_sqlite_repository.py tests\test_locked_evaluation.py tests\test_m1_strategy.py -q` -> `56 passed`
- `python -m pytest -q` -> `278 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> passed; LF/CRLF warnings only
- Bad storage CLI probe -> exit 2 and did not create the typo directory

## Scope Notes

- PR8 does not automatically mutate strategy cards.
- PR8 does not implement the full research autopilot loop.
- PR8 does not add live trading, real broker execution, secrets, or runtime
  artifacts.
