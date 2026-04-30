# PR63: Cross-Sample Autopilot Run UX

## Context

PR62 anchored completed replacement retest autopilot runs to a direct
`lineage_cross_sample_validation_agenda` when that agenda names the replacement
strategy card. That made the artifact chain correct, but the UX still treated
the cross-sample agenda as only a pending handoff.

There was also a visibility edge case: once a linked autopilot run and newer
paper-shadow outcome existed, the lineage task plan could advance and no longer
be the best way to recover the cross-sample agenda for display.

## Decision

Dashboard and operator console snapshots now recover the latest cross-sample
agenda from linked research autopilot runs when the current task plan no longer
points at it. The cross-sample agenda panel also shows:

- linked autopilot run id
- loop status
- linked paper-shadow outcome id
- next research action

This keeps the fresh-sample validation chain visible as:

`cross-sample agenda -> linked autopilot run -> fresh-sample outcome -> next research action`

## Verification

- `python -m pytest tests\test_dashboard.py::test_dashboard_shows_lineage_cross_sample_validation_agenda tests\test_operator_console.py::test_operator_console_shows_lineage_cross_sample_validation_agenda -q`

