# PR107 Raw Quarantine Replacement Retest Review

## Reviewer

- Reviewer subagent: Franklin
- Review date: 2026-05-02
- Result: APPROVED

## Scope

PR107 fixes a replacement retest blocker found in active BTC-USD storage:

- lineage routing already treats raw paper-shadow `QUARANTINE` as a
  replacement-required outcome;
- `create_revision_retest_scaffold` and `revision-retest-plan` still only
  accepted `QUARANTINE_STRATEGY`;
- active replacement card `strategy-card:98d8cf7e57414c4f` was therefore
  rejected before it could enter the retest chain.

## Reviewer Findings

No blocking findings.

Franklin confirmed that:

- replacement retest source checks now accept exactly `QUARANTINE` and
  `QUARANTINE_STRATEGY`;
- the change does not broaden replacement retesting to `RETIRE`, `REVISE`, or
  promotion-ready outcomes;
- lineage ownership and source-outcome checks still run before the action gate;
- no runtime, secret, `.codex`, `paper_storage`, `reports`, `output`, or `.env`
  files are included.

## Verification Evidence

Controller verification before final review:

- New targeted tests first failed before the fix with
  `source paper shadow outcome does not require replacement`, then passed after
  the fix.
- `python -m pytest .\tests\test_research_autopilot.py -q` -> 72 passed.
- Active storage smoke:
  `python .\run_forecast_loop.py revision-retest-plan --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD --revision-card-id strategy-card:98d8cf7e57414c4f --symbol BTC-USD`
  exited 0 and returned `next_task_id=create_revision_retest_scaffold`.
- `python -m pytest -q` -> 474 passed.
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` ->
  passed.
- `python .\run_forecast_loop.py --help` -> passed.
- `git diff --check` -> passed with CRLF warnings only.
- `python .\run_forecast_loop.py health-check --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD --symbol BTC-USD`
  -> healthy, `repair_required=false`.

## Residual Risk

Residual risk is low. The new tests cover the raw `QUARANTINE` positive path
for both scaffold and read-only task plan. Non-quarantine rejection behavior is
preserved by the precise replacement action set and existing source/lineage
guards.
