# PR157 Digest Evidence Fallback Research Backtest

## Context

Recent decision, digest, dashboard, operator console, and research report paths
use the shared `latest_backtest_for_research` selector so standalone
decision-blocker backtests remain the primary research backtest evidence when
newer walk-forward-internal helper backtests also exist.

`resolve_strategy_digest_evidence` still fell back to raw latest same-symbol
backtest selection when a digest did not carry explicit `evidence_artifact_ids`.
That fallback mostly affects older or partial digest artifacts, but it could make
dashboard and operator console evidence cards display a walk-forward-internal
backtest as primary evidence.

## Decision

`resolve_strategy_digest_evidence` now accepts optional `backtest_runs` and uses
`latest_backtest_for_research` for its fallback backtest selection.

Dashboard and operator console now pass same-symbol `BacktestRun` records into
the resolver.

## Impact

- Explicit digest evidence ids still win first.
- Fallback backtest selection now matches the rest of the research loop.
- Existing callers remain compatible because `backtest_runs` is optional.
- No storage format change.

## Verification

- Added regression coverage for a digest without explicit evidence ids where a
  newer walk-forward-internal backtest coexists with an older standalone
  decision-blocker backtest.
- The resolver must choose the standalone blocker backtest.
