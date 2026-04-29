# PR31: Strategy Lineage Visibility

## Context

The research direction prioritizes strategy quality, self-evolution, and
concrete strategy visibility. PR30 made completed revision retest autopilot runs
visible, but the UX still lacked a compact view of how a strategy family is
evolving across parent strategy cards, DRAFT revisions, and paper-shadow
outcomes.

## Decision

Add a read-only `StrategyLineageSummary` derived from existing artifacts:

- root strategy card id
- revision card ids and revision count
- paper-shadow outcome count
- recommended strategy action counts
- failure-attribution counts
- best and worst after-cost excess return
- latest paper-shadow outcome id

The summary is computed by `forecast_loop.strategy_lineage` and carried by the
dashboard and operator console snapshots.

## Scope

This PR does not create new strategy cards, promote or demote strategies,
execute retests, submit orders, or mutate artifacts. It only summarizes existing
strategy-card and paper-shadow evidence.

## UX Behavior

Dashboard and operator console strategy surfaces now include a `策略 lineage`
panel. The operator can see whether failures are concentrated around actions
such as `REVISE_STRATEGY` or `QUARANTINE_STRATEGY`, and whether the dominant
failure attribution is repeated across parent and revision outcomes.

## Verification

Regression tests cover:

- summary counting for revisions, actions, failure attributions, and best/worst
  excess return
- dashboard rendering of the lineage summary
- operator console research and overview rendering of the same lineage summary

Targeted command:

```powershell
python -m pytest tests\test_strategy_lineage.py tests\test_dashboard.py tests\test_operator_console.py -k "strategy_lineage" -q
```
