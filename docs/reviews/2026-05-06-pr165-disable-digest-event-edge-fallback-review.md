# PR165 Review: Disable Digest Event-Edge Fallback

## Reviewer

- Subagent: Volta (`019dfaca-cbd8-7f81-ac8c-7eeb1e1f6088`)
- Role: reviewer
- Scope: code review only, no file edits
- Final verdict: APPROVED

## Review Focus

The review checked that event-edge active strategy metrics are now explicit-only,
while explicit digest IDs and active chain IDs continue to resolve.

## Final Reviewer Findings

No blocking findings.

Reviewer confirmed:

- event-edge active strategy metrics no longer fall back to unlinked same-symbol
  event-edge artifacts;
- explicit digest event-edge IDs still resolve;
- active chain `event_edge_evaluation_id` and `event_edge_evaluation_ids` paths
  still resolve;
- backtest and walk-forward fallback remain intact;
- legacy digest default fields remain compatible;
- no secrets, runtime artifacts, real order, or real capital paths were added.

## Reviewer Verification

- `git status --short --branch`
- `git merge-base HEAD main`
- `git diff main -- src/forecast_loop/strategy_research_digest.py src/forecast_loop/strategy_digest_evidence.py tests/test_strategy_research_digest.py tests/test_strategy_digest_evidence.py`
- `git diff --check -- src/forecast_loop/strategy_research_digest.py src/forecast_loop/strategy_digest_evidence.py tests/test_strategy_research_digest.py tests/test_strategy_digest_evidence.py docs/architecture/PR165-disable-digest-event-edge-fallback.md`
- `rg -n "submit_order|place_order|real_order|real capital|real-capital|broker|exchange|api[_-]?key|secret|private[_-]?key|LIVE|live order|runtime" ...`
- `python -m pytest tests\test_strategy_research_digest.py tests\test_strategy_digest_evidence.py tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q` -> `30 passed`
- `python -m pytest tests\test_strategy_research_digest.py::test_strategy_research_digest_does_not_fallback_to_unlinked_event_edge tests\test_strategy_digest_evidence.py::test_resolve_strategy_digest_evidence_falls_back_to_latest_same_symbol_as_of tests\test_strategy_digest_evidence.py::test_resolve_strategy_digest_evidence_prefers_digest_evidence_ids tests\test_strategy_research_digest.py::test_strategy_research_digest_prefers_active_retest_evidence_over_newer_symbol_artifacts tests\test_strategy_research_digest.py::test_strategy_research_digest_does_not_fallback_when_active_retest_evidence_ids_are_unresolved -q` -> `5 passed`
- `python -m pytest tests\test_strategy_digest_evidence.py -q` -> `6 passed`
- `python -m pytest tests\test_strategy_research_digest.py -q` -> `22 passed`
- `python -m pytest -q` -> `574 passed`

## Local Gate Evidence

- `python -m pytest -q` -> `574 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> exit 0, LF/CRLF warnings only

## Conclusion

PR165 can proceed to PR packaging.
