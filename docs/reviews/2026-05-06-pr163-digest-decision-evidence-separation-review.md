# PR163 Review: Digest Decision Evidence Separation

## Reviewer

- Subagent: Singer (`019dfaa8-7079-7461-938f-57e661fc26a9`)
- Role: reviewer
- Scope: code review only, no file edits
- Final verdict: APPROVED

## Findings

### P1: BUY decision evidence is mislabeled as blocker evidence

Initial review found that `decision_research_artifact_ids` extracted
`event-edge:*`, `backtest-result:*`, and `walk-forward:*` from every latest
decision, including tradeable `BUY` / `SELL` decisions with no blocker. This
would render passing validation evidence under `決策阻擋研究證據`.

Resolution:

- Added a tradeable `BUY` regression test.
- Updated extraction so passing tradeable directional evidence is not shown as
  blocker evidence.

### P1: Risk-stop decisions relabel passing validation as blocker evidence

Second review found the same issue for non-research risk stops such as
`STOP_NEW_ENTRIES` with `blocked_reason=risk_stop_new_entries` and `flags=none`.

Resolution:

- Added a risk-stop regression test.
- Tightened extraction so `decision_research_artifact_ids` is populated only
  when the linked decision has an actual `主要研究阻擋：...` summary.

## Final Reviewer Verification

- `python -m pytest tests\test_strategy_research_digest.py::test_strategy_research_digest_records_decision_blocker_research_artifact_ids tests\test_strategy_research_digest.py::test_strategy_research_digest_does_not_label_tradeable_buy_evidence_as_blocker_research tests\test_strategy_research_digest.py::test_strategy_research_digest_does_not_label_risk_stop_evidence_as_blocker_research -q` -> `3 passed`
- `python -m pytest tests\test_strategy_research_digest.py tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q` -> `22 passed`
- `git diff --check main -- ...` -> no whitespace errors
- Read-only reproducers confirmed:
  - `BUY_CASE BUY True None []`
  - `RISK_CASE STOP_NEW_ENTRIES False risk_stop_new_entries []`

## Local Gate Evidence

- `python -m pytest -q` -> `571 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> exit 0, LF/CRLF warnings only

## Conclusion

No blocking findings remain. PR163 can proceed to PR packaging.
