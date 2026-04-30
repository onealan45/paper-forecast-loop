# PR55 Lineage Replacement Visibility

Date: 2026-04-30

## Context

PR54 made replacement retest paper-shadow outcomes affect source lineage
performance counts and verdicts. That fixed the accounting path, but it still
left a readability gap: an operator could see the aggregate lineage verdict
change without a first-class explanation of which replacement strategy
contributed to that change.

The project direction prioritizes research capability, prediction quality, and
visible strategy reasoning. Replacement hypotheses therefore need to appear as
research evidence, not only as hidden contributors to counts.

## Decision

`StrategyLineageSummary` now includes explicit replacement contribution fields:

- `replacement_card_ids`
- `replacement_nodes`
- `replacement_count`

Each replacement node records:

- replacement strategy card id, name, status, and hypothesis
- source root card id
- source outcome id that triggered replacement
- replacement failure attributions
- latest replacement paper-shadow outcome id
- latest replacement recommended action
- latest replacement excess return after costs

Dashboard, operator console, and `strategy-lineage` JSON output now expose these
replacement contribution nodes alongside revision tree, performance verdict,
and performance trajectory.

## Non-Goals

- No strategy promotion logic is changed.
- No paper order, broker, sandbox, live execution, or real-capital behavior is
  added.
- Replacement cards remain separate replacement hypotheses, not child revisions.

## Verification

- Added lineage summary coverage for replacement node ids, source outcome,
  latest outcome, action, and excess return.
- Added dashboard and operator-console coverage requiring replacement
  contribution text after a replacement retest outcome exists.
- Existing lineage and replacement UX tests continue to pass.
