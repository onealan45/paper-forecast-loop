# PR62: Cross-Sample Autopilot Agenda Anchor

## Context

PR58-PR61 created and exposed `lineage_cross_sample_validation_agenda`
artifacts for improving lineages and improving replacement retests. Those
agendas can now include both the lineage root strategy card and the exact
replacement card being validated.

However, completed replacement retest autopilot runs still resolved their
agenda through the older root-level `strategy_lineage_research_agenda`. That
kept the completed evidence chain valid, but it weakened the handoff: the
fresh-sample validation pass did not close under the agenda that explicitly
requested that validation.

## Decision

When recording a completed replacement retest autopilot run, prefer the latest
`lineage_cross_sample_validation_agenda` that directly includes the replacement
strategy card. If no such direct-card cross-sample agenda exists, keep the
existing fallback to the root-level `strategy_lineage_research_agenda`.

This keeps the progression:

`improving replacement -> cross-sample agenda -> completed retest autopilot run`

as one visible research chain.

## Verification

- `python -m pytest tests\test_research_autopilot.py::test_replacement_retest_autopilot_prefers_direct_cross_sample_agenda tests\test_research_autopilot.py::test_replacement_retest_autopilot_helper_records_latest_completed_chain -q`

