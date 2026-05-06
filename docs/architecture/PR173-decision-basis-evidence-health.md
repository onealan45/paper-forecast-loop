# PR173: Strategy Decision Basis Evidence Health Gate

## Context

Strategy decisions can include research evidence ids inside `decision_basis`.
Current production decisions use fields such as:

- `backtest_result=<backtest-result:id>`
- `walk_forward=<walk-forward:id>`
- `event_edge=<event-edge:id>`

These links are used by downstream digest and UX evidence resolution. Before
this PR, `health-check` validated structured id lists on strategy decisions but
did not validate these text-based research evidence links.

## Decision

`health-check` now parses the three explicit research evidence fields in
`StrategyDecision.decision_basis`:

- `backtest_result`
- `walk_forward`
- `event_edge`

If one of those fields contains an artifact id that is absent from storage,
`health-check` creates a blocking, repair-required finding:

- `decision_basis_missing_backtest_result`
- `decision_basis_missing_walk_forward`
- `decision_basis_missing_event_edge`

The placeholders `missing`, `none`, and `null` are accepted because they are
normal fail-closed research gate states, not broken links.

## Boundaries

- This does not change decision generation or research gate behavior.
- This does not parse arbitrary prose in `decision_basis`; it only checks the
  explicit key/value evidence fields produced by the current research gate.
- This does not change dashboard or strategy digest fallback behavior.

## Verification

Red/green tests:

```powershell
python -m pytest tests\test_m1_strategy.py::test_health_check_detects_strategy_decision_basis_missing_research_evidence tests\test_m1_strategy.py::test_health_check_ignores_strategy_decision_basis_missing_placeholders -q
```

Focused and full gates:

```powershell
python -m pytest tests\test_m1_strategy.py tests\test_research_gates.py tests\test_strategy_digest_evidence.py -q
python -m pytest tests\test_backtest.py tests\test_walk_forward.py tests\test_m7_evidence_artifacts.py -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```
