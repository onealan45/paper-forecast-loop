# PR164 Review: Digest Event-Edge Fallback Separation

## Reviewer

- Subagent: Euclid (`019dfac1-0d5a-7d80-b54f-c05105fc43c6`)
- Role: reviewer
- Scope: code review only, no file edits
- Final verdict: APPROVED

## Review Focus

The review checked that event-edge fallback no longer lets
decision-blocker event-edge artifacts appear as active strategy metrics, while
keeping the artifacts visible under `決策阻擋研究證據`.

## Final Reviewer Findings

No blocking findings.

Reviewer confirmed:

- digest generation excludes `decision_research_artifact_ids` from event-edge
  fallback;
- dashboard/operator-console read-side evidence resolution also excludes those
  IDs from fallback;
- explicit active event-edge IDs still win before fallback;
- legacy digest rows remain compatible through the default empty field;
- no real order, real capital, secrets, or runtime paths were introduced.

## Reviewer Verification

- `git status --short --branch`
- `git diff --name-status main -- ...`
- `git diff main -- ...`
- `Get-Content docs\architecture\PR164-digest-event-edge-fallback-separation.md`
- `rg -n "real order|real capital|broker|exchange|secret|api_key|token|password|private_key|live" ...` -> no matches
- `git diff --check -- ...` -> exit 0
- `python -m pytest tests\test_strategy_research_digest.py tests\test_strategy_digest_evidence.py tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q` -> `29 passed`
- `python -m pytest tests\test_strategy_research_digest.py::test_strategy_research_digest_does_not_use_decision_blocker_event_edge_as_strategy_metric tests\test_strategy_digest_evidence.py::test_resolve_strategy_digest_evidence_event_edge_fallback_excludes_decision_blocker_ids tests\test_strategy_digest_evidence.py::test_resolve_strategy_digest_evidence_prefers_digest_evidence_ids -q` -> `3 passed`

## Local Gate Evidence

- `python -m pytest -q` -> `573 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> exit 0, LF/CRLF warnings only

## Conclusion

PR164 can proceed to PR packaging.
