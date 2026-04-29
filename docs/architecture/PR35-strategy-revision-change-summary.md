# PR35: Strategy Revision Change Summary

## Context

PR31 through PR34 made strategy lineage visible, recursive, tree-shaped, and
edge-case hardened. The UX could show which revision belonged where, but it
still forced the operator to infer what each revision actually changed from raw
strategy-card artifacts.

The user's current direction prioritizes research quality, prediction quality,
and concrete strategy visibility. A self-evolving strategy loop must show the
revision hypothesis and failure mode it is trying to repair.

## Decision

`StrategyLineageRevisionNode` now carries human-readable revision context:

- strategy name
- status
- hypothesis
- source outcome id
- intended failure attributions to repair

Dashboard and operator console `Revision Tree` rows now include:

```text
Depth <n> / Parent <id> / <revision id> / <status> /
Hypothesis <text> / Source <outcome id> / Fixes <attributions>
```

This keeps the lineage summary read-only while making strategy evolution easier
to inspect from UX.

## Scope

This PR does not generate strategies, mutate strategy cards, promote/demote
strategies, execute retests, or add broker/order behavior. It only exposes
existing `StrategyCard` fields and revision parameters through the read-only
lineage summary.

## Verification

Regression tests cover:

- lineage nodes carrying revision name/status/hypothesis/source/failure data;
- dashboard rendering of nested revision hypothesis, source outcome, and fixes;
- operator console rendering of the same data in research and overview pages.

Targeted command:

```powershell
python -m pytest tests\test_strategy_lineage.py tests\test_dashboard.py tests\test_operator_console.py -q
```
