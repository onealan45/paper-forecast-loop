# PR37: Strategy Lineage Performance Trajectory

## Context

PR31 through PR36 made strategy lineage visible, recursive, tree-shaped,
human-readable, and escaped. The remaining UX weakness was that lineage still
looked like structure plus text; it did not directly show whether revisions
improved or worsened paper-shadow evidence.

The user wants stronger research and prediction visibility. For strategy
self-evolution, the operator needs to see the performance path of a strategy
family across parent and revision shadow outcomes.

## Decision

Add `StrategyLineageOutcomeNode` to the lineage summary. Each node records:

- paper-shadow outcome id
- strategy card id
- after-cost excess return
- delta versus the previous lineage outcome with known excess return
- change label: `基準`, `改善`, `惡化`, `持平`, or `未知`
- recommended strategy action
- failure attributions

Dashboard and operator console now render a `表現軌跡` section beside the
revision tree.

## Scope

This PR is read-only summary and UX visibility. It does not execute retests,
mutate strategy cards, promote/demote strategies, or add broker/order behavior.

## Verification

Regression tests cover:

- lineage outcome nodes and delta/change labels;
- dashboard rendering of the latest nested outcome's excess, delta, action, and
  failure attribution;
- operator console research and overview rendering of the same trajectory.

Targeted command:

```powershell
python -m pytest tests\test_strategy_lineage.py tests\test_dashboard.py tests\test_operator_console.py -q
```
