# PR122 Refresh Digest After Retest Autopilot Review

## Scope

- Branch: `codex/pr122-refresh-digest-after-retest-autopilot`
- Files reviewed:
  - `src/forecast_loop/autopilot.py`
  - `tests/test_research_autopilot.py`

## Reviewer

- Subagent: `019de5d4-6c11-7c31-9648-2029bbea8237`
- Role: reviewer
- Model target: best available / maximum reasoning

## Findings

- No blocking findings.

## Verdict

APPROVED

## Reviewer Notes

- `RevisionRetestAutopilotRunResult.to_dict()` adding `strategy_research_digest` is an additive CLI JSON change.
- The helper test locks that digest refresh happens after the new run is saved by asserting `autopilot_run_id`, `strategy_card_id`, and `paper_shadow_outcome_id` all match the completed replacement chain.
- Reviewer noted the CLI payload did not explicitly assert the new digest field at review time; this archive includes the follow-up test coverage added after review.

## Verification

- `python -m pytest tests/test_research_autopilot.py::test_replacement_retest_autopilot_helper_refreshes_digest_after_run_is_saved -q` -> passed.
- `python -m pytest tests/test_research_autopilot.py tests/test_strategy_research_digest.py -q` -> passed.
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed.
- `python -m pytest -q` -> passed.
- `python .\run_forecast_loop.py --help` -> passed.
- `git diff --check` -> passed with only CRLF warnings.

## Residual Risk

- Runtime artifacts can still contain older digest rows; consumers should read the latest row. The active storage was refreshed after this fix so the latest digest now points at the latest completed retest chain.
