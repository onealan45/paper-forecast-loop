# PR161 Digest Evidence Point In Time

## Problem

PR160 made read-side digest evidence fail closed when explicit evidence IDs were
unresolved. The resolver still allowed an explicit digest evidence ID to resolve
to an artifact whose `created_at` was later than the digest timestamp.

That is a point-in-time leak in the operator-facing dashboard and console: a
historical digest should not display evidence that did not exist when the digest
was created.

## Decision

`resolve_strategy_digest_evidence()` now requires explicit ID matches to satisfy
all of these conditions:

- artifact ID matches the digest-listed ID;
- artifact symbol matches the digest symbol;
- artifact `created_at` is less than or equal to the digest `created_at`.

If an explicit ID points to a future artifact, that evidence type remains empty.
Because the digest explicitly listed an ID for that type, the resolver still
does not fall back to latest same-symbol evidence.

## Acceptance

- Explicit digest IDs resolve only point-in-time evidence.
- Explicit future IDs do not resolve and do not fallback.
- Existing explicit-ID, unresolved-ID, and no-ID fallback behavior remains
  covered by tests.

## Verification

- `python -m pytest tests\test_strategy_digest_evidence.py::test_resolve_strategy_digest_evidence_does_not_resolve_future_digest_ids -q`
- `python -m pytest tests\test_strategy_digest_evidence.py::test_resolve_strategy_digest_evidence_prefers_digest_evidence_ids tests\test_strategy_digest_evidence.py::test_resolve_strategy_digest_evidence_does_not_fallback_when_digest_ids_are_unresolved -q`
- `python -m pytest tests\test_strategy_digest_evidence.py -q`
