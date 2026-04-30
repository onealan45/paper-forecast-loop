# PR60: Cross-Sample Agenda Replacement Links

## Context

PR58 created `lineage_cross_sample_validation_agenda` artifacts after an
improving lineage or replacement retest. PR59 made those agendas visible in the
dashboard and operator console. The remaining traceability issue was that an
improving replacement card appeared in the agenda hypothesis text but not in
`strategy_card_ids`.

Natural-language prompts are useful for humans, but downstream research tools
should not have to parse prompt text to identify the strategy hypothesis being
validated.

## Decision

When `verify_cross_sample_persistence` executes, the agenda now builds
`strategy_card_ids` from:

- the lineage root card id
- the latest outcome's strategy card id, only when that card is a
  `lineage_replacement_strategy_hypothesis` linked back to the same root

If the latest outcome is not from a root-linked replacement card, the agenda
keeps only the root card id.

## Impact

This keeps the agenda compatible with existing lineage lookup, because the root
card remains present. It also makes the exact improving replacement hypothesis a
structured artifact link for future fresh-sample validation, reporting, and
research automation.

## Verification

- `python -m pytest tests\test_lineage_research_executor.py::test_execute_lineage_research_next_task_creates_cross_sample_validation_agenda -q`
- `python -m pytest tests\test_lineage_research_executor.py tests\test_lineage_research_plan.py -q`

