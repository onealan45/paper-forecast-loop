# PR160 Digest Evidence Resolver Fail Closed

## Problem

PR159 made new `strategy-research-digest` artifacts prefer active-chain evidence
and fail closed when linked evidence IDs are unresolved. The dashboard and
operator console still read digest evidence through
`resolve_strategy_digest_evidence()`. That resolver could select the latest
same-symbol event-edge, backtest, or walk-forward artifact when a digest already
listed an ID for that evidence type but the ID did not resolve.

That kept a read-side path for mixing a digest with unrelated newer evidence.

## Decision

`resolve_strategy_digest_evidence()` now uses per-type fail-closed selection:

- if the digest lists `event-edge:*`, only those event-edge IDs are eligible;
- if the digest lists `backtest-result:*`, only those backtest IDs are eligible;
- if the digest lists `walk-forward:*`, only those walk-forward IDs are
  eligible;
- fallback to latest same-symbol evidence remains available only when the
  digest lists no IDs for that evidence type.

The resolver also requires the resolved artifact symbol to match the digest
symbol, so cross-symbol IDs do not leak into the evidence cards.

## Acceptance

- Digest evidence cards prefer explicit digest IDs.
- Explicit but unresolved digest IDs do not fall back to unrelated same-symbol
  artifacts.
- No-ID digests still use the existing latest same-symbol fallback.
- The decision-blocker backtest fallback preference remains intact when no
  backtest ID is listed.

## Verification

- `python -m pytest tests\test_strategy_digest_evidence.py::test_resolve_strategy_digest_evidence_does_not_fallback_when_digest_ids_are_unresolved -q`
- `python -m pytest tests\test_strategy_digest_evidence.py::test_resolve_strategy_digest_evidence_falls_back_to_latest_same_symbol_as_of tests\test_strategy_digest_evidence.py::test_resolve_strategy_digest_evidence_fallback_prefers_decision_blocker_backtest -q`
- `python -m pytest tests\test_strategy_digest_evidence.py -q`
