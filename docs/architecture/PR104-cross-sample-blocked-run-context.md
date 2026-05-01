# PR104 Cross-Sample Blocked Run Context

## Purpose

After PR103, active BTC storage could record a cross-sample autopilot run under
the direct `lineage_cross_sample_validation_agenda`. The run correctly remained
`BLOCKED` because locked evaluation, leaderboard, baseline, and walk-forward
gates did not pass. However, `lineage-research-plan` still rendered the next
task as `cross_sample_autopilot_run_missing`, which hid the actual blocked run
and made the repair path ambiguous.

## Decision

Lineage task planning now distinguishes three states:

- accepted cross-sample run exists -> task completed;
- no linked cross-sample run exists -> task blocked as missing;
- linked run exists but is blocked, stale, or invalid -> task blocked with that
  run id, blocker list, strategy targets, and latest lineage outcome.

The new blocked reason is:

- `cross_sample_autopilot_run_blocked`

The dashboard/operator-console display helper translates that reason while
preserving the raw machine code.

## Non-Goals

- Do not treat a blocked run as completed fresh-sample validation.
- Do not weaken locked evaluation, leaderboard, baseline, walk-forward, or
  paper-shadow gates.
- Do not auto-repair the blocked evidence chain.

## Runtime Evidence

Active BTC storage now surfaces blocked cross-sample run
`research-autopilot-run:016506777c8b2d13` against agenda
`research-agenda:d18e27908892e692` with blocker inputs such as
`locked_evaluation_not_rankable`, `baseline_edge_not_positive`,
`holdout_excess_not_positive`, `walk_forward_excess_not_positive`, and
`overfit_risk_flagged`.

## Verification

Added regression coverage proving:

- a blocked linked run is surfaced as blocked context instead of being
  mislabeled as missing;
- a stale linked run that points to an older paper-shadow outcome is surfaced as
  invalid context instead of being treated as completed validation;
- display copy covers `cross_sample_autopilot_run_blocked`.
