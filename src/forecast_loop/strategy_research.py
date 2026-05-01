from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from forecast_loop.models import (
    ExperimentTrial,
    LeaderboardEntry,
    LockedEvaluationResult,
    PaperShadowOutcome,
    ResearchAgenda,
    ResearchAutopilotRun,
    SplitManifest,
    StrategyCard,
)


REVISION_CARD_BASIS = "paper_shadow_strategy_revision_candidate"
REVISION_AGENDA_BASIS = "paper_shadow_strategy_revision_agenda"
REVISION_REQUIRED_ACTIONS = {"RETIRE", "REVISE", "REVISE_STRATEGY", "QUARANTINE"}


@dataclass(slots=True)
class StrategyRevisionCandidate:
    strategy_card: StrategyCard
    research_agenda: ResearchAgenda | None
    source_outcome: PaperShadowOutcome | None
    retest_trial: ExperimentTrial | None
    retest_split_manifest: SplitManifest | None
    retest_next_required_artifacts: list[str]


@dataclass(slots=True)
class StrategyResearchChain:
    strategy_card: StrategyCard | None
    experiment_trial: ExperimentTrial | None
    locked_evaluation: LockedEvaluationResult | None
    leaderboard_entry: LeaderboardEntry | None
    paper_shadow_outcome: PaperShadowOutcome | None
    research_agenda: ResearchAgenda | None
    research_autopilot_run: ResearchAutopilotRun | None
    revision_candidate: StrategyRevisionCandidate | None


def resolve_latest_strategy_research_chain(
    *,
    symbol: str,
    strategy_cards: list[StrategyCard],
    experiment_trials: list[ExperimentTrial],
    locked_evaluations: list[LockedEvaluationResult],
    split_manifests: list[SplitManifest],
    leaderboard_entries: list[LeaderboardEntry],
    paper_shadow_outcomes: list[PaperShadowOutcome],
    research_agendas: list[ResearchAgenda],
    research_autopilot_runs: list[ResearchAutopilotRun],
) -> StrategyResearchChain:
    cards = [item for item in strategy_cards if symbol in item.symbols]
    trials = [item for item in experiment_trials if item.symbol == symbol]
    entries = [item for item in leaderboard_entries if item.symbol == symbol]
    outcomes = [item for item in paper_shadow_outcomes if item.symbol == symbol]
    agendas = [item for item in research_agendas if item.symbol == symbol]
    runs = [item for item in research_autopilot_runs if item.symbol == symbol]
    card_ids = {item.card_id for item in cards}
    trial_ids = {item.trial_id for item in trials}
    evaluations = [
        item
        for item in locked_evaluations
        if item.strategy_card_id in card_ids or item.trial_id in trial_ids
    ]

    card_by_id = {item.card_id: item for item in cards}
    trial_by_id = {item.trial_id: item for item in trials}
    evaluation_by_id = {item.evaluation_id: item for item in evaluations}
    entry_by_id = {item.entry_id: item for item in entries}
    outcome_by_id = {item.outcome_id: item for item in outcomes}
    agenda_by_id = {item.agenda_id: item for item in agendas}
    revision_candidate = _latest_revision_candidate(
        cards,
        outcome_by_id,
        agendas,
        trials,
        split_manifests,
        locked_evaluations,
        entries,
        outcomes,
    )

    latest_run = _latest(runs)
    if latest_run is not None:
        chain = _chain_from_ids(
            symbol=symbol,
            strategy_card_id=latest_run.strategy_card_id,
            experiment_trial_id=latest_run.experiment_trial_id,
            locked_evaluation_id=latest_run.locked_evaluation_id,
            leaderboard_entry_id=latest_run.leaderboard_entry_id,
            paper_shadow_outcome_id=latest_run.paper_shadow_outcome_id,
            agenda_id=latest_run.agenda_id,
            research_autopilot_run=latest_run,
            card_by_id=card_by_id,
            trial_by_id=trial_by_id,
            evaluation_by_id=evaluation_by_id,
            entry_by_id=entry_by_id,
            outcome_by_id=outcome_by_id,
            agenda_by_id=agenda_by_id,
            agendas=agendas,
        )
        chain.revision_candidate = revision_candidate
        return chain

    latest_anchor = _latest_anchor(cards, trials, evaluations, entries, outcomes, agendas)
    if latest_anchor is None:
        return StrategyResearchChain(None, None, None, None, None, None, None, revision_candidate)

    kind, anchor = latest_anchor
    if kind == "outcome":
        outcome = anchor
        assert isinstance(outcome, PaperShadowOutcome)
        chain = _chain_from_ids(
            symbol=symbol,
            strategy_card_id=outcome.strategy_card_id,
            experiment_trial_id=outcome.trial_id,
            locked_evaluation_id=outcome.evaluation_id,
            leaderboard_entry_id=outcome.leaderboard_entry_id,
            paper_shadow_outcome_id=outcome.outcome_id,
            agenda_id=None,
            research_autopilot_run=None,
            card_by_id=card_by_id,
            trial_by_id=trial_by_id,
            evaluation_by_id=evaluation_by_id,
            entry_by_id=entry_by_id,
            outcome_by_id=outcome_by_id,
            agenda_by_id=agenda_by_id,
            agendas=agendas,
        )
        chain.revision_candidate = revision_candidate
        return chain
    if kind == "entry":
        entry = anchor
        assert isinstance(entry, LeaderboardEntry)
        chain = _chain_from_ids(
            symbol=symbol,
            strategy_card_id=entry.strategy_card_id,
            experiment_trial_id=entry.trial_id,
            locked_evaluation_id=entry.evaluation_id,
            leaderboard_entry_id=entry.entry_id,
            paper_shadow_outcome_id=None,
            agenda_id=None,
            research_autopilot_run=None,
            card_by_id=card_by_id,
            trial_by_id=trial_by_id,
            evaluation_by_id=evaluation_by_id,
            entry_by_id=entry_by_id,
            outcome_by_id=outcome_by_id,
            agenda_by_id=agenda_by_id,
            agendas=agendas,
        )
        chain.revision_candidate = revision_candidate
        return chain
    if kind == "evaluation":
        evaluation = anchor
        assert isinstance(evaluation, LockedEvaluationResult)
        chain = _chain_from_ids(
            symbol=symbol,
            strategy_card_id=evaluation.strategy_card_id,
            experiment_trial_id=evaluation.trial_id,
            locked_evaluation_id=evaluation.evaluation_id,
            leaderboard_entry_id=None,
            paper_shadow_outcome_id=None,
            agenda_id=None,
            research_autopilot_run=None,
            card_by_id=card_by_id,
            trial_by_id=trial_by_id,
            evaluation_by_id=evaluation_by_id,
            entry_by_id=entry_by_id,
            outcome_by_id=outcome_by_id,
            agenda_by_id=agenda_by_id,
            agendas=agendas,
        )
        chain.revision_candidate = revision_candidate
        return chain
    if kind == "trial":
        trial = anchor
        assert isinstance(trial, ExperimentTrial)
        chain = _chain_from_ids(
            symbol=symbol,
            strategy_card_id=trial.strategy_card_id,
            experiment_trial_id=trial.trial_id,
            locked_evaluation_id=None,
            leaderboard_entry_id=None,
            paper_shadow_outcome_id=None,
            agenda_id=None,
            research_autopilot_run=None,
            card_by_id=card_by_id,
            trial_by_id=trial_by_id,
            evaluation_by_id=evaluation_by_id,
            entry_by_id=entry_by_id,
            outcome_by_id=outcome_by_id,
            agenda_by_id=agenda_by_id,
            agendas=agendas,
        )
        chain.revision_candidate = revision_candidate
        return chain
    if kind == "agenda":
        agenda = anchor
        assert isinstance(agenda, ResearchAgenda)
        card = _latest([card_by_id[item] for item in agenda.strategy_card_ids if item in card_by_id])
        return StrategyResearchChain(card, None, None, None, None, agenda, None, revision_candidate)

    card = anchor
    assert isinstance(card, StrategyCard)
    return StrategyResearchChain(
        card,
        None,
        None,
        None,
        None,
        _latest_agenda_for_card(agendas, card.card_id),
        None,
        revision_candidate,
    )


def _chain_from_ids(
    *,
    symbol: str,
    strategy_card_id: str,
    experiment_trial_id: str | None,
    locked_evaluation_id: str | None,
    leaderboard_entry_id: str | None,
    paper_shadow_outcome_id: str | None,
    agenda_id: str | None,
    research_autopilot_run: ResearchAutopilotRun | None,
    card_by_id: dict[str, StrategyCard],
    trial_by_id: dict[str, ExperimentTrial],
    evaluation_by_id: dict[str, LockedEvaluationResult],
    entry_by_id: dict[str, LeaderboardEntry],
    outcome_by_id: dict[str, PaperShadowOutcome],
    agenda_by_id: dict[str, ResearchAgenda],
    agendas: list[ResearchAgenda],
) -> StrategyResearchChain:
    card = _valid_card(card_by_id.get(strategy_card_id), symbol)
    trial = _valid_trial(trial_by_id.get(experiment_trial_id or ""), symbol, strategy_card_id)
    evaluation = _valid_evaluation(
        evaluation_by_id.get(locked_evaluation_id or ""),
        strategy_card_id=strategy_card_id,
        trial_id=experiment_trial_id,
    )
    entry = _valid_entry(
        entry_by_id.get(leaderboard_entry_id or ""),
        symbol=symbol,
        strategy_card_id=strategy_card_id,
        trial_id=experiment_trial_id,
        evaluation_id=locked_evaluation_id,
    )
    outcome = _valid_outcome(
        outcome_by_id.get(paper_shadow_outcome_id or ""),
        symbol=symbol,
        strategy_card_id=strategy_card_id,
        trial_id=experiment_trial_id,
        evaluation_id=locked_evaluation_id,
        leaderboard_entry_id=leaderboard_entry_id,
    )
    agenda = _valid_agenda(agenda_by_id.get(agenda_id or ""), symbol, strategy_card_id)
    if agenda is None:
        agenda = _latest_agenda_for_card(agendas, strategy_card_id)
    return StrategyResearchChain(card, trial, evaluation, entry, outcome, agenda, research_autopilot_run, None)


def _latest_revision_candidate(
    cards: list[StrategyCard],
    outcome_by_id: dict[str, PaperShadowOutcome],
    agendas: list[ResearchAgenda],
    trials: list[ExperimentTrial],
    split_manifests: list[SplitManifest],
    locked_evaluations: list[LockedEvaluationResult],
    leaderboard_entries: list[LeaderboardEntry],
    paper_shadow_outcomes: list[PaperShadowOutcome],
) -> StrategyRevisionCandidate | None:
    revision_cards = [
        card
        for card in cards
        if card.status == "DRAFT"
        and card.decision_basis == REVISION_CARD_BASIS
        and isinstance(card.parameters.get("revision_source_outcome_id"), str)
    ]
    revision = _latest(revision_cards)
    if revision is None:
        return None
    source_outcome_id = str(revision.parameters["revision_source_outcome_id"])
    source_outcome = outcome_by_id.get(source_outcome_id)
    revision_agendas = [
        agenda
        for agenda in agendas
        if revision.card_id in agenda.strategy_card_ids and agenda.decision_basis == REVISION_AGENDA_BASIS
    ]
    agenda = _latest(revision_agendas)
    retest_trial = _latest_revision_retest_trial(trials, revision)
    retest_split = _latest_revision_split_manifest(split_manifests, revision, retest_trial)
    return StrategyRevisionCandidate(
        strategy_card=revision,
        research_agenda=agenda,
        source_outcome=source_outcome,
        retest_trial=retest_trial,
        retest_split_manifest=retest_split,
        retest_next_required_artifacts=_revision_retest_next_required_artifacts(
            retest_trial,
            retest_split,
            locked_evaluations,
            leaderboard_entries,
            paper_shadow_outcomes,
        ),
    )


def _latest_revision_retest_trial(
    trials: list[ExperimentTrial],
    revision: StrategyCard,
) -> ExperimentTrial | None:
    candidates = [
        trial
        for trial in trials
        if trial.strategy_card_id == revision.card_id
        and trial.status in {"PENDING", "PASSED"}
        and trial.parameters.get("revision_retest_protocol") == "pr14-v1"
        and trial.parameters.get("revision_retest_source_card_id") == revision.card_id
        and trial.parameters.get("revision_source_outcome_id") == revision.parameters.get("revision_source_outcome_id")
    ]
    return _latest(candidates)


def _latest_revision_split_manifest(
    split_manifests: list[SplitManifest],
    revision: StrategyCard,
    retest_trial: ExperimentTrial | None,
) -> SplitManifest | None:
    if retest_trial is None or retest_trial.dataset_id is None:
        return None
    candidates = [
        manifest
        for manifest in split_manifests
        if manifest.strategy_card_id == revision.card_id
        and manifest.dataset_id == retest_trial.dataset_id
        and manifest.symbol == retest_trial.symbol
        and manifest.status == "LOCKED"
    ]
    return _latest(candidates)


def _revision_retest_next_required_artifacts(
    retest_trial: ExperimentTrial | None,
    retest_split: SplitManifest | None,
    locked_evaluations: list[LockedEvaluationResult],
    leaderboard_entries: list[LeaderboardEntry],
    paper_shadow_outcomes: list[PaperShadowOutcome],
) -> list[str]:
    required: list[str] = []
    locked_evaluation = _latest_revision_locked_evaluation(
        locked_evaluations,
        retest_trial,
        retest_split,
    )
    leaderboard_entry = _latest_revision_leaderboard_entry(
        leaderboard_entries,
        retest_trial,
        locked_evaluation,
    )
    shadow_outcome = _latest_revision_shadow_outcome(
        paper_shadow_outcomes,
        retest_trial,
        locked_evaluation,
        leaderboard_entry,
    )
    if retest_trial is None:
        required.append("experiment_trial")
    if retest_split is None:
        required.extend(["split_manifest", "cost_model_snapshot"])
    if locked_evaluation is None:
        required.append("baseline_evaluation")
    if retest_trial is None or retest_trial.backtest_result_id is None:
        required.append("backtest_result")
    if retest_trial is None or retest_trial.walk_forward_validation_id is None:
        required.append("walk_forward_validation")
    if locked_evaluation is None:
        required.append("locked_evaluation_result")
    if leaderboard_entry is None:
        required.append("leaderboard_entry")
    if shadow_outcome is None:
        required.append("paper_shadow_outcome")
    return required


def _latest_revision_locked_evaluation(
    locked_evaluations: list[LockedEvaluationResult],
    retest_trial: ExperimentTrial | None,
    retest_split: SplitManifest | None,
) -> LockedEvaluationResult | None:
    if retest_trial is None:
        return None
    candidates = []
    for evaluation in locked_evaluations:
        if evaluation.strategy_card_id != retest_trial.strategy_card_id:
            continue
        if evaluation.trial_id != retest_trial.trial_id:
            continue
        if retest_split is not None and evaluation.split_manifest_id != retest_split.manifest_id:
            continue
        if retest_trial.backtest_result_id is not None and evaluation.backtest_result_id != retest_trial.backtest_result_id:
            continue
        if (
            retest_trial.walk_forward_validation_id is not None
            and evaluation.walk_forward_validation_id != retest_trial.walk_forward_validation_id
        ):
            continue
        candidates.append(evaluation)
    return _latest(candidates)


def _latest_revision_leaderboard_entry(
    leaderboard_entries: list[LeaderboardEntry],
    retest_trial: ExperimentTrial | None,
    locked_evaluation: LockedEvaluationResult | None,
) -> LeaderboardEntry | None:
    if retest_trial is None or locked_evaluation is None:
        return None
    return _latest(
        [
            entry
            for entry in leaderboard_entries
            if entry.strategy_card_id == retest_trial.strategy_card_id
            and entry.trial_id == retest_trial.trial_id
            and entry.evaluation_id == locked_evaluation.evaluation_id
            and entry.symbol == retest_trial.symbol
        ]
    )


def _latest_revision_shadow_outcome(
    paper_shadow_outcomes: list[PaperShadowOutcome],
    retest_trial: ExperimentTrial | None,
    locked_evaluation: LockedEvaluationResult | None,
    leaderboard_entry: LeaderboardEntry | None,
) -> PaperShadowOutcome | None:
    if retest_trial is None or locked_evaluation is None or leaderboard_entry is None:
        return None
    return _latest(
        [
            outcome
            for outcome in paper_shadow_outcomes
            if outcome.leaderboard_entry_id == leaderboard_entry.entry_id
            and outcome.strategy_card_id == retest_trial.strategy_card_id
            and outcome.trial_id == retest_trial.trial_id
            and outcome.evaluation_id == locked_evaluation.evaluation_id
            and outcome.symbol == retest_trial.symbol
        ]
    )


def _latest_anchor(
    cards: list[StrategyCard],
    trials: list[ExperimentTrial],
    evaluations: list[LockedEvaluationResult],
    entries: list[LeaderboardEntry],
    outcomes: list[PaperShadowOutcome],
    agendas: list[ResearchAgenda],
) -> tuple[str, object] | None:
    anchors: list[tuple[datetime, str, object]] = []
    anchors.extend((item.created_at, "card", item) for item in cards)
    anchors.extend((item.created_at, "trial", item) for item in trials)
    anchors.extend((item.created_at, "evaluation", item) for item in evaluations)
    anchors.extend((item.created_at, "entry", item) for item in entries)
    anchors.extend((item.created_at, "outcome", item) for item in outcomes)
    anchors.extend((item.created_at, "agenda", item) for item in agendas)
    if not anchors:
        return None
    _, kind, item = max(anchors, key=lambda value: value[0])
    return kind, item


def _latest(items):
    if not items:
        return None
    return max(items, key=lambda item: item.created_at)


def _latest_agenda_for_card(agendas: list[ResearchAgenda], card_id: str) -> ResearchAgenda | None:
    return _latest([item for item in agendas if card_id in item.strategy_card_ids])


def _valid_card(card: StrategyCard | None, symbol: str) -> StrategyCard | None:
    if card is None or symbol not in card.symbols:
        return None
    return card


def _valid_trial(
    trial: ExperimentTrial | None,
    symbol: str,
    strategy_card_id: str,
) -> ExperimentTrial | None:
    if trial is None or trial.symbol != symbol or trial.strategy_card_id != strategy_card_id:
        return None
    return trial


def _valid_evaluation(
    evaluation: LockedEvaluationResult | None,
    *,
    strategy_card_id: str,
    trial_id: str | None,
) -> LockedEvaluationResult | None:
    if evaluation is None or evaluation.strategy_card_id != strategy_card_id:
        return None
    if trial_id is not None and evaluation.trial_id != trial_id:
        return None
    return evaluation


def _valid_entry(
    entry: LeaderboardEntry | None,
    *,
    symbol: str,
    strategy_card_id: str,
    trial_id: str | None,
    evaluation_id: str | None,
) -> LeaderboardEntry | None:
    if entry is None or entry.symbol != symbol or entry.strategy_card_id != strategy_card_id:
        return None
    if trial_id is not None and entry.trial_id != trial_id:
        return None
    if evaluation_id is not None and entry.evaluation_id != evaluation_id:
        return None
    return entry


def _valid_outcome(
    outcome: PaperShadowOutcome | None,
    *,
    symbol: str,
    strategy_card_id: str,
    trial_id: str | None,
    evaluation_id: str | None,
    leaderboard_entry_id: str | None,
) -> PaperShadowOutcome | None:
    if outcome is None or outcome.symbol != symbol or outcome.strategy_card_id != strategy_card_id:
        return None
    if trial_id is not None and outcome.trial_id != trial_id:
        return None
    if evaluation_id is not None and outcome.evaluation_id != evaluation_id:
        return None
    if leaderboard_entry_id is not None and outcome.leaderboard_entry_id != leaderboard_entry_id:
        return None
    return outcome


def _valid_agenda(
    agenda: ResearchAgenda | None,
    symbol: str,
    strategy_card_id: str,
) -> ResearchAgenda | None:
    if agenda is None or agenda.symbol != symbol:
        return None
    if agenda.strategy_card_ids and strategy_card_id not in agenda.strategy_card_ids:
        return None
    return agenda
