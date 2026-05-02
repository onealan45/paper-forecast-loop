# PR126: Digest Strategy Rules UX

## Context

The strategy research digest gives automation a compact view of the current
research state, but the dashboard and operator console only showed the digest
summary, next rationale, failure concentration, and evidence ids. That still
forced a human to scroll elsewhere to understand the concrete strategy rules.

## Decision

Keep the digest artifact schema unchanged and enrich only the read-only UX:

- resolve the strategy card referenced by the latest digest;
- show digest-linked hypothesis, entry rules, exit rules, and risk rules beside
  the digest;
- show the same content in both dashboard and operator console overview /
  research surfaces.

This preserves JSONL/SQLite compatibility while making the strategy content
visible at the point where operators already read the current research handoff.

## Scope

Included:

- dashboard snapshot field for the digest-linked strategy card;
- operator-console snapshot field for the digest-linked strategy card;
- digest panel and preview rule rendering;
- regression tests for dashboard and operator console visibility.

Excluded:

- strategy research digest schema changes;
- strategy mutation;
- changing evaluation gates;
- live trading or broker execution.

## Verification

- `python -m pytest tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q`
