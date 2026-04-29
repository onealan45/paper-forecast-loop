# PR31 Strategy Lineage Visibility Review

## Review Scope

- Branch: `codex/strategy-lineage-visibility`
- Topic: read-only strategy lineage / demotion visibility derived from existing
  strategy-card and paper-shadow outcome artifacts.
- Reviewer role: final reviewer subagent.

## Findings

- Initial reviewer finding: P1 root selection bug. When the latest research
  chain pointed at a DRAFT revision card, lineage summary used the revision as
  root and omitted parent strategy outcomes.
- Fix: `build_strategy_lineage_summary` now resolves `parent_card_id` back to
  the true parent root when the current card is a revision.
- Regression coverage: summary, dashboard snapshot, and operator console
  snapshot tests now cover latest-chain-is-revision behavior.

## Verification

Controller verification before review:

```powershell
python -m pytest tests\test_strategy_lineage.py -q
python -m pytest tests\test_strategy_lineage.py tests\test_dashboard.py tests\test_operator_console.py -k "strategy_lineage" -q
python -m pytest tests\test_strategy_lineage.py tests\test_dashboard.py tests\test_operator_console.py -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Observed results:

- summary tests: `1 passed`
- targeted lineage UX tests: `3 passed`
- dashboard/operator-console/lineage tests: `45 passed`
- full suite: `364 passed`
- compileall: exit 0
- CLI help: exit 0
- diff whitespace check: exit 0

After fixing the P1 lineage root issue:

```powershell
python -m pytest tests\test_strategy_lineage.py tests\test_dashboard.py tests\test_operator_console.py -k "strategy_lineage or lineage_uses_parent" -q
python -m pytest tests\test_strategy_lineage.py tests\test_dashboard.py tests\test_operator_console.py -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Observed results:

- targeted P1 regression tests: `6 passed`
- dashboard/operator-console/lineage tests: `48 passed`
- full suite: `367 passed`
- compileall: exit 0
- CLI help: exit 0
- diff whitespace check: exit 0

## Reviewer Verdict

Initial reviewer: `CHANGES REQUESTED`.

Follow-up reviewer after P1 regression fix: `PASS`.

Residual risk accepted for this PR: lineage currently covers the direct parent
plus direct revisions. Recursive multi-generation revision trees are deferred.

## Scope Boundary

This PR is read-only summary and UX visibility. It does not execute retests,
promote strategies, mutate strategy cards, place orders, or add broker/live
execution behavior.
