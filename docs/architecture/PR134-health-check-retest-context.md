# PR134 Health Check Retest Evidence Context

## Problem

PR133 made the retest planner reject PASSED revision/replacement retest trials
when their linked backtest or walk-forward artifacts were created under another
retest chain `id_context`. That protected task planning, but storage health could
still report the same polluted artifact graph as only a generic link-valid state.

For self-evolving strategy research, a PASSED retest trial is an evidence claim.
If it points to cross-card or cross-chain evaluation artifacts, health-check must
surface that as a repair-visible storage defect instead of relying on the
planner to silently ignore the trial.

## Decision

`health-check` now inspects PASSED revision/replacement retest trials with
`revision_retest_protocol == RETEST_PROTOCOL_VERSION`.

For each linked evidence artifact:

- the linked backtest result must resolve to a backtest run whose
  `decision_basis` contains a valid retest chain `id_context`
- the linked walk-forward validation must contain the same valid retest chain
  `id_context`
- valid contexts include the PASSED trial context and, for a matching same-chain
  PENDING source trial, the original source trial context
- a PASSED retest trial with linked evidence but no `revision_source_outcome_id`
  is unverifiable and must be health-blocking
- `id_context` comparison is token-based rather than prefix-based, so
  `<valid-context>-extra` is not accepted as the valid context

When the check fails, health-check emits blocking findings:

- `revision_retest_passed_trial_backtest_context_mismatch`
- `revision_retest_passed_trial_walk_forward_context_mismatch`
- `revision_retest_passed_trial_context_unverifiable`

## Scope

This PR does not change the retest planner or executor. It adds an independent
health-check guard so artifact pollution is visible even outside planner output.

## Verification

Regression coverage creates a PASSED retest trial for the current revision card
that links to backtest and walk-forward evidence carrying a different
`revision_retest:<card>:<trial>:<source_outcome>` context. The health check must
emit both blocking context-mismatch finding codes.
