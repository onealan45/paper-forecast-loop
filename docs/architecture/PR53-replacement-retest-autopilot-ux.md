# PR53 Replacement Retest Autopilot UX

Date: 2026-04-30

## Context

PR52 allowed completed lineage replacement retest chains to record a final
`ResearchAutopilotRun` through `record-revision-retest-autopilot-run`. The
dashboard and operator console still only showed the replacement strategy and
scaffold/executor state, so the UX did not show whether the replacement
hypothesis had completed the research audit loop.

## Decision

Dashboard and operator console snapshots now expose a replacement-specific
latest retest autopilot run:

- `latest_lineage_replacement_retest_autopilot_run`

The replacement strategy panel now shows:

- loop status;
- run id;
- next research action;
- paper-shadow outcome id;
- blockers;
- step list.

The panel explicitly frames this as read-only research evidence. It does not
mean the strategy passed promotion gates, placed an order, or moved into any
real-capital workflow.

## Non-Goals

- No retest execution behavior changes.
- No strategy promotion or automatic mutation.
- No paper order, broker, sandbox, live trading, or real-capital path.
- No new artifact schema.

## Verification

- Dashboard test now seeds a replacement retest autopilot run and asserts it is
  selected and rendered in the replacement panel.
- Operator console test covers the same state.
- Existing revision-candidate retest autopilot wiring remains separate.
