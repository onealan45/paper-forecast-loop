# PR159 Digest Chain Evidence Selection

## Problem

`strategy-research-digest` already lets the latest digest-selected strategy own
the current strategy slot. The remaining evidence selector could still append
the latest same-symbol backtest or walk-forward artifact when the active retest
chain already had explicit evidence IDs on its trial and locked evaluation.

That made the digest summary able to mix the current replacement strategy with
newer but unrelated same-symbol research evidence. For an operator-facing
strategy research loop, that is misleading: the current hypothesis, locked
evaluation, leaderboard entry, and displayed evidence should describe the same
research chain.

## Decision

Digest evidence selection now prefers the active strategy chain before using
same-symbol fallback artifacts:

- locked evaluation linked event-edge / backtest / walk-forward;
- experiment trial linked event-edge / backtest / walk-forward;
- strategy-card listed evidence IDs;
- only then the previous same-symbol fallback selection.

If the active chain has linked IDs for an evidence type but those IDs cannot be
resolved from point-in-time artifacts, that evidence type stays absent from the
digest instead of borrowing newer same-symbol evidence. Fallback is allowed only
when the active chain has no linked IDs for that evidence type.

This preserves the existing decision-blocker fallback when the current strategy
chain has no explicit research evidence, while preventing an active retest from
borrowing evidence from an unrelated newer artifact.

## Acceptance

- A digest for an active retest includes the retest-linked backtest and
  walk-forward IDs.
- Newer unrelated same-symbol backtest or walk-forward artifacts do not enter
  that digest evidence list.
- If retest-linked IDs are unresolved, newer unrelated same-symbol artifacts are
  still excluded instead of used as fallback evidence.
- The digest research summary reports the active retest metrics, not the newer
  unrelated metrics.
- Existing digest tests continue to pass.

## Verification

- `python -m pytest tests\test_strategy_research_digest.py::test_strategy_research_digest_prefers_active_retest_evidence_over_newer_symbol_artifacts -q`
- `python -m pytest tests\test_strategy_research_digest.py::test_strategy_research_digest_does_not_fallback_when_active_retest_evidence_ids_are_unresolved -q`
- `python -m pytest tests\test_strategy_research_digest.py -q`
