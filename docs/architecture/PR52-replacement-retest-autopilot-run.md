# PR52 Replacement Retest Autopilot Run

Date: 2026-04-30

## Context

Replacement strategies now share the existing retest scaffold and executor
chain. After a replacement strategy completes retest and paper-shadow
observation, the final audit step still depended on the older revision-only
agenda lookup.

That prevented a completed replacement retest chain from recording a
`ResearchAutopilotRun` through `record-revision-retest-autopilot-run`.

## Decision

`record_revision_retest_autopilot_run` now supports replacement retest cards:

- traditional revision cards still use `paper_shadow_strategy_revision_agenda`;
- lineage replacement cards use the source `strategy_lineage_research_agenda`
  when the agenda references the replacement source lineage root;
- replacement retest paper-shadow outcomes do not require a separate
  `StrategyDecision` artifact for the autopilot run, matching the existing
  revision-retest behavior.

The completed chain still records the same `ResearchAutopilotRun` artifact
shape and does not introduce a separate replacement-only pipeline.

## Non-Goals

- No strategy promotion is added.
- No execution, order, broker, sandbox, live trading, or real-capital behavior
  is added.
- No new strategy decision generation is added.
- No agenda mutation is performed.

## Verification

- Added helper coverage for a completed lineage replacement retest chain.
- Added CLI coverage for `record-revision-retest-autopilot-run` with a
  replacement card.
- The tests assert no `agenda_strategy_card_mismatch` or
  `strategy_decision_missing` blockers are introduced for the replacement
  retest completion path.
