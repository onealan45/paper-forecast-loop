# PR162 Decision Agenda Does Not Mask Strategy

## Problem

Decision-blocker research agendas can have `strategy_card_ids=[]` because they
anchor a blocked strategy decision rather than owning a strategy-card lineage.
When such an agenda became the newest research artifact, the strategy digest
resolver could treat it as the latest strategy anchor and return
`no_strategy_card`.

That made the UX look as if the system had no current strategy even though an
active replacement retest strategy and lineage still existed.

## Decision

`resolve_latest_strategy_research_chain()` now lets research agendas participate
as strategy anchors only when they name at least one `strategy_card_id`.

Empty decision-blocker agendas remain useful decision/research evidence, but
they do not own or replace the current strategy slot. The digest can still link
the latest decision and blocker context separately.

If the storage has no strategy/evidence anchors at all, an empty agenda can
still represent the agenda-only state. This preserves the pre-strategy UX where
operators can see the first research agenda before any strategy card exists.

## Acceptance

- A newer empty decision-blocker agenda does not hide the current strategy card.
- A newer agenda that explicitly names a strategy card still can anchor that
  card's strategy context.
- An agenda-only storage with no strategy cards still displays the agenda-only
  state.
- Existing same-card retest and agenda anchor behavior remains covered.

## Verification

- `python -m pytest tests\test_strategy_research_digest.py::test_strategy_research_digest_does_not_let_empty_decision_agenda_mask_current_strategy -q`
- `python -m pytest tests\test_dashboard.py::test_dashboard_strategy_research_panel_shows_agenda_only_state -q`
- `python -m pytest tests\test_strategy_research_digest.py::test_strategy_research_digest_keeps_card_shadow_outcome_when_decision_agenda_is_newer tests\test_strategy_research_digest.py::test_strategy_research_digest_does_not_mask_newer_same_card_retest_waiting_for_shadow -q`
- `python -m pytest tests\test_strategy_research_digest.py -q`
