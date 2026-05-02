# PR131: Traditional Chinese Digest Panel Labels

## Context

The strategy research digest is now the primary handoff surface for current
strategy logic. PR129 and PR130 made the content more complete and scannable,
but the digest panels still showed operator-facing labels such as `Digest`,
`Strategy`, `Outcome`, `Recommended`, `Failure concentration`, `Next rationale`,
`Digest strategy rules`, and `Evidence`.

That mixed-language surface weakens readability for the current Traditional
Chinese UX target.

## Decision

Localize the strategy research digest panel labels in both dashboard and
operator console:

- `摘要 ID`
- `策略`
- `Paper-shadow 結果`
- `建議動作`
- `失敗集中`
- `下一步理由`
- `策略規則摘要`
- `證據`

The legacy strategy-card fallback labels are also localized to `假說`, `進場`,
`出場`, and `風控`.

## Scope

Included:

- dashboard digest panel labels;
- operator-console digest panel and overview preview labels;
- regression tests requiring Traditional Chinese labels and rejecting the old
  `Digest strategy rules` / `Failure concentration` labels in the digest
  sections;
- README and PRD updates.

Excluded:

- broader dashboard-wide translation;
- changing artifact schemas or strategy generation logic;
- changing evidence, lineage, or paper-shadow calculations.

## Verification

- `python -m pytest tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q`
