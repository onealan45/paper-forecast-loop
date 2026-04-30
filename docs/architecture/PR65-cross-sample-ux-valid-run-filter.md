# PR65: Cross-Sample UX Valid Run Filter

## Context

PR63 made linked cross-sample autopilot runs visible in dashboard and operator
console. PR64 then made the lineage task plan require a completed linked
autopilot run before treating fresh-sample validation as complete.

The remaining UX gap was evidence selection. The dashboard/operator console
could still display a newer same-agenda run as if it were valid fresh-sample
evidence when that run was blocked, pointed at a missing paper-shadow outcome,
or belonged to another same-symbol lineage.

## Decision

The UX now applies the same validity contract expected by the lineage planning
layer before a cross-sample run is shown as linked evidence:

- `decision_basis` must be `research_paper_autopilot_loop`.
- the run must not be `BLOCKED` and must not have blocked reasons.
- `paper_shadow_outcome_id` must exist in storage.
- the linked outcome must be the current lineage `latest_outcome_id`.
- the linked outcome's strategy card must belong to the current root,
  revision, or replacement lineage.

The dashboard and operator console also anchor lineage summaries back to the
current lineage task-plan root when an unrelated newer same-symbol autopilot run
would otherwise hijack the generic latest research chain.

Revision/replacement retest autopilot panels can still display repair-oriented
blocked retest runs, but the run must reference an experiment trial created by
the revision-retest protocol for that exact revision or replacement strategy
card. A cross-sample run, parent strategy run, or unrelated same-symbol run
cannot masquerade as retest closure just because it shares the same strategy
card id or emits a generic `strategy_card` step.

## Verification

- `python -m pytest tests\test_dashboard.py::test_dashboard_shows_lineage_cross_sample_validation_agenda tests\test_operator_console.py::test_operator_console_shows_lineage_cross_sample_validation_agenda -q`
