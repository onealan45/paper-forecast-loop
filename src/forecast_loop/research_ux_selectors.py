from __future__ import annotations

from forecast_loop.lineage_research_plan import LineageResearchTaskPlan
from forecast_loop.models import (
    ExperimentTrial,
    PaperShadowOutcome,
    ResearchAgenda,
    ResearchAutopilotRun,
    StrategyCard,
)
from forecast_loop.strategy_lineage import StrategyLineageSummary


def latest_revision_retest_autopilot_run(
    runs: list[ResearchAutopilotRun],
    revision_card: StrategyCard | None,
    experiment_trials: list[ExperimentTrial],
) -> ResearchAutopilotRun | None:
    if revision_card is None:
        return None
    matches = [
        run
        for run in runs
        if run.strategy_card_id == revision_card.card_id
        and run.decision_basis == "research_paper_autopilot_loop"
        and run.strategy_decision_id is None
        and run.paper_shadow_outcome_id is not None
        and _research_autopilot_run_uses_retest_trial(run, revision_card.card_id, experiment_trials)
    ]
    return max(matches, key=lambda run: run.created_at) if matches else None


def latest_cross_sample_autopilot_run(
    runs: list[ResearchAutopilotRun],
    agendas: list[ResearchAgenda],
    summary: StrategyLineageSummary | None,
    task_plan: LineageResearchTaskPlan | None,
    paper_shadow_outcomes: list[PaperShadowOutcome],
) -> ResearchAutopilotRun | None:
    lineage_ids = lineage_strategy_ids(summary, task_plan)
    cross_sample_agenda_ids = {
        agenda.agenda_id
        for agenda in cross_sample_agendas_for_lineage(agendas, summary, task_plan)
    }
    matches = [
        run
        for run in runs
        if run.agenda_id in cross_sample_agenda_ids
        and valid_cross_sample_autopilot_run(
            run,
            paper_shadow_outcomes=paper_shadow_outcomes,
            lineage_ids=lineage_ids,
            latest_outcome_id=summary.latest_outcome_id if summary else None,
        )
    ]
    return max(matches, key=lambda run: run.created_at) if matches else None


def cross_sample_agendas_for_lineage(
    agendas: list[ResearchAgenda],
    summary: StrategyLineageSummary | None,
    task_plan: LineageResearchTaskPlan | None,
) -> list[ResearchAgenda]:
    candidates = [
        agenda
        for agenda in agendas
        if agenda.decision_basis == "lineage_cross_sample_validation_agenda"
    ]
    lineage_ids = lineage_strategy_ids(summary, task_plan)
    if not lineage_ids:
        return []
    return [
        agenda
        for agenda in candidates
        if lineage_ids.intersection(agenda.strategy_card_ids)
    ]


def latest_autopilot_run_for_agenda(
    runs: list[ResearchAutopilotRun],
    agenda: ResearchAgenda | None,
    paper_shadow_outcomes: list[PaperShadowOutcome],
    summary: StrategyLineageSummary | None,
) -> ResearchAutopilotRun | None:
    if agenda is None:
        return None
    lineage_ids = lineage_strategy_ids(summary, None)
    matches = [
        run
        for run in runs
        if run.agenda_id == agenda.agenda_id
        and valid_cross_sample_autopilot_run(
            run,
            paper_shadow_outcomes=paper_shadow_outcomes,
            lineage_ids=lineage_ids,
            latest_outcome_id=summary.latest_outcome_id if summary else None,
        )
    ]
    return max(matches, key=lambda run: run.created_at) if matches else None


def valid_cross_sample_autopilot_run(
    run: ResearchAutopilotRun,
    *,
    paper_shadow_outcomes: list[PaperShadowOutcome],
    lineage_ids: set[str],
    latest_outcome_id: str | None,
) -> bool:
    if run.decision_basis != "research_paper_autopilot_loop":
        return False
    if run.loop_status == "BLOCKED" or run.blocked_reasons:
        return False
    if run.paper_shadow_outcome_id is None or run.paper_shadow_outcome_id != latest_outcome_id:
        return False
    outcome = paper_shadow_outcome_by_id(paper_shadow_outcomes, run.paper_shadow_outcome_id)
    return outcome is not None and outcome.strategy_card_id in lineage_ids


def paper_shadow_outcome_by_id(
    outcomes: list[PaperShadowOutcome],
    outcome_id: str | None,
) -> PaperShadowOutcome | None:
    if outcome_id is None:
        return None
    return next((outcome for outcome in outcomes if outcome.outcome_id == outcome_id), None)


def lineage_strategy_ids(
    summary: StrategyLineageSummary | None,
    task_plan: LineageResearchTaskPlan | None,
) -> set[str]:
    lineage_ids: set[str] = set()
    if summary is not None:
        lineage_ids.update([summary.root_card_id, *summary.revision_card_ids, *summary.replacement_card_ids])
    if task_plan is not None:
        lineage_ids.add(task_plan.root_card_id)
    return lineage_ids


def strategy_card_by_id(cards: list[StrategyCard], card_id: str | None) -> StrategyCard | None:
    if card_id is None:
        return None
    return next((card for card in cards if card.card_id == card_id), None)


def research_agenda_by_id(agendas: list[ResearchAgenda], agenda_id: str | None) -> ResearchAgenda | None:
    if agenda_id is None:
        return None
    return next((agenda for agenda in agendas if agenda.agenda_id == agenda_id), None)


def _research_autopilot_run_uses_retest_trial(
    run: ResearchAutopilotRun,
    card_id: str,
    experiment_trials: list[ExperimentTrial],
) -> bool:
    trial = next((item for item in experiment_trials if item.trial_id == run.experiment_trial_id), None)
    if trial is None or trial.strategy_card_id != card_id:
        return False
    return (
        trial.parameters.get("revision_retest_protocol") == "pr14-v1"
        and trial.parameters.get("revision_retest_source_card_id") == card_id
    )

