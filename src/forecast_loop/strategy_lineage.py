from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from forecast_loop.models import PaperShadowOutcome, StrategyCard


@dataclass(frozen=True, slots=True)
class StrategyLineageRevisionNode:
    card_id: str
    parent_card_id: str
    depth: int


@dataclass(frozen=True, slots=True)
class StrategyLineageSummary:
    root_card_id: str
    revision_card_ids: list[str]
    revision_nodes: list[StrategyLineageRevisionNode]
    revision_count: int
    outcome_count: int
    action_counts: dict[str, int]
    failure_attribution_counts: dict[str, int]
    best_excess_return_after_costs: float | None
    worst_excess_return_after_costs: float | None
    latest_outcome_id: str | None


def build_strategy_lineage_summary(
    *,
    root_card: StrategyCard | None,
    strategy_cards: list[StrategyCard],
    paper_shadow_outcomes: list[PaperShadowOutcome],
) -> StrategyLineageSummary | None:
    if root_card is None:
        return None

    root_card = _lineage_root_card(root_card, strategy_cards)
    revision_cards, revision_nodes = _lineage_revision_tree(root_card, strategy_cards)
    lineage_card_ids = {root_card.card_id, *(card.card_id for card in revision_cards)}
    lineage_outcomes = sorted(
        [outcome for outcome in paper_shadow_outcomes if outcome.strategy_card_id in lineage_card_ids],
        key=lambda outcome: (outcome.created_at, outcome.outcome_id),
    )
    excess_returns = [
        outcome.excess_return_after_costs
        for outcome in lineage_outcomes
        if outcome.excess_return_after_costs is not None
    ]

    return StrategyLineageSummary(
        root_card_id=root_card.card_id,
        revision_card_ids=[card.card_id for card in revision_cards],
        revision_nodes=revision_nodes,
        revision_count=len(revision_cards),
        outcome_count=len(lineage_outcomes),
        action_counts=dict(sorted(Counter(outcome.recommended_strategy_action for outcome in lineage_outcomes).items())),
        failure_attribution_counts=dict(
            sorted(
                Counter(
                    attribution
                    for outcome in lineage_outcomes
                    for attribution in outcome.failure_attributions
                ).items()
            )
        ),
        best_excess_return_after_costs=max(excess_returns) if excess_returns else None,
        worst_excess_return_after_costs=min(excess_returns) if excess_returns else None,
        latest_outcome_id=lineage_outcomes[-1].outcome_id if lineage_outcomes else None,
    )


def _lineage_root_card(card: StrategyCard, strategy_cards: list[StrategyCard]) -> StrategyCard:
    parent_by_id = {candidate.card_id: candidate for candidate in strategy_cards}
    current = card
    visited = {card.card_id}
    while current.parent_card_id is not None:
        parent = parent_by_id.get(current.parent_card_id)
        if parent is None or parent.card_id in visited:
            return current
        current = parent
        visited.add(current.card_id)
    return current


def _lineage_revision_tree(
    root_card: StrategyCard,
    strategy_cards: list[StrategyCard],
) -> tuple[list[StrategyCard], list[StrategyLineageRevisionNode]]:
    children_by_parent: dict[str, list[StrategyCard]] = {}
    for card in strategy_cards:
        if card.card_id == root_card.card_id or card.parent_card_id is None:
            continue
        children_by_parent.setdefault(card.parent_card_id, []).append(card)

    for children in children_by_parent.values():
        children.sort(key=lambda card: (card.created_at, card.card_id))

    revision_cards: list[StrategyCard] = []
    revision_nodes: list[StrategyLineageRevisionNode] = []
    visited = {root_card.card_id}
    stack = [(card, 1) for card in reversed(children_by_parent.get(root_card.card_id, []))]
    while stack:
        card, depth = stack.pop()
        if card.card_id in visited:
            continue
        visited.add(card.card_id)
        revision_cards.append(card)
        revision_nodes.append(
            StrategyLineageRevisionNode(
                card_id=card.card_id,
                parent_card_id=card.parent_card_id or root_card.card_id,
                depth=depth,
            )
        )
        stack.extend((child, depth + 1) for child in reversed(children_by_parent.get(card.card_id, [])))
    return revision_cards, revision_nodes
