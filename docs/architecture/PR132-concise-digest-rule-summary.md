# PR132: Concise Digest Rule Summary

## Context

PR129 added `strategy_rule_summary` so automation and UX can read concrete
strategy logic from one digest artifact. Active storage then exposed a
readability problem: the hypothesis rule could copy a full strategy-card
paragraph, including long failure-key lists, into the first dashboard line.

The full strategy card should remain unchanged, but the digest handoff should
stay concise.

## Decision

Compact strategy rule-summary text at digest build time:

- short rule text remains unchanged;
- long text prefers the first sentence when it fits the summary budget;
- text without a usable sentence boundary is truncated deterministically with
  an ASCII ellipsis;
- the full `label + text` rule line is kept within the summary budget;
- the full original strategy-card fields remain available in the strategy card
  artifact.

This keeps the digest as a readable handoff artifact without mutating research
source material.

## Scope

Included:

- deterministic compaction helper in the digest builder;
- regression test proving a long hypothesis keeps only the concise first
  sentence and drops noisy failure-key spillover;
- regression test proving no-boundary fallback truncation is deterministic and
  bounded after the rule label is included;
- README and PRD updates.

Excluded:

- translating strategy-card content;
- changing digest ids or source artifact schemas;
- changing dashboard/operator-console layout;
- changing strategy evaluation, backtest, or paper-shadow logic.

## Verification

- `python -m pytest tests\test_strategy_research_digest.py::test_strategy_research_digest_compacts_long_rule_summary_text -q`
