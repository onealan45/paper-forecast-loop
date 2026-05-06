# PR179 Dashboard Latest Decision By Time Review

## Scope

Review target: `codex/pr179-dashboard-latest-decision-by-time`.

This review covers the dashboard strategy decision selector and its regression
tests. The intent is to prevent stale JSONL tail rows and cross-symbol decision
rows from replacing the active dashboard symbol's latest strategy decision.

## Reviewer History

- Hegel: `CHANGES_REQUESTED`
  - P1: dashboard strategy decision selection was not scoped to the dashboard
    symbol. A multi-symbol storage could show a BTC-USD decision while the
    latest forecast and dashboard state were SPY.
- Peirce: `CHANGES_REQUESTED`
  - P2: the first symbol-scope regression test was not sensitive to the old
    tail-selection bug because the SPY decision was also the JSONL tail.
- Boole: `APPROVED`
  - No blocker or important findings after the symbol-scope fix and
    regression-sensitive test update.

## Final Reviewer Evidence

Boole reviewed:

- `src/forecast_loop/dashboard.py`
  - Dashboard snapshot construction determines `dashboard_symbol`, filters
    strategy decisions to that symbol, then selects the max `created_at`.
- `tests/test_dashboard.py`
  - Same-symbol stale tail regression.
  - Multi-symbol regression where latest forecast is SPY while a newer BTC-USD
    decision is the JSONL tail.
- `docs/architecture/PR179-dashboard-latest-decision-by-time.md`
  - The architecture note matches the implementation: symbol-first, then max
    `created_at`.

Boole independently ran:

```powershell
python -m pytest tests\test_dashboard.py::test_dashboard_strategy_decision_uses_latest_created_at_not_file_tail tests\test_dashboard.py::test_dashboard_strategy_decision_is_scoped_to_dashboard_symbol -q
git diff --check eead221 -- src/forecast_loop/dashboard.py tests/test_dashboard.py
```

## Final Verdict

`APPROVED`.

No blocking findings remain.

## Residual Risks

- This PR only changes `latest_strategy_decision` selection. It does not make
  baseline, portfolio, risk, or digest latest-field selection symbol-scoped.
- This PR does not infer whether the selected decision has the same evidence
  chain as the latest forecast; it only prevents stale-tail and cross-symbol
  display mistakes.

