from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from forecast_loop.models import PaperShadowOutcome, StrategyCard


REPLACEMENT_DECISION_BASIS = "lineage_replacement_strategy_hypothesis"
QUARANTINE_ACTIONS = {"QUARANTINE", "QUARANTINE_STRATEGY"}
REVISION_ACTIONS = {"REVISE", "REVISE_STRATEGY"}


@dataclass(frozen=True, slots=True)
class StrategyLineageRevisionNode:
    card_id: str
    parent_card_id: str
    depth: int
    strategy_name: str
    status: str
    hypothesis: str
    source_outcome_id: str | None
    failure_attributions: list[str]


@dataclass(frozen=True, slots=True)
class StrategyLineageOutcomeNode:
    outcome_id: str
    strategy_card_id: str
    excess_return_after_costs: float | None
    delta_vs_previous_excess: float | None
    change_label: str
    recommended_strategy_action: str
    failure_attributions: list[str]


@dataclass(frozen=True, slots=True)
class StrategyLineageReplacementNode:
    card_id: str
    strategy_name: str
    status: str
    hypothesis: str
    source_root_card_id: str
    source_outcome_id: str | None
    failure_attributions: list[str]
    latest_outcome_id: str | None
    latest_recommended_strategy_action: str | None
    latest_excess_return_after_costs: float | None


@dataclass(frozen=True, slots=True)
class StrategyLineageSummary:
    root_card_id: str
    revision_card_ids: list[str]
    revision_nodes: list[StrategyLineageRevisionNode]
    replacement_card_ids: list[str]
    replacement_nodes: list[StrategyLineageReplacementNode]
    outcome_nodes: list[StrategyLineageOutcomeNode]
    revision_count: int
    replacement_count: int
    outcome_count: int
    action_counts: dict[str, int]
    failure_attribution_counts: dict[str, int]
    best_excess_return_after_costs: float | None
    worst_excess_return_after_costs: float | None
    latest_outcome_id: str | None
    performance_verdict: str
    improved_outcome_count: int
    worsened_outcome_count: int
    unknown_outcome_count: int
    latest_change_label: str
    latest_delta_vs_previous_excess: float | None
    primary_failure_attribution: str | None
    latest_recommended_strategy_action: str | None
    next_research_focus: str


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
    replacement_cards = _lineage_replacement_cards(root_card, strategy_cards)
    lineage_card_ids = {
        root_card.card_id,
        *(card.card_id for card in revision_cards),
        *(card.card_id for card in replacement_cards),
    }
    lineage_outcomes = sorted(
        [outcome for outcome in paper_shadow_outcomes if outcome.strategy_card_id in lineage_card_ids],
        key=lambda outcome: (outcome.created_at, outcome.outcome_id),
    )
    outcome_nodes = _lineage_outcome_nodes(lineage_outcomes)
    replacement_nodes = _lineage_replacement_nodes(root_card, replacement_cards, lineage_outcomes)
    excess_returns = [
        outcome.excess_return_after_costs
        for outcome in lineage_outcomes
        if outcome.excess_return_after_costs is not None
    ]
    action_counts = dict(sorted(Counter(outcome.recommended_strategy_action for outcome in lineage_outcomes).items()))
    failure_attribution_counts = dict(
        sorted(
            Counter(
                attribution
                for outcome in lineage_outcomes
                for attribution in _outcome_failure_references(outcome)
            ).items()
        )
    )
    verdict = _lineage_performance_verdict(outcome_nodes, failure_attribution_counts)

    return StrategyLineageSummary(
        root_card_id=root_card.card_id,
        revision_card_ids=[card.card_id for card in revision_cards],
        revision_nodes=revision_nodes,
        replacement_card_ids=[card.card_id for card in replacement_cards],
        replacement_nodes=replacement_nodes,
        outcome_nodes=outcome_nodes,
        revision_count=len(revision_cards),
        replacement_count=len(replacement_cards),
        outcome_count=len(lineage_outcomes),
        action_counts=action_counts,
        failure_attribution_counts=failure_attribution_counts,
        best_excess_return_after_costs=max(excess_returns) if excess_returns else None,
        worst_excess_return_after_costs=min(excess_returns) if excess_returns else None,
        latest_outcome_id=lineage_outcomes[-1].outcome_id if lineage_outcomes else None,
        performance_verdict=verdict["performance_verdict"],
        improved_outcome_count=verdict["improved_outcome_count"],
        worsened_outcome_count=verdict["worsened_outcome_count"],
        unknown_outcome_count=verdict["unknown_outcome_count"],
        latest_change_label=verdict["latest_change_label"],
        latest_delta_vs_previous_excess=verdict["latest_delta_vs_previous_excess"],
        primary_failure_attribution=verdict["primary_failure_attribution"],
        latest_recommended_strategy_action=verdict["latest_recommended_strategy_action"],
        next_research_focus=verdict["next_research_focus"],
    )


def _lineage_root_card(card: StrategyCard, strategy_cards: list[StrategyCard]) -> StrategyCard:
    parent_by_id = {candidate.card_id: candidate for candidate in strategy_cards}
    replacement_root_id = _string_parameter(card, "replacement_source_lineage_root_card_id")
    if card.decision_basis == REPLACEMENT_DECISION_BASIS and replacement_root_id in parent_by_id:
        return parent_by_id[replacement_root_id]
    current = card
    visited = {card.card_id}
    while current.parent_card_id is not None:
        parent = parent_by_id.get(current.parent_card_id)
        if parent is None:
            return current
        if parent.card_id in visited:
            return card
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
                strategy_name=card.strategy_name,
                status=card.status,
                hypothesis=card.hypothesis,
                source_outcome_id=_string_parameter(card, "revision_source_outcome_id"),
                failure_attributions=_string_list_parameter(card, "revision_failure_attributions"),
            )
        )
        stack.extend((child, depth + 1) for child in reversed(children_by_parent.get(card.card_id, [])))
    return revision_cards, revision_nodes


def _lineage_replacement_cards(
    root_card: StrategyCard,
    strategy_cards: list[StrategyCard],
) -> list[StrategyCard]:
    replacements = [
        card
        for card in strategy_cards
        if card.card_id != root_card.card_id
        and card.decision_basis == REPLACEMENT_DECISION_BASIS
        and _string_parameter(card, "replacement_source_lineage_root_card_id") == root_card.card_id
    ]
    return sorted(replacements, key=lambda card: (card.created_at, card.card_id))


def _lineage_replacement_nodes(
    root_card: StrategyCard,
    replacement_cards: list[StrategyCard],
    lineage_outcomes: list[PaperShadowOutcome],
) -> list[StrategyLineageReplacementNode]:
    outcomes_by_card_id: dict[str, list[PaperShadowOutcome]] = {}
    for outcome in lineage_outcomes:
        outcomes_by_card_id.setdefault(outcome.strategy_card_id, []).append(outcome)

    nodes: list[StrategyLineageReplacementNode] = []
    for card in replacement_cards:
        latest_outcome = _latest_outcome(outcomes_by_card_id.get(card.card_id, []))
        nodes.append(
            StrategyLineageReplacementNode(
                card_id=card.card_id,
                strategy_name=card.strategy_name,
                status=card.status,
                hypothesis=card.hypothesis,
                source_root_card_id=root_card.card_id,
                source_outcome_id=_string_parameter(card, "replacement_source_outcome_id"),
                failure_attributions=_string_list_parameter(card, "replacement_failure_attributions"),
                latest_outcome_id=latest_outcome.outcome_id if latest_outcome else None,
                latest_recommended_strategy_action=(
                    latest_outcome.recommended_strategy_action if latest_outcome else None
                ),
                latest_excess_return_after_costs=(
                    latest_outcome.excess_return_after_costs if latest_outcome else None
                ),
            )
        )
    return nodes


def _latest_outcome(outcomes: list[PaperShadowOutcome]) -> PaperShadowOutcome | None:
    if not outcomes:
        return None
    return max(outcomes, key=lambda outcome: (outcome.created_at, outcome.outcome_id))


def _string_parameter(card: StrategyCard, key: str) -> str | None:
    value = card.parameters.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def _string_list_parameter(card: StrategyCard, key: str) -> list[str]:
    value = card.parameters.get(key)
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str) and value:
        return [value]
    return []


def _lineage_outcome_nodes(paper_shadow_outcomes: list[PaperShadowOutcome]) -> list[StrategyLineageOutcomeNode]:
    nodes: list[StrategyLineageOutcomeNode] = []
    previous_excess: float | None = None
    for outcome in paper_shadow_outcomes:
        current_excess = outcome.excess_return_after_costs
        delta = _delta(current_excess, previous_excess)
        nodes.append(
            StrategyLineageOutcomeNode(
                outcome_id=outcome.outcome_id,
                strategy_card_id=outcome.strategy_card_id,
                excess_return_after_costs=current_excess,
                delta_vs_previous_excess=delta,
                change_label=_change_label(delta, baseline=current_excess is not None and previous_excess is None),
                recommended_strategy_action=outcome.recommended_strategy_action,
                failure_attributions=_outcome_failure_references(outcome),
            )
        )
        if current_excess is not None:
            previous_excess = current_excess
    return nodes


def _outcome_failure_references(outcome: PaperShadowOutcome) -> list[str]:
    return _unique_strings(list(outcome.failure_attributions or outcome.blocked_reasons))


def _unique_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item and item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered


def _lineage_performance_verdict(
    outcome_nodes: list[StrategyLineageOutcomeNode],
    failure_attribution_counts: dict[str, int],
) -> dict[str, object]:
    improved = sum(1 for node in outcome_nodes if node.change_label == "改善")
    worsened = sum(1 for node in outcome_nodes if node.change_label == "惡化")
    unknown = sum(1 for node in outcome_nodes if node.change_label == "未知")
    latest = outcome_nodes[-1] if outcome_nodes else None
    primary_failure = _latest_or_primary_failure_attribution(latest, failure_attribution_counts)
    performance_verdict = _performance_verdict_label(outcome_nodes, improved, worsened, unknown, latest)
    latest_action = latest.recommended_strategy_action if latest else None
    return {
        "performance_verdict": performance_verdict,
        "improved_outcome_count": improved,
        "worsened_outcome_count": worsened,
        "unknown_outcome_count": unknown,
        "latest_change_label": latest.change_label if latest else "證據不足",
        "latest_delta_vs_previous_excess": latest.delta_vs_previous_excess if latest else None,
        "primary_failure_attribution": primary_failure,
        "latest_recommended_strategy_action": latest_action,
        "next_research_focus": _next_research_focus(performance_verdict, latest_action, primary_failure),
    }


def _performance_verdict_label(
    outcome_nodes: list[StrategyLineageOutcomeNode],
    improved: int,
    worsened: int,
    unknown: int,
    latest: StrategyLineageOutcomeNode | None,
) -> str:
    if not outcome_nodes or unknown == len(outcome_nodes):
        return "證據不足"
    if latest and latest.change_label in {"改善", "惡化", "持平"}:
        return latest.change_label
    if worsened > improved:
        return "偏弱"
    if improved > worsened:
        return "偏強"
    return "觀察中"


def _latest_or_primary_failure_attribution(
    latest: StrategyLineageOutcomeNode | None,
    failure_attribution_counts: dict[str, int],
) -> str | None:
    if latest and latest.failure_attributions:
        return latest.failure_attributions[0]
    if failure_attribution_counts:
        return max(failure_attribution_counts.items(), key=lambda item: (item[1], item[0]))[0]
    return None


def _next_research_focus(
    performance_verdict: str,
    latest_recommended_strategy_action: str | None,
    primary_failure_attribution: str | None,
) -> str:
    failure = primary_failure_attribution or "主要失敗"
    if performance_verdict == "證據不足":
        return "先補齊 paper-shadow outcome 證據，再判斷修正方向。"
    if latest_recommended_strategy_action in QUARANTINE_ACTIONS:
        return f"停止加碼此 lineage，優先研究 {failure} 的修正或新策略。"
    if latest_recommended_strategy_action in REVISION_ACTIONS or performance_verdict in {"惡化", "偏弱"}:
        return f"優先修正 {failure}，再重跑 locked retest。"
    if performance_verdict in {"改善", "偏強"}:
        return "保留此 lineage，下一步驗證改善是否能跨樣本持續。"
    return "維持觀察，等待更多 paper-shadow outcome。"


def _delta(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return round(current - previous, 10)


def _change_label(delta: float | None, *, baseline: bool) -> str:
    if baseline:
        return "基準"
    if delta is None:
        return "未知"
    if delta > 0:
        return "改善"
    if delta < 0:
        return "惡化"
    return "持平"
