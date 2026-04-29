# Plan: Strategy Revision Escape Regressions

## Scope

Convert the PR35 reviewer residual risk into committed tests: revision change
summary fields must remain escaped when strategy names, hypotheses, source
outcomes, or intended fixes contain malicious HTML.

## Steps

1. Add dashboard and operator-console tests with `<script>` fixtures.
2. Run targeted tests and change production code only if escaping fails.
3. Update README, PRD, architecture, and review archive.
4. Run full verification gates.
5. Request independent reviewer subagent review before PR/merge.

## Acceptance Criteria

- Raw `<script>` strings do not appear in dashboard or operator-console output.
- Escaped strategy name, hypothesis, source outcome, and fix attribution remain
  visible to the operator.
- No production change is made unless the tests expose a real escape bug.
- Full gates pass.
- Reviewer subagent reports no blocking findings.
