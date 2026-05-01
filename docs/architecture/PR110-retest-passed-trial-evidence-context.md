# PR110 Retest Passed Trial Evidence Context

## Purpose

PR109 made executor-created retest backtest and walk-forward artifacts
chain-local by adding retest-specific evidence ID context. Active BTC-USD
runtime then exposed the next collision: `record_passed_retest_trial` could
still return an older stale PASSED `experiment_trial`.

The stale and fresh PASSED trials shared the same generic experiment-trial ID
inputs:

- strategy card id;
- trial index;
- status;
- seed;
- protocol/source parameters.

The ID did not include the linked backtest or walk-forward evidence IDs. Because
JSONL save is append-unique by artifact ID, the fresh PASSED trial was not
persisted and the plan stayed on `record_passed_retest_trial`.

## Decision

Revision retest PASSED trials now include a parameter named
`revision_retest_evidence_context` with the linked evidence IDs:

```text
backtest_<backtest_result_id>__walk_forward_<walk_forward_validation_id>
```

This keeps generic experiment trial behavior unchanged while making
executor-recorded revision/replacement retest PASSED trials evidence-specific.

The read-only task plan command also includes the same parameter, so a manual
operator copy of the suggested `record-experiment-trial` command has the same
identity semantics as the executor. The delimiter intentionally avoids
PowerShell metacharacters.

## Non-Goals

- Do not change generic experiment trial identity.
- Do not rewrite old stale PASSED trial rows.
- Do not loosen PR108 freshness checks.
- Do not promote, trade, or create paper-shadow outcomes without explicit
  observation evidence.

## Runtime Evidence

Before PR110, active replacement retest execution returned stale trial
`experiment-trial:b71d9655fa8d3e41` and the plan stayed on
`record_passed_retest_trial`.

With PR110 logic, the same active replacement retest records fresh PASSED trial
`experiment-trial:97e6fc0e81eef8bb` and advances to
`evaluate_leaderboard_gate`.

## Verification

Regression coverage proves that `execute_revision_retest_next_task` records an
evidence-specific PASSED trial when a stale same-card/same-index PASSED trial
already exists, and that `revision-retest-plan` exposes the matching
`revision_retest_evidence_context` parameter in the copyable command.
