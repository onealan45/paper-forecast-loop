# PR127: Refresh Legacy Replacement Card Content

## Context

PR125 made newly drafted lineage replacement strategy cards failure-aware, but
runtime storage can already contain older DRAFT replacement cards created from
the generic template. Because strategy cards are immutable audit artifacts in
JSONL and SQLite storage, updating the existing `card_id` would either be
ignored by the repository or rewrite history.

## Decision

Add `refresh-replacement-strategy-card` as an explicit append-only refresh path.
The command creates a new DRAFT `lineage_replacement_strategy_hypothesis`
successor card when a legacy replacement card is missing
`replacement_strategy_archetype`.

The refreshed card:

- preserves the original source lineage root and source paper-shadow outcome;
- records `replacement_refresh_source_card_id`;
- uses the same failure-aware design helper as newly drafted replacements;
- keeps the replacement in DRAFT until locked retest and paper-shadow evidence
  exist;
- does not reuse old retest evidence as proof of the refreshed rules.

Lineage task planning now resolves multiple replacements for the same source
outcome by newest `(created_at, card_id)`, so a refreshed successor becomes the
visible research target while older cards remain auditable.

## Scope

Included:

- domain helper `refresh_replacement_strategy_hypothesis`;
- CLI command `refresh-replacement-strategy-card`;
- latest-replacement selection for lineage task plans;
- regression tests for successor creation, CLI output, and plan selection.

Excluded:

- mutating existing `strategy_cards.jsonl` rows;
- automatically retesting the refreshed card;
- changing leaderboard, paper-shadow, or promotion gates;
- live trading, broker execution, or real order submission.

## Verification

- `python -m pytest tests\test_strategy_evolution.py tests\test_lineage_research_plan.py tests\test_lineage_research_executor.py tests\test_strategy_lineage.py tests\test_strategy_research_digest.py tests\test_dashboard.py::test_dashboard_shows_lineage_replacement_strategy_hypothesis tests\test_operator_console.py::test_operator_console_shows_lineage_replacement_strategy_hypothesis -q`
