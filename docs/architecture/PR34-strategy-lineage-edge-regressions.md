# PR34: Strategy Lineage Edge Regressions

## Context

PR33 exposed revision parent/depth rows in the strategy UX. The final reviewer
accepted the change but noted that branching, missing-parent, and cycle behavior
had only been smoke-checked, not committed as regression tests.

These cases matter because strategy self-evolution will eventually create
branching hypothesis trees, and corrupted or partially migrated artifacts should
not destabilize the read-only UX.

## Decision

Add committed regression coverage for:

- branching revision trees, preserving deterministic DFS order by
  `(created_at, card_id)`;
- missing parents, falling back to the current card as the lineage root while
  still including descendants;
- parent cycles, terminating safely and anchoring the UX to the originally
  requested card.

The cycle case revealed a real edge bug: traversal terminated but selected the
cycle's other node as root. The fix now returns the originally requested card
when a parent cycle is detected.

## Scope

This PR is lineage hardening only. It does not change strategy generation,
promotion, retest execution, broker behavior, or order paths.

## Verification

Targeted command:

```powershell
python -m pytest tests\test_strategy_lineage.py -q
```

Full gate remains:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
git ls-files .codex paper_storage reports output .env
```
