# PR103 Revision Cross-Sample Autopilot Anchor

## Purpose

PR102 makes cross-sample validation agendas name the latest revision card when
that revision produced the latest lineage improvement. The next gap was in
autopilot closure: `record-revision-retest-autopilot-run` still preferred the
older `paper_shadow_strategy_revision_agenda` for normal DRAFT revisions, so a
direct `lineage_cross_sample_validation_agenda` could remain blocked even after
the revision retest chain had completed.

## Decision

Completed revision retest autopilot runs now prefer a direct cross-sample agenda
when the agenda's strategy targets exactly match:

- the lineage root strategy card; and
- the completed revision card.

Replacement retest behavior keeps the same direct cross-sample preference, but
now shares the same exact target-set rule. A polluted cross-sample agenda that
includes unrelated strategy cards is ignored instead of being used as the
autopilot anchor.

## Non-Goals

- Do not mark blocked evaluation evidence as valid.
- Do not promote revisions or replacements.
- Do not change leaderboard, locked-evaluation, or paper-shadow gates.

## Verification

Added regression coverage for:

- normal DRAFT revision retest autopilot preferring a direct root-plus-revision
  `lineage_cross_sample_validation_agenda`;
- polluted cross-sample agendas with unrelated targets being ignored;
- replacement direct cross-sample anchoring remaining intact.
