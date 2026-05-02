# PR129: Strategy Rule Summary Digest

## Context

PR126 made the dashboard and operator console show strategy rules beside the
latest strategy research digest by resolving the referenced `StrategyCard`.
That improved human readability, but automation still had to join multiple
artifacts to understand the concrete strategy logic. This kept the digest from
being a complete handoff artifact for self-evolving strategy research.

## Decision

Add `strategy_rule_summary` to `StrategyResearchDigest` as an append-only,
machine-readable list of concise rule lines. The digest builder derives the
list deterministically from the current strategy card:

- hypothesis;
- signal description;
- first entry rule;
- first exit rule;
- first risk rule;
- selected failure controls and replacement research gates when available.

Dashboard and operator-console rendering now prefer `strategy_rule_summary`
from the digest. They still fall back to the referenced strategy card for
legacy digest rows that do not contain the new field.

## Scope

Included:

- backward-compatible `StrategyResearchDigest` model parsing;
- digest builder summary extraction;
- dashboard and operator-console preference for persisted digest rules;
- regression tests proving the UX uses digest-owned rule summaries.

Excluded:

- strategy mutation;
- changing research gates;
- changing backtest, walk-forward, or paper-shadow evaluation logic;
- real broker or live-order execution.

## Verification

- `python -m pytest tests\test_strategy_research_digest.py::test_record_strategy_research_digest_persists_current_strategy_and_lineage_context tests\test_strategy_research_digest.py::test_strategy_research_digest_prefers_newer_retest_leaderboard_over_stale_autopilot_run tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q`
