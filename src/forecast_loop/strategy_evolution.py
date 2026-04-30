from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from forecast_loop.models import PaperShadowOutcome, ResearchAgenda, StrategyCard
from forecast_loop.storage import ArtifactRepository
from forecast_loop.strategy_research import REVISION_REQUIRED_ACTIONS


REVISION_AUTHOR = "codex-strategy-evolution"
REVISION_DECISION_BASIS = "paper_shadow_strategy_revision_candidate"
REVISION_AGENDA_BASIS = "paper_shadow_strategy_revision_agenda"
REPLACEMENT_AUTHOR = "codex-strategy-evolution"
REPLACEMENT_DECISION_BASIS = "lineage_replacement_strategy_hypothesis"


@dataclass(frozen=True, slots=True)
class StrategyRevisionResult:
    strategy_card: StrategyCard
    research_agenda: ResearchAgenda


@dataclass(frozen=True, slots=True)
class StrategyReplacementResult:
    strategy_card: StrategyCard


def propose_strategy_revision(
    *,
    repository: ArtifactRepository,
    created_at: datetime,
    paper_shadow_outcome_id: str,
    author: str = REVISION_AUTHOR,
    revision_version: str | None = None,
) -> StrategyRevisionResult:
    outcome = _find_required(
        repository.load_paper_shadow_outcomes(),
        attr="outcome_id",
        value=paper_shadow_outcome_id,
        artifact_name="paper shadow outcome",
    )
    assert isinstance(outcome, PaperShadowOutcome)
    if outcome.recommended_strategy_action not in REVISION_REQUIRED_ACTIONS:
        raise ValueError(
            "paper shadow outcome does not require revision: "
            f"{paper_shadow_outcome_id} action={outcome.recommended_strategy_action}"
        )

    parent = _find_required(
        repository.load_strategy_cards(),
        attr="card_id",
        value=outcome.strategy_card_id,
        artifact_name="strategy card",
    )
    assert isinstance(parent, StrategyCard)
    attributions = _failure_attributions(outcome)
    existing_revision = _existing_revision_for_outcome(repository.load_strategy_cards(), parent, outcome)
    if existing_revision is not None:
        agenda = _existing_or_create_agenda(
            repository=repository,
            created_at=created_at,
            outcome=outcome,
            parent=parent,
            revision=existing_revision,
            attributions=attributions,
        )
        return StrategyRevisionResult(strategy_card=existing_revision, research_agenda=agenda)

    entry_rules, exit_rules, risk_rules, parameters = _revision_mutation(parent, outcome, attributions)
    version = revision_version or f"{parent.version}.rev1"
    hypothesis = (
        f"Revision of {parent.strategy_name}: address paper-shadow failure "
        f"{', '.join(attributions)} from {outcome.outcome_id} before any renewed promotion attempt."
    )
    card_id = StrategyCard.build_id(
        strategy_name=f"{parent.strategy_name} revision",
        strategy_family=parent.strategy_family,
        version=version,
        symbols=parent.symbols,
        hypothesis=hypothesis,
        parameters=parameters,
    )
    existing_card = _find_optional(repository.load_strategy_cards(), "card_id", card_id)
    if existing_card is None:
        revision = StrategyCard(
            card_id=card_id,
            created_at=created_at,
            strategy_name=f"{parent.strategy_name} revision",
            strategy_family=parent.strategy_family,
            version=version,
            status="DRAFT",
            symbols=list(parent.symbols),
            hypothesis=hypothesis,
            signal_description=(
                f"{parent.signal_description} Revision adds paper-shadow failure-attribution "
                "guards and must be retested before promotion."
            ).strip(),
            entry_rules=entry_rules,
            exit_rules=exit_rules,
            risk_rules=risk_rules,
            parameters=parameters,
            data_requirements=list(parent.data_requirements),
            feature_snapshot_ids=[],
            backtest_result_ids=[],
            walk_forward_validation_ids=[],
            event_edge_evaluation_ids=[],
            parent_card_id=parent.card_id,
            author=author,
            decision_basis=REVISION_DECISION_BASIS,
        )
        repository.save_strategy_card(revision)
    else:
        assert isinstance(existing_card, StrategyCard)
        revision = existing_card

    agenda = _existing_or_create_agenda(
        repository=repository,
        created_at=created_at,
        outcome=outcome,
        parent=parent,
        revision=revision,
        attributions=attributions,
    )

    return StrategyRevisionResult(strategy_card=revision, research_agenda=agenda)


def draft_replacement_strategy_hypothesis(
    *,
    repository: ArtifactRepository,
    created_at: datetime,
    root_card_id: str,
    paper_shadow_outcome_id: str,
    author: str = REPLACEMENT_AUTHOR,
) -> StrategyReplacementResult:
    outcome = _find_required(
        repository.load_paper_shadow_outcomes(),
        attr="outcome_id",
        value=paper_shadow_outcome_id,
        artifact_name="paper shadow outcome",
    )
    assert isinstance(outcome, PaperShadowOutcome)
    root = _find_required(
        repository.load_strategy_cards(),
        attr="card_id",
        value=root_card_id,
        artifact_name="strategy card",
    )
    assert isinstance(root, StrategyCard)
    existing = _existing_replacement_for_outcome(repository.load_strategy_cards(), outcome.outcome_id)
    if existing is not None:
        return StrategyReplacementResult(strategy_card=existing)

    attributions = _failure_attributions(outcome)
    strategy_name = f"Replacement for {root.strategy_name}"
    hypothesis = (
        f"Replacement hypothesis after lineage {root.card_id} was quarantined by {outcome.outcome_id}. "
        f"Do not recursively tune the failed rules; test a distinct signal stack focused on "
        f"{', '.join(attributions)}."
    )
    parameters: dict[str, object] = {
        "replacement_source_lineage_root_card_id": root.card_id,
        "replacement_source_outcome_id": outcome.outcome_id,
        "replacement_failure_attributions": attributions,
        "replacement_required_research": ["locked_backtest", "walk_forward", "paper_shadow"],
        "replacement_not_child_revision": True,
        "minimum_after_cost_edge": max(float(root.parameters.get("minimum_after_cost_edge", 0.0)), 0.015),
    }
    card_id = StrategyCard.build_id(
        strategy_name=strategy_name,
        strategy_family=root.strategy_family,
        version=f"{root.version}.replacement1",
        symbols=list(root.symbols),
        hypothesis=hypothesis,
        parameters=parameters,
    )
    existing_by_id = _find_optional(repository.load_strategy_cards(), "card_id", card_id)
    if existing_by_id is not None:
        assert isinstance(existing_by_id, StrategyCard)
        return StrategyReplacementResult(strategy_card=existing_by_id)

    replacement = StrategyCard(
        card_id=card_id,
        created_at=created_at,
        strategy_name=strategy_name,
        strategy_family=root.strategy_family,
        version=f"{root.version}.replacement1",
        status="DRAFT",
        symbols=list(root.symbols),
        hypothesis=hypothesis,
        signal_description=(
            "Research an alternative signal stack for the same symbol instead of a child revision of the "
            "quarantined lineage."
        ),
        entry_rules=[
            "Define a replacement entry signal that does not reuse the quarantined lineage as its primary trigger.",
            "Require explicit baseline-edge evidence before any simulated BUY/SELL action.",
        ],
        exit_rules=[
            "Exit the simulated hypothesis when the replacement signal loses its baseline edge.",
            "Stop the paper-shadow test if the invalidation condition tied to the source failure appears.",
        ],
        risk_rules=[
            "Keep the replacement in DRAFT until locked backtest, walk-forward, and paper-shadow evidence exist.",
            f"Prioritize mitigation of {', '.join(attributions)} before any promotion attempt.",
        ],
        parameters=parameters,
        data_requirements=list(root.data_requirements),
        feature_snapshot_ids=[],
        backtest_result_ids=[],
        walk_forward_validation_ids=[],
        event_edge_evaluation_ids=[],
        parent_card_id=None,
        author=author,
        decision_basis=REPLACEMENT_DECISION_BASIS,
    )
    repository.save_strategy_card(replacement)
    return StrategyReplacementResult(strategy_card=replacement)


def _revision_mutation(
    parent: StrategyCard,
    outcome: PaperShadowOutcome,
    attributions: list[str],
) -> tuple[list[str], list[str], list[str], dict[str, object]]:
    entry_rules = list(parent.entry_rules)
    exit_rules = list(parent.exit_rules)
    risk_rules = list(parent.risk_rules)
    parameters: dict[str, object] = dict(parent.parameters)
    parameters.update(
        {
            "revision_source_outcome_id": outcome.outcome_id,
            "revision_failure_attributions": attributions,
            "revision_requires_locked_retest": True,
        }
    )

    for attribution in attributions:
        if attribution == "negative_excess_return":
            entry_rules.append(
                "Require positive after-cost edge versus the active baseline suite before simulated entry."
            )
            risk_rules.append("Block promotion until the revised card beats no-trade and persistence baselines.")
            parameters["minimum_after_cost_edge"] = max(float(parameters.get("minimum_after_cost_edge", 0.0)), 0.01)
        elif attribution == "adverse_excursion_breach":
            risk_rules.append(
                "Cut simulated max position by 50% until paper-shadow adverse excursion returns inside limits."
            )
            parameters["max_position_multiplier"] = min(float(parameters.get("max_position_multiplier", 1.0)), 0.5)
        elif attribution == "turnover_breach":
            exit_rules.append("Avoid flip-flop exits unless the adverse signal persists for the cooldown window.")
            risk_rules.append("Apply a cooldown between simulated entries to reduce churn and turnover.")
            parameters["cooldown_hours"] = max(int(parameters.get("cooldown_hours", 0)), 6)
        else:
            entry_rules.append(f"Isolate failure attribution '{attribution}' in the next locked research trial.")

    return _unique(entry_rules), _unique(exit_rules), _unique(risk_rules), parameters


def _build_revision_agenda(
    *,
    created_at: datetime,
    outcome: PaperShadowOutcome,
    parent: StrategyCard,
    revision: StrategyCard,
    attributions: list[str],
) -> ResearchAgenda:
    title = f"Revision test for {parent.strategy_name}"
    hypothesis = (
        f"Revision candidate {revision.card_id} should repair paper-shadow failure "
        f"{', '.join(attributions)} from {outcome.outcome_id} without weakening baseline edge."
    )
    return ResearchAgenda(
        agenda_id=ResearchAgenda.build_id(
            symbol=outcome.symbol,
            title=title,
            hypothesis=hypothesis,
            target_strategy_family=parent.strategy_family,
            strategy_card_ids=[revision.card_id],
        ),
        created_at=created_at,
        symbol=outcome.symbol,
        title=title,
        hypothesis=hypothesis,
        priority="HIGH",
        status="OPEN",
        target_strategy_family=parent.strategy_family,
        strategy_card_ids=[revision.card_id],
        expected_artifacts=[
            "strategy_card",
            "experiment_trial",
            "locked_evaluation",
            "leaderboard_entry",
            "paper_shadow_outcome",
        ],
        acceptance_criteria=[
            "revision card stays DRAFT until new locked evaluation passes",
            "paper-shadow failure attribution is explicitly tested",
            "revised card beats active baselines after costs",
        ],
        blocked_actions=["real_order_submission", "automatic_promotion_without_retest"],
        decision_basis=REVISION_AGENDA_BASIS,
    )


def _existing_or_create_agenda(
    *,
    repository: ArtifactRepository,
    created_at: datetime,
    outcome: PaperShadowOutcome,
    parent: StrategyCard,
    revision: StrategyCard,
    attributions: list[str],
) -> ResearchAgenda:
    existing = _existing_agenda_for_revision(repository.load_research_agendas(), revision)
    if existing is not None:
        return existing
    agenda = _build_revision_agenda(
        created_at=created_at,
        outcome=outcome,
        parent=parent,
        revision=revision,
        attributions=attributions,
    )
    repository.save_research_agenda(agenda)
    return agenda


def _existing_revision_for_outcome(
    cards: list[StrategyCard],
    parent: StrategyCard,
    outcome: PaperShadowOutcome,
) -> StrategyCard | None:
    return next(
        (
            card
            for card in cards
            if card.parent_card_id == parent.card_id
            and card.decision_basis == REVISION_DECISION_BASIS
            and card.parameters.get("revision_source_outcome_id") == outcome.outcome_id
        ),
        None,
    )


def _existing_agenda_for_revision(agendas: list[ResearchAgenda], revision: StrategyCard) -> ResearchAgenda | None:
    return next(
        (
            agenda
            for agenda in agendas
            if agenda.decision_basis == REVISION_AGENDA_BASIS and agenda.strategy_card_ids == [revision.card_id]
        ),
        None,
    )


def _existing_replacement_for_outcome(cards: list[StrategyCard], outcome_id: str) -> StrategyCard | None:
    return next(
        (
            card
            for card in cards
            if card.decision_basis == REPLACEMENT_DECISION_BASIS
            and card.parameters.get("replacement_source_outcome_id") == outcome_id
        ),
        None,
    )


def _failure_attributions(outcome: PaperShadowOutcome) -> list[str]:
    items = outcome.failure_attributions or outcome.blocked_reasons or [outcome.outcome_grade.lower()]
    return _unique(items)


def _find_required(items: list[object], *, attr: str, value: str, artifact_name: str) -> object:
    item = _find_optional(items, attr, value)
    if item is None:
        raise ValueError(f"missing {artifact_name}: {value}")
    return item


def _find_optional(items: list[object], attr: str, value: str) -> object | None:
    return next((item for item in items if getattr(item, attr) == value), None)


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item and item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered
