# PR33: Strategy Lineage Tree Visibility

## Context

PR32 made strategy lineage recursive, but the visible lineage was still a flat
list of revision card ids. That preserved counts and outcomes, yet it did not
show how nested or sibling revisions relate to each other.

For self-evolving strategy research, parent/depth structure matters. A second
revision that fixes the first revision is not the same thing as a sibling
revision that explores a separate hypothesis.

## Decision

`StrategyLineageSummary` now includes `revision_nodes`. Each node records:

- revision card id
- parent card id
- depth from the root strategy card

The existing summary fields remain unchanged for compatibility:

- `revision_card_ids`
- revision count
- action counts
- failure-attribution counts
- best/worst after-cost excess return
- latest outcome id

Dashboard and operator console now render a `Revision Tree` section with
`Depth <n> / Parent <id> / <revision id>` rows.

## Scope

This PR is read-only UX and summary metadata. It does not create strategy
cards, mutate strategies, execute retest tasks, promote/demote strategies,
submit orders, or add broker behavior.

## Verification

Regression tests cover:

- summary nodes for a second-generation revision;
- dashboard snapshot and HTML showing depth/parent rows;
- operator console research and overview pages showing depth/parent rows.

Targeted command:

```powershell
python -m pytest tests\test_strategy_lineage.py tests\test_dashboard.py tests\test_operator_console.py -k "strategy_lineage" -q
```
