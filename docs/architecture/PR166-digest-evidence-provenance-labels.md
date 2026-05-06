# PR166: Digest Evidence Provenance Labels

## Context

PR165 disabled event-edge fallback so an unlinked event-edge artifact can no
longer appear as active strategy validation. Active runtime verification showed
the same dashboard area still needed stronger provenance for backtest and
walk-forward metrics: they may be direct strategy-chain evidence or same-symbol
background fallback.

Without an explicit source label, the operator can read fallback metrics as if
the active strategy chain directly linked them.

## Decision

Strategy digest evidence now carries per-metric provenance:

- `direct`: the metric was resolved from digest/strategy-chain evidence IDs.
- `background_fallback`: the metric was selected as same-symbol context because
  no direct metric was linked.

Digest generation no longer writes fallback backtest/walk-forward IDs into
`evidence_artifact_ids`. Directly linked metrics still remain in the evidence
chain.

Fallback selection also excludes IDs listed in
`decision_research_artifact_ids`. Decision-blocker backtest and walk-forward
artifacts remain visible under `決策阻擋研究證據`, but they cannot leak into
`策略證據指標` as background fallback.

Dashboard and operator console render the provenance next to each metric:

- `來源：直接連結`
- `來源：背景參考（未由目前策略鏈直接指定）`

## Boundaries

- This does not change backtest, walk-forward, or event-edge calculations.
- This does not remove fallback context from research visibility.
- This does not hide decision-blocker research evidence; it remains under
  `決策阻擋研究證據`.
- This does not allow decision-blocker backtest/walk-forward artifacts to
  become active or background strategy metrics.
- This only prevents fallback context from being mistaken for directly linked
  active strategy validation.

## Verification

- Red tests:
  `python -m pytest tests\test_strategy_digest_evidence.py::test_resolve_strategy_digest_evidence_prefers_digest_evidence_ids tests\test_strategy_digest_evidence.py::test_resolve_strategy_digest_evidence_falls_back_to_latest_same_symbol_as_of tests\test_strategy_research_digest.py::test_strategy_research_digest_surfaces_latest_backtest_and_walk_forward_metrics tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q`
- Focused green:
  `python -m pytest tests\test_strategy_research_digest.py tests\test_strategy_digest_evidence.py tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q`
- Reviewer blocker regression:
  `python -m pytest tests\test_strategy_digest_evidence.py::test_resolve_strategy_digest_evidence_fallback_excludes_decision_blocker_ids tests\test_strategy_research_digest.py::test_strategy_research_digest_does_not_use_decision_blocker_backtest_or_walk_forward_as_strategy_metric -q`
