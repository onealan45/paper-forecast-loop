# PR163: Digest Decision Evidence Separation

## Context

After PR162, the active strategy digest correctly stays anchored on the current
replacement strategy card when newer decision-blocker agendas have no strategy
card. The remaining UX problem is semantic: active strategy validation evidence
and decision-blocker research evidence can appear near each other, which makes
it hard to tell whether a metric validates the current strategy or explains why
the current BUY/SELL decision is blocked.

## Decision

`StrategyResearchDigest` now records `decision_research_artifact_ids` separately
from the general `evidence_artifact_ids` chain. The new field is extracted from
the linked `StrategyDecision.decision_basis` for research artifacts with these
prefixes:

- `event-edge:`
- `backtest-result:`
- `walk-forward:`

Passing evidence is not copied into this field. A linked decision must expose an
actual `主要研究阻擋：...` summary before research artifact IDs are shown in
this blocker-specific section. This keeps tradeable `BUY` / `SELL` evidence and
non-research risk stops out of `決策阻擋研究證據`.

Dashboard and operator console now render a dedicated
`決策阻擋研究證據` section below `策略證據指標`.

## Boundaries

- This does not change decision generation, backtest results, walk-forward
  validation, or paper-shadow execution.
- This does not reinterpret decision-blocker evidence as active strategy
  validation.
- Existing digest JSONL rows remain readable because the new field defaults to
  an empty list.

## Verification

- Red test: `python -m pytest tests\test_strategy_research_digest.py::test_strategy_research_digest_records_decision_blocker_research_artifact_ids -q`
- Red test: `python -m pytest tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary -q`
- Red test: `python -m pytest tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q`
- Focused green: `python -m pytest tests\test_strategy_research_digest.py tests\test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary tests\test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q`
