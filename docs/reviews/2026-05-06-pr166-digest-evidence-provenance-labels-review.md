# PR166 Review: Digest Evidence Provenance Labels

## Reviewer

- Subagent: Laplace (`019dfae0-d189-7bd3-b287-6794b687ca7c`)
- Role: reviewer
- Scope: code review only, no file edits
- Final verdict: APPROVED

## Review Focus

The review checked that strategy digest metrics now distinguish direct evidence
from background fallback, and that decision-blocker research artifacts cannot
leak into active strategy metrics.

## Initial Reviewer Finding

P1 blocker:

- `src/forecast_loop/strategy_research_digest.py`
- `src/forecast_loop/strategy_digest_evidence.py`

Decision-blocker `walk-forward:*` could still leak into active strategy metrics.
The read-side resolver did not pass `id_field="validation_id"` into the
walk-forward fallback selector, so `decision_research_artifact_ids` was not
applied. The digest builder also did not exclude decision-blocker walk-forward
IDs when selecting fallback context.

## Fix Summary

- Backtest fallback now excludes IDs listed in
  `decision_research_artifact_ids`.
- Walk-forward fallback now passes `id_field="validation_id"` so excluded
  decision-blocker IDs are actually filtered.
- Digest generation applies the same exclusions before building research
  summaries.
- UI labels each metric source as either direct linked evidence or background
  fallback context.

## Reviewer Verification

Reviewer approved after the P1 fix.

Controller verification after fix:

- `python -m pytest tests\test_strategy_digest_evidence.py::test_resolve_strategy_digest_evidence_fallback_excludes_decision_blocker_ids tests\test_strategy_research_digest.py::test_strategy_research_digest_does_not_use_decision_blocker_backtest_or_walk_forward_as_strategy_metric -q` -> `2 passed`
- `python -m pytest tests\test_strategy_research_digest.py tests\test_strategy_digest_evidence.py tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q` -> `31 passed`
- `python -m pytest -q` -> `575 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> exit 0, LF/CRLF warnings only

## Conclusion

PR166 can proceed to PR packaging.
