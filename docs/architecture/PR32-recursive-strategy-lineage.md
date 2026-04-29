# PR32: Recursive Strategy Lineage

## Context

PR31 added read-only strategy lineage summaries, but the first implementation
covered only the parent strategy and its direct revision cards. That was enough
for the first self-evolution loop, but it lost signal once a revision itself
became the parent of another revision.

For the user's current research direction, this is a material limitation:
self-evolving strategy work must show how an idea changes over multiple failed
or revised paper-shadow cycles, not only the latest direct child.

## Decision

`forecast_loop.strategy_lineage` now resolves lineage in two recursive steps:

- walk `parent_card_id` upward until the original root strategy card is found;
- collect all descendant strategy cards under that root, not only direct
  children.

The resulting `StrategyLineageSummary` still uses the same read-only fields:

- root strategy card id
- revision card ids and revision count
- paper-shadow outcome count
- recommended strategy action counts
- failure-attribution counts
- best and worst after-cost excess return
- latest paper-shadow outcome id

The difference is that those fields now include multi-generation revision
trees.

## Scope

This PR does not create, execute, promote, demote, or mutate strategies. It
does not add broker behavior or any order path. It only improves how existing
strategy-card and paper-shadow artifacts are summarized for research UX.

## UX Behavior

Dashboard and operator console strategy lineage panels now keep second- and
later-generation revisions attached to the original strategy root. If a first
revision fails and produces a second revision, the UX shows both revision cards,
all related paper-shadow outcomes, repeated failure attributions, and the
latest outcome in one lineage summary.

## Verification

Regression tests cover:

- `build_strategy_lineage_summary` resolving a second-generation revision back
  to the original root card;
- dashboard snapshot and HTML including nested revision outcome evidence;
- operator console research and overview pages including nested revision
  outcome evidence.

Targeted command:

```powershell
python -m pytest tests\test_strategy_lineage.py tests\test_dashboard.py tests\test_operator_console.py -k "strategy_lineage" -q
```
