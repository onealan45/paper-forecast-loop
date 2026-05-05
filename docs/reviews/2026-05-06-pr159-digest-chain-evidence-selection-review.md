# PR159 Digest Chain Evidence Selection Review

## Scope

Reviewed branch `codex/pr159-digest-chain-evidence-selection`.

Files in scope:

- `src/forecast_loop/strategy_research_digest.py`
- `tests/test_strategy_research_digest.py`
- `docs/architecture/PR159-digest-chain-evidence-selection.md`

Runtime outputs, `paper_storage/`, `reports/`, `.codex/`, `.env`, and secrets
were not part of the review scope and must not be committed.

## Reviewers

- Final reviewer subagent `Dewey` initially returned `BLOCKED`.
- Final reviewer subagent `Confucius` returned `APPROVED` after the blocking
  issue was fixed.

## Blocking Finding Resolved

### P1 Chain-linked IDs still fell back when unresolved

The first review found that explicit active-chain evidence IDs were collected,
but unresolved, future-filtered, or symbol-mismatched IDs still allowed
`strategy-research-digest` to fall back to the latest same-symbol artifact.
That could mix an active strategy digest with unrelated newer backtest or
walk-forward evidence.

Resolution:

- Added `_chain_artifact_or_fallback`.
- If active-chain IDs exist for an evidence type, the selector now resolves only
  those IDs and returns `None` when they are unavailable.
- Same-symbol fallback is now allowed only when the active chain has no linked
  IDs for that evidence type.
- Added regression coverage for unresolved linked IDs.
- Updated the architecture note to document the fail-closed behavior.

## Final Result

`APPROVED`

No blocking findings remained. The digest selector now keeps strategy summary
evidence aligned with the active retest chain and avoids borrowing unrelated
same-symbol artifacts when linked evidence is unresolved.

## Verification

- `python -m pytest tests\test_strategy_research_digest.py::test_strategy_research_digest_prefers_active_retest_evidence_over_newer_symbol_artifacts -q` -> passed
- `python -m pytest tests\test_strategy_research_digest.py::test_strategy_research_digest_does_not_fallback_when_active_retest_evidence_ids_are_unresolved -q` -> passed
- `python -m pytest tests\test_strategy_research_digest.py -q` -> `16 passed`
- `python -m pytest -q` -> `565 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> passed, with LF/CRLF warnings only

Runtime smoke:

- Latest active-storage digest: `strategy-research-digest:e1716d3756be1177`
- Current strategy card: `strategy-card:a449935e2c48473c`
- Current action: `WAIT_FOR_PAPER_SHADOW_OUTCOME`
- Digest evidence included active retest backtest
  `backtest-result:5ec1824ba7acab13`.
- Digest evidence included active retest walk-forward
  `walk-forward:582b3c2bc39004ea`.
- Digest evidence excluded unrelated walk-forward
  `walk-forward:5e77659c586cee55`.
