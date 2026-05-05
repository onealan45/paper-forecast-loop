# PR158 Operator Console Current Strategy Focus Review

## Scope

Reviewed the working-tree diff for branch
`codex/pr158-operator-console-current-retest-focus`.

Files in scope:

- `src/forecast_loop/operator_console.py`
- `tests/test_operator_console.py`
- `docs/architecture/PR158-operator-console-current-strategy-focus.md`

Runtime outputs, `paper_storage/`, `reports/`, `.codex/`, `.env`, and secrets
were not part of the review scope and must not be committed.

## Reviewers

- Final reviewer subagent `Dirac` initially returned `BLOCKED`.
- Final reviewer subagent `Bernoulli` returned `APPROVED` after the blocking
  issue was fixed.

## Blocking Finding Resolved

### P1 Current action still used stale autopilot action

The first review found that the current strategy slot had moved to the latest
digest-selected card, but the current next-action panel and overview preview
still used the stale autopilot `next_research_action`. This could still show
`REVISE_STRATEGY` while the latest digest was waiting for a replacement
paper-shadow outcome.

Resolution:

- Added a current-action helper that uses digest `next_research_action` and
  digest ID when the digest-selected strategy card owns the current strategy.
- Kept autopilot action as the fallback when the digest does not own the
  current strategy.
- Added regression coverage for the research page current-action slot and the
  overview preview.

## Final Result

`APPROVED`

No blocking findings remained. The operator console now lets the
digest-selected current strategy drive both the current next-action panel and
overview preview. Stale revision candidates are suppressed only from active
current-action surfaces and remain visible through lineage history.

## Verification

- `python -m pytest tests\test_operator_console.py -q` -> `46 passed`
- `python -m pytest -q` -> `563 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> passed, with LF/CRLF warnings only
- `python .\run_forecast_loop.py operator-console --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD --symbol BTC-USD --page research --output .\reports\operator-console-smoke\research.html` -> passed

Smoke result:

- Current strategy card: `strategy-card:21b5169756bc0feb`
- Current action source: `strategy-research-digest:afbeebe415697deb`
- Current action: `WAIT_FOR_PAPER_SHADOW_OUTCOME`
- Lineage replacement card: `strategy-card:21b5169756bc0feb`
- Replacement next task: `record_paper_shadow_outcome / blocked`
