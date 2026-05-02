# PR130: Dashboard Digest Rules List

## Context

PR129 made `StrategyResearchDigest.strategy_rule_summary` the machine-readable
handoff for concrete strategy logic. The dashboard consumed that field, but it
rendered all rule lines through the generic inline metadata helper. Active
storage showed the problem immediately: a long hypothesis, signal description,
entry rule, exit rule, risk rule, failure controls, and validation gates were
all compressed into one dense `<dd>` string.

## Decision

Render digest-owned strategy rules as a vertical dashboard list:

- one rule line per list item;
- wrapped code text for long hypotheses and failure keys;
- legacy digest fallback to the linked strategy card remains unchanged.

The goal is not to hide detail. It is to make the current strategy logic
scannable before the operator reaches lower-level artifact tables.

## Scope

Included:

- dashboard digest rule-list helper and CSS;
- regression test proving digest rules are no longer inline-separated;
- README and PRD status updates.

Excluded:

- changing the `StrategyResearchDigest` schema;
- changing operator-console rendering, which already uses a vertical list;
- changing strategy generation, gates, or paper-shadow scoring.

## Verification

- `python -m pytest tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary -q`
