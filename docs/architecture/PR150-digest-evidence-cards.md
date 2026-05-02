# PR150 Digest Evidence Cards

## Context

PR148 added latest same-symbol event-edge, backtest, and walk-forward evidence
metrics to `StrategyResearchDigest.research_summary` and
`evidence_artifact_ids`. That made automation handoff more concrete, but the
dashboard and operator console still showed the metrics primarily as a dense
sentence.

## Decision

Add read-only structured evidence cards for the latest strategy research digest:

- Event edge: sample size, after-cost edge, hit rate, pass state, and flags.
- Backtest: strategy return, benchmark return, drawdown, win rate, and trades.
- Walk-forward: excess return, window count, test win rate, overfit window
  count, and flags.

The cards are resolved from the digest's linked evidence ids when present. For
older digests that do not include those ids, the UI falls back to the latest
same-symbol artifact created at or before the digest timestamp.

## Non-Goals

- No artifact schema change.
- No change to strategy decision gates.
- No automatic promotion from evidence cards.
- No hidden execution path.

## Verification

- `tests/test_strategy_digest_evidence.py`
- dashboard digest evidence-card regression
- operator-console digest evidence-card regression
