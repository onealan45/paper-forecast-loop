# PR108 Retest Evidence Card Ownership Review

## Reviewer

- Reviewer subagent: Mencius
- Review date: 2026-05-02
- Result: APPROVED

## Scope

PR108 fixes a retest evidence-chain bug discovered after PR107 runtime smoke.
The active replacement retest card `strategy-card:98d8cf7e57414c4f` could enter
the retest chain, but the planner selected older split-aligned backtest and
walk-forward artifacts from an earlier revision card because only symbol and
split windows matched.

The intended fix is narrow:

- fallback split-aligned evidence is eligible only when it was created at or
  after the current pending retest trial started;
- linked evidence on a PASSED retest trial is valid only when it was created at
  or after that trial started;
- stale PASSED trials that link pre-trial evidence are ignored by the planner.

## Reviewer Findings

No blocking findings.

Mencius confirmed that:

- PASSED-trial linked evidence and fallback split-aligned evidence are both
  constrained to the corresponding retest trial start time;
- the change blocks stale pre-trial backtest / walk-forward evidence from
  closing a newer retest chain;
- no runtime, secret, `.codex`, `paper_storage`, `reports`, `output`, or `.env`
  files are included.

## Verification Evidence

Controller verification before final review:

- New targeted tests first failed before the fix:
  - `test_revision_retest_task_plan_does_not_reuse_preexisting_split_evidence_for_new_card`
  - `test_revision_retest_task_plan_rejects_passed_trial_with_pretrial_evidence`
- After the fix, targeted tests passed.
- `python -m pytest .\tests\test_research_autopilot.py -q` -> 74 passed.
- Active storage smoke:
  `python .\run_forecast_loop.py revision-retest-plan --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD --revision-card-id strategy-card:98d8cf7e57414c4f --symbol BTC-USD`
  exited 0 and returned `passed_trial_id=null`, `backtest_result_id=null`,
  `walk_forward_validation_id=null`, `next_task_id=run_backtest`.
- `python -m pytest -q` -> 476 passed.
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` ->
  passed.
- `python .\run_forecast_loop.py --help` -> passed.
- `git diff --check` -> passed with CRLF warnings only.
- `python .\run_forecast_loop.py health-check --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD --symbol BTC-USD`
  -> healthy, `repair_required=false`.

Reviewer spot verification:

- PR108 targeted tests -> 2 passed.
- `git diff --check` -> CRLF warnings only.

## Residual Risk

The ownership guard is timestamp-based because this PR does not change artifact
schemas. It prevents the observed pre-trial stale evidence reuse bug, but it
cannot distinguish two concurrent same-window retest chains that both create
evidence after the trial start. A future schema-level improvement should link
backtest and walk-forward artifacts to the strategy card or retest trial
directly.
