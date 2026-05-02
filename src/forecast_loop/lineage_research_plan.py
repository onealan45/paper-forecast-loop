from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from forecast_loop.models import PaperShadowOutcome, ResearchAgenda, ResearchAutopilotRun, StrategyCard
from forecast_loop.storage import ArtifactRepository
from forecast_loop.strategy_evolution import REPLACEMENT_DECISION_BASIS
from forecast_loop.strategy_lineage import (
    QUARANTINE_ACTIONS,
    REVISION_ACTIONS,
    StrategyLineageReplacementNode,
    StrategyLineageSummary,
    build_strategy_lineage_summary,
)
from forecast_loop.strategy_research import resolve_latest_strategy_research_chain


@dataclass(frozen=True, slots=True)
class LineageResearchTask:
    task_id: str
    title: str
    status: str
    required_artifact: str
    artifact_id: str | None
    command_args: list[str] | None
    worker_prompt: str
    blocked_reason: str | None
    missing_inputs: list[str]
    rationale: str

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "status": self.status,
            "required_artifact": self.required_artifact,
            "artifact_id": self.artifact_id,
            "command_args": list(self.command_args) if self.command_args is not None else None,
            "worker_prompt": self.worker_prompt,
            "blocked_reason": self.blocked_reason,
            "missing_inputs": list(self.missing_inputs),
            "rationale": self.rationale,
        }


@dataclass(frozen=True, slots=True)
class LineageResearchTaskPlan:
    symbol: str
    agenda_id: str
    root_card_id: str
    latest_outcome_id: str | None
    performance_verdict: str
    latest_recommended_strategy_action: str | None
    next_research_focus: str
    next_task_id: str | None
    tasks: list[LineageResearchTask]

    def task_by_id(self, task_id: str) -> LineageResearchTask:
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        raise KeyError(task_id)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "agenda_id": self.agenda_id,
            "root_card_id": self.root_card_id,
            "latest_outcome_id": self.latest_outcome_id,
            "performance_verdict": self.performance_verdict,
            "latest_recommended_strategy_action": self.latest_recommended_strategy_action,
            "next_research_focus": self.next_research_focus,
            "next_task_id": self.next_task_id,
            "tasks": [task.to_dict() for task in self.tasks],
        }


def build_lineage_research_task_plan(
    *,
    repository: ArtifactRepository,
    storage_dir: Path | str | None,
    symbol: str,
) -> LineageResearchTaskPlan:
    symbol = symbol.upper()
    storage = Path(storage_dir) if storage_dir is not None else None
    strategy_cards = [item for item in repository.load_strategy_cards() if symbol in item.symbols]
    paper_shadow_outcomes = [item for item in repository.load_paper_shadow_outcomes() if item.symbol == symbol]
    research_agendas = [item for item in repository.load_research_agendas() if item.symbol == symbol]
    research_autopilot_runs = [item for item in repository.load_research_autopilot_runs() if item.symbol == symbol]
    agenda, summary = _latest_agenda_anchored_lineage(
        research_agendas=research_agendas,
        strategy_cards=strategy_cards,
        paper_shadow_outcomes=paper_shadow_outcomes,
    )
    if summary is None:
        chain = resolve_latest_strategy_research_chain(
            symbol=symbol,
            strategy_cards=strategy_cards,
            experiment_trials=repository.load_experiment_trials(),
            locked_evaluations=repository.load_locked_evaluation_results(),
            split_manifests=repository.load_split_manifests(),
            leaderboard_entries=repository.load_leaderboard_entries(),
            paper_shadow_outcomes=paper_shadow_outcomes,
            research_agendas=research_agendas,
            research_autopilot_runs=research_autopilot_runs,
        )
        summary = build_strategy_lineage_summary(
            root_card=chain.strategy_card,
            strategy_cards=strategy_cards,
            paper_shadow_outcomes=paper_shadow_outcomes,
        )
        if summary is None:
            raise ValueError(f"strategy lineage not found for symbol: {symbol}")
        agenda = _latest_lineage_research_agenda(research_agendas, summary)
    if agenda is None:
        raise ValueError(f"lineage research agenda not found for symbol: {symbol}; run create-lineage-research-agenda first")
    tasks = _build_tasks(
        storage=storage,
        symbol=symbol,
        strategy_cards=strategy_cards,
        paper_shadow_outcomes=paper_shadow_outcomes,
        research_agendas=research_agendas,
        research_autopilot_runs=research_autopilot_runs,
        agenda=agenda,
        summary=summary,
    )
    next_task = next((task for task in tasks if task.status != "completed"), None)
    return LineageResearchTaskPlan(
        symbol=symbol,
        agenda_id=agenda.agenda_id,
        root_card_id=summary.root_card_id,
        latest_outcome_id=summary.latest_outcome_id,
        performance_verdict=summary.performance_verdict,
        latest_recommended_strategy_action=summary.latest_recommended_strategy_action,
        next_research_focus=summary.next_research_focus,
        next_task_id=next_task.task_id if next_task else None,
        tasks=tasks,
    )


def _latest_agenda_anchored_lineage(
    *,
    research_agendas: list[ResearchAgenda],
    strategy_cards: list[StrategyCard],
    paper_shadow_outcomes: list[PaperShadowOutcome],
) -> tuple[ResearchAgenda | None, StrategyLineageSummary | None]:
    card_by_id = {card.card_id: card for card in strategy_cards}
    candidates = [
        agenda
        for agenda in research_agendas
        if agenda.decision_basis == "strategy_lineage_research_agenda"
    ]
    for agenda in sorted(candidates, key=lambda item: item.created_at, reverse=True):
        root_card = _root_card_for_agenda(agenda, card_by_id)
        summary = build_strategy_lineage_summary(
            root_card=root_card,
            strategy_cards=strategy_cards,
            paper_shadow_outcomes=paper_shadow_outcomes,
        )
        if summary is not None:
            return agenda, summary
    return None, None


def _root_card_for_agenda(
    agenda: ResearchAgenda,
    card_by_id: dict[str, StrategyCard],
) -> StrategyCard | None:
    cards = [card_by_id[card_id] for card_id in agenda.strategy_card_ids if card_id in card_by_id]
    roots = [card for card in cards if card.parent_card_id is None]
    return roots[0] if roots else (cards[0] if cards else None)


def _latest_lineage_research_agenda(
    agendas: list[ResearchAgenda],
    summary: StrategyLineageSummary,
) -> ResearchAgenda | None:
    lineage_ids = {summary.root_card_id, *summary.revision_card_ids}
    candidates = [
        agenda
        for agenda in agendas
        if agenda.decision_basis == "strategy_lineage_research_agenda"
        and lineage_ids.intersection(agenda.strategy_card_ids)
    ]
    return max(candidates, key=lambda item: item.created_at) if candidates else None


def _build_tasks(
    *,
    storage: Path | None,
    symbol: str,
    strategy_cards: list[StrategyCard],
    paper_shadow_outcomes: list[PaperShadowOutcome],
    research_agendas: list[ResearchAgenda],
    research_autopilot_runs: list[ResearchAutopilotRun],
    agenda: ResearchAgenda,
    summary: StrategyLineageSummary,
) -> list[LineageResearchTask]:
    tasks = [_agenda_task(agenda, summary)]
    latest_outcome = _latest_outcome(summary.latest_outcome_id, paper_shadow_outcomes)
    if summary.latest_recommended_strategy_action in QUARANTINE_ACTIONS:
        tasks.append(_replacement_strategy_task(strategy_cards, summary, latest_outcome))
    elif summary.latest_recommended_strategy_action in REVISION_ACTIONS or summary.performance_verdict in {"惡化", "偏弱"}:
        tasks.append(_revision_task(storage, symbol, strategy_cards, summary, latest_outcome))
    elif summary.performance_verdict in {"改善", "偏強"}:
        tasks.extend(_cross_sample_tasks(summary, research_agendas, research_autopilot_runs, paper_shadow_outcomes))
    else:
        tasks.append(_evidence_task(summary))
    return tasks


def _agenda_task(agenda: ResearchAgenda, summary: StrategyLineageSummary) -> LineageResearchTask:
    return LineageResearchTask(
        task_id="resolve_lineage_research_agenda",
        title="Resolve lineage research agenda",
        status="completed",
        required_artifact="research_agenda",
        artifact_id=agenda.agenda_id,
        command_args=None,
        worker_prompt=(
            f"Use agenda {agenda.agenda_id} to work on lineage {summary.root_card_id}. "
            f"Focus: {summary.next_research_focus}"
        ),
        blocked_reason=None,
        missing_inputs=[],
        rationale="A lineage-derived agenda already exists and anchors this task plan.",
    )


def _revision_task(
    storage: Path | None,
    symbol: str,
    strategy_cards: list[StrategyCard],
    summary: StrategyLineageSummary,
    latest_outcome: PaperShadowOutcome | None,
) -> LineageResearchTask:
    if latest_outcome is None:
        return _evidence_task(summary)
    existing_revision = _revision_for_source_outcome(strategy_cards, latest_outcome.outcome_id)
    if existing_revision is not None:
        return LineageResearchTask(
            task_id="propose_strategy_revision",
            title="Propose strategy revision",
            status="completed",
            required_artifact="strategy_card",
            artifact_id=existing_revision.card_id,
            command_args=None,
            worker_prompt=f"Revision {existing_revision.card_id} already exists for {latest_outcome.outcome_id}.",
            blocked_reason=None,
            missing_inputs=[],
            rationale="The latest lineage failure already has a DRAFT revision candidate.",
        )
    missing = []
    if storage is None:
        missing.append("storage_dir")
    command = None
    if storage is not None:
        command = _base_command() + [
            "propose-strategy-revision",
            "--storage-dir",
            str(storage),
            "--paper-shadow-outcome-id",
            latest_outcome.outcome_id,
        ]
    return LineageResearchTask(
        task_id="propose_strategy_revision",
        title="Propose strategy revision",
        status="ready" if command is not None else "blocked",
        required_artifact="strategy_card",
        artifact_id=None,
        command_args=command,
        worker_prompt=(
            f"修正 {latest_outcome.outcome_id} 的失敗歸因："
            f"{', '.join(latest_outcome.failure_attributions or ['unspecified_failure'])}。"
            "建立 DRAFT strategy revision，並保留 locked retest 要求。"
        ),
        blocked_reason="storage_dir_required" if command is None else None,
        missing_inputs=missing,
        rationale=f"Lineage verdict is {summary.performance_verdict}; next focus is {summary.next_research_focus}",
    )


def _replacement_strategy_task(
    strategy_cards: list[StrategyCard],
    summary: StrategyLineageSummary,
    latest_outcome: PaperShadowOutcome | None,
) -> LineageResearchTask:
    failure = summary.primary_failure_attribution or "主要失敗"
    outcome_id = latest_outcome.outcome_id if latest_outcome is not None else "latest lineage outcome"
    existing_replacement = _replacement_for_source_outcome(strategy_cards, outcome_id)
    if existing_replacement is not None:
        return LineageResearchTask(
            task_id="draft_replacement_strategy_hypothesis",
            title="Draft replacement strategy hypothesis",
            status="completed",
            required_artifact="strategy_card",
            artifact_id=existing_replacement.card_id,
            command_args=None,
            worker_prompt=f"Replacement strategy {existing_replacement.card_id} already exists for {outcome_id}.",
            blocked_reason=None,
            missing_inputs=[],
            rationale="A quarantined lineage already produced a replacement strategy hypothesis.",
        )
    return LineageResearchTask(
        task_id="draft_replacement_strategy_hypothesis",
        title="Draft replacement strategy hypothesis",
        status="ready",
        required_artifact="strategy_card",
        artifact_id=None,
        command_args=None,
        worker_prompt=(
            f"此 lineage 最新結果 {outcome_id} 已要求 QUARANTINE。"
            f"不要只微調舊規則；研究一個可替代的新策略假說，優先處理 {failure}，"
            "並明確寫出資料來源、預測訊號、回測設計、失效條件。"
        ),
        blocked_reason=None,
        missing_inputs=[],
        rationale="A quarantined lineage should trigger new strategy research instead of blind recursive patching.",
    )


def _cross_sample_tasks(
    summary: StrategyLineageSummary,
    research_agendas: list[ResearchAgenda],
    research_autopilot_runs: list[ResearchAutopilotRun],
    paper_shadow_outcomes: list[PaperShadowOutcome],
) -> list[LineageResearchTask]:
    linked_run = _cross_sample_autopilot_run_for_lineage(
        summary,
        research_agendas,
        research_autopilot_runs,
        paper_shadow_outcomes,
    )
    linked_agenda = _agenda_by_id(research_agendas, linked_run.agenda_id) if linked_run is not None else None
    agenda_task = _cross_sample_task(summary, research_agendas, existing_agenda=linked_agenda)
    tasks = [agenda_task]
    if agenda_task.status == "completed":
        agenda = _agenda_by_id(research_agendas, agenda_task.artifact_id)
        tasks.append(_cross_sample_autopilot_task(agenda, research_autopilot_runs, paper_shadow_outcomes, summary))
    return tasks


def _cross_sample_task(
    summary: StrategyLineageSummary,
    research_agendas: list[ResearchAgenda],
    *,
    existing_agenda: ResearchAgenda | None = None,
) -> LineageResearchTask:
    if existing_agenda is None:
        existing_agenda = _cross_sample_agenda_for_summary(research_agendas, summary)
    if existing_agenda is not None:
        return LineageResearchTask(
            task_id="verify_cross_sample_persistence",
            title="Verify cross-sample persistence",
            status="completed",
            required_artifact="research_agenda",
            artifact_id=existing_agenda.agenda_id,
            command_args=None,
            worker_prompt=f"Cross-sample validation agenda {existing_agenda.agenda_id} already exists.",
            blocked_reason=None,
            missing_inputs=[],
            rationale="A replacement-aware cross-sample validation agenda has been created for this latest lineage outcome.",
        )
    replacement_context = _latest_replacement_context(summary)
    replacement_prompt = (
        ""
        if replacement_context is None
        else (
            f" Replacement {replacement_context.card_id} produced "
            f"{replacement_context.latest_outcome_id or 'no latest outcome'}"
            f" with excess {replacement_context.latest_excess_return_after_costs}. "
            f"Source outcome: {replacement_context.source_outcome_id or 'none'}."
        )
    )
    replacement_rationale = (
        ""
        if replacement_context is None
        else (
            f" Latest improvement came from replacement {replacement_context.card_id}; "
            "cross-sample validation should test that hypothesis directly."
        )
    )
    return LineageResearchTask(
        task_id="verify_cross_sample_persistence",
        title="Verify cross-sample persistence",
        status="ready",
        required_artifact="research_agenda",
        artifact_id=None,
        command_args=None,
        worker_prompt=(
            "Lineage is improving. Extend validation across a fresh sample before increasing confidence. "
            f"{replacement_prompt}"
            f"Current focus: {summary.next_research_focus}"
        ),
        blocked_reason=None,
        missing_inputs=[],
        rationale=f"Improving lineage evidence still needs cross-sample confirmation.{replacement_rationale}",
    )


def _cross_sample_autopilot_task(
    agenda: ResearchAgenda | None,
    research_autopilot_runs: list[ResearchAutopilotRun],
    paper_shadow_outcomes: list[PaperShadowOutcome],
    summary: StrategyLineageSummary,
) -> LineageResearchTask:
    run = _cross_sample_autopilot_run_for_agenda(agenda, research_autopilot_runs, paper_shadow_outcomes, summary)
    if run is not None:
        return LineageResearchTask(
            task_id="record_cross_sample_autopilot_run",
            title="Record cross-sample autopilot run",
            status="completed",
            required_artifact="research_autopilot_run",
            artifact_id=run.run_id,
            command_args=None,
            worker_prompt=f"Cross-sample autopilot run {run.run_id} already closes agenda {run.agenda_id}.",
            blocked_reason=None,
            missing_inputs=[],
            rationale="Fresh-sample validation has a linked research autopilot run and paper-shadow outcome.",
        )
    blocked_run = _latest_cross_sample_autopilot_run_for_agenda(agenda, research_autopilot_runs, summary)
    if blocked_run is not None:
        missing_inputs = _invalid_cross_sample_run_inputs(
            blocked_run,
            paper_shadow_outcomes=paper_shadow_outcomes,
            summary=summary,
        )
        return LineageResearchTask(
            task_id="record_cross_sample_autopilot_run",
            title="Record cross-sample autopilot run",
            status="blocked",
            required_artifact="research_autopilot_run",
            artifact_id=blocked_run.run_id,
            command_args=None,
            worker_prompt=_blocked_cross_sample_run_prompt(blocked_run, agenda, summary, missing_inputs),
            blocked_reason=_invalid_cross_sample_run_reason(blocked_run),
            missing_inputs=missing_inputs,
            rationale=(
                "A cross-sample autopilot run is recorded, but it is not accepted as completed fresh-sample "
                "evidence because its evidence chain is blocked, stale, or not linked to the latest lineage outcome."
            ),
        )
    return LineageResearchTask(
        task_id="record_cross_sample_autopilot_run",
        title="Record cross-sample autopilot run",
        status="blocked",
        required_artifact="research_autopilot_run",
        artifact_id=None,
        command_args=None,
        worker_prompt=_cross_sample_handoff_prompt(agenda, summary),
        blocked_reason="cross_sample_autopilot_run_missing",
        missing_inputs=_cross_sample_missing_inputs(agenda),
        rationale=(
            "Cross-sample validation agenda exists, but no linked completed autopilot run is recorded yet. "
            "The run must link the agenda's expected fresh-sample evidence before the lineage can treat it as validated."
        ),
    )


def _blocked_cross_sample_run_prompt(
    run: ResearchAutopilotRun,
    agenda: ResearchAgenda | None,
    summary: StrategyLineageSummary,
    missing_inputs: list[str],
) -> str:
    agenda_id = agenda.agenda_id if agenda else run.agenda_id
    blockers = ", ".join(missing_inputs) or "unspecified_blocker"
    strategy_cards = ", ".join(agenda.strategy_card_ids) if agenda else run.strategy_card_id
    return (
        f"Cross-sample autopilot run {run.run_id} exists for agenda {agenda_id}, "
        f"strategy cards: {strategy_cards}, "
        f"latest lineage outcome: {summary.latest_outcome_id or 'none'}, "
        f"but it is not accepted as completed fresh-sample evidence. "
        f"Repair or rerun the evidence chain for blockers: {blockers}."
    )


def _cross_sample_handoff_prompt(
    agenda: ResearchAgenda | None,
    summary: StrategyLineageSummary,
) -> str:
    if agenda is None:
        return (
            "Complete the fresh-sample validation chain for this cross-sample agenda, then record the linked "
            "research autopilot run so the lineage can compare the new sample against prior evidence."
        )
    expected = ", ".join(agenda.expected_artifacts) or "fresh-sample evidence"
    strategy_cards = ", ".join(agenda.strategy_card_ids) or summary.root_card_id
    return (
        f"Complete cross-sample validation agenda {agenda.agenda_id} for lineage {summary.root_card_id}. "
        f"Strategy cards: {strategy_cards}. "
        f"Latest lineage outcome: {summary.latest_outcome_id or 'none'}. "
        f"Expected evidence: {expected}. "
        "After those artifacts exist, record the linked research autopilot run so the lineage can compare "
        "the fresh sample against prior evidence."
    )


def _cross_sample_missing_inputs(agenda: ResearchAgenda | None) -> list[str]:
    missing: list[str] = []
    for item in [*(agenda.expected_artifacts if agenda is not None else []), "research_autopilot_run"]:
        if item not in missing:
            missing.append(item)
    return missing


def _cross_sample_autopilot_run_for_agenda(
    agenda: ResearchAgenda | None,
    research_autopilot_runs: list[ResearchAutopilotRun],
    paper_shadow_outcomes: list[PaperShadowOutcome],
    summary: StrategyLineageSummary,
) -> ResearchAutopilotRun | None:
    if agenda is None:
        return None
    lineage_ids = _lineage_strategy_ids(summary)
    matches = [
        run
        for run in research_autopilot_runs
        if run.agenda_id == agenda.agenda_id
        and _valid_cross_sample_autopilot_run(run, paper_shadow_outcomes, lineage_ids, summary.latest_outcome_id)
    ]
    return max(matches, key=lambda run: run.created_at) if matches else None


def _latest_cross_sample_autopilot_run_for_agenda(
    agenda: ResearchAgenda | None,
    research_autopilot_runs: list[ResearchAutopilotRun],
    summary: StrategyLineageSummary,
) -> ResearchAutopilotRun | None:
    if agenda is None:
        return None
    lineage_ids = _lineage_strategy_ids(summary)
    matches = [
        run
        for run in research_autopilot_runs
        if run.agenda_id == agenda.agenda_id
        and run.decision_basis == "research_paper_autopilot_loop"
        and run.strategy_card_id in lineage_ids
    ]
    return max(matches, key=lambda run: run.created_at) if matches else None


def _cross_sample_autopilot_run_for_lineage(
    summary: StrategyLineageSummary,
    agendas: list[ResearchAgenda],
    research_autopilot_runs: list[ResearchAutopilotRun],
    paper_shadow_outcomes: list[PaperShadowOutcome],
) -> ResearchAutopilotRun | None:
    lineage_ids = _lineage_strategy_ids(summary)
    cross_sample_agenda_ids = {
        agenda.agenda_id
        for agenda in agendas
        if agenda.decision_basis == "lineage_cross_sample_validation_agenda"
        and lineage_ids.intersection(agenda.strategy_card_ids)
    }
    matches = [
        run
        for run in research_autopilot_runs
        if run.agenda_id in cross_sample_agenda_ids
        and run.strategy_card_id in lineage_ids
        and _valid_cross_sample_autopilot_run(run, paper_shadow_outcomes, lineage_ids, summary.latest_outcome_id)
    ]
    return max(matches, key=lambda run: run.created_at) if matches else None


def _valid_cross_sample_autopilot_run(
    run: ResearchAutopilotRun,
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
    outcome = _latest_outcome(run.paper_shadow_outcome_id, paper_shadow_outcomes)
    return outcome is not None and outcome.strategy_card_id in lineage_ids


def _invalid_cross_sample_run_reason(run: ResearchAutopilotRun) -> str:
    if run.loop_status == "BLOCKED" or run.blocked_reasons:
        return "cross_sample_autopilot_run_blocked"
    return "cross_sample_autopilot_run_invalid"


def _invalid_cross_sample_run_inputs(
    run: ResearchAutopilotRun,
    *,
    paper_shadow_outcomes: list[PaperShadowOutcome],
    summary: StrategyLineageSummary,
) -> list[str]:
    if run.blocked_reasons:
        return list(run.blocked_reasons)
    missing: list[str] = []
    if run.paper_shadow_outcome_id is None:
        missing.append("paper_shadow_outcome")
    elif run.paper_shadow_outcome_id != summary.latest_outcome_id:
        missing.append("latest_paper_shadow_outcome")
    elif _latest_outcome(run.paper_shadow_outcome_id, paper_shadow_outcomes) is None:
        missing.append("paper_shadow_outcome")
    if run.loop_status == "BLOCKED" and "blocked_evidence_chain" not in missing:
        missing.append("blocked_evidence_chain")
    return missing or ["valid_cross_sample_autopilot_run"]


def _lineage_strategy_ids(summary: StrategyLineageSummary) -> set[str]:
    return {summary.root_card_id, *summary.revision_card_ids, *summary.replacement_card_ids}


def _agenda_by_id(agendas: list[ResearchAgenda], agenda_id: str | None) -> ResearchAgenda | None:
    if agenda_id is None:
        return None
    return next((agenda for agenda in agendas if agenda.agenda_id == agenda_id), None)


def _cross_sample_agenda_for_summary(
    agendas: list[ResearchAgenda],
    summary: StrategyLineageSummary,
) -> ResearchAgenda | None:
    if summary.latest_outcome_id is None:
        return None
    marker = f"latest_lineage_outcome={summary.latest_outcome_id}"
    target_ids = set(_cross_sample_target_card_ids(summary))
    candidates = [
        agenda
        for agenda in agendas
        if agenda.decision_basis == "lineage_cross_sample_validation_agenda"
        and summary.root_card_id in agenda.strategy_card_ids
        and target_ids == set(agenda.strategy_card_ids)
        and marker in agenda.acceptance_criteria
    ]
    return max(candidates, key=lambda agenda: agenda.created_at) if candidates else None


def _cross_sample_target_card_ids(summary: StrategyLineageSummary) -> list[str]:
    card_ids = [summary.root_card_id]
    latest_card_id = _latest_outcome_strategy_card_id(summary)
    lineage_ids = _lineage_strategy_ids(summary)
    if latest_card_id is not None and latest_card_id != summary.root_card_id and latest_card_id in lineage_ids:
        card_ids.append(latest_card_id)
    return card_ids


def _latest_outcome_strategy_card_id(summary: StrategyLineageSummary) -> str | None:
    if summary.latest_outcome_id is None:
        return None
    for outcome in reversed(summary.outcome_nodes):
        if outcome.outcome_id == summary.latest_outcome_id:
            return outcome.strategy_card_id
    return None


def _latest_replacement_context(summary: StrategyLineageSummary) -> StrategyLineageReplacementNode | None:
    if not summary.replacement_nodes or summary.latest_change_label != "改善":
        return None
    for node in reversed(summary.replacement_nodes):
        if node.latest_outcome_id == summary.latest_outcome_id:
            return node
    return None


def _evidence_task(summary: StrategyLineageSummary) -> LineageResearchTask:
    return LineageResearchTask(
        task_id="collect_lineage_shadow_evidence",
        title="Collect lineage paper-shadow evidence",
        status="blocked",
        required_artifact="paper_shadow_outcome",
        artifact_id=None,
        command_args=None,
        worker_prompt=(
            "先補齊此 lineage 的 paper-shadow outcome，再判斷是否修正、隔離或擴大研究。"
        ),
        blocked_reason="paper_shadow_outcome_missing",
        missing_inputs=["paper_shadow_outcome"],
        rationale=f"Lineage verdict is {summary.performance_verdict}; evidence is insufficient.",
    )


def _latest_outcome(outcome_id: str | None, outcomes: list[PaperShadowOutcome]) -> PaperShadowOutcome | None:
    if outcome_id is None:
        return None
    return next((outcome for outcome in outcomes if outcome.outcome_id == outcome_id), None)


def _revision_for_source_outcome(cards: list[StrategyCard], outcome_id: str) -> StrategyCard | None:
    return next(
        (
            card
            for card in cards
            if card.decision_basis == "paper_shadow_strategy_revision_candidate"
            and card.parameters.get("revision_source_outcome_id") == outcome_id
        ),
        None,
    )


def _replacement_for_source_outcome(cards: list[StrategyCard], outcome_id: str) -> StrategyCard | None:
    matches = [
        card
        for card in cards
        if card.decision_basis == REPLACEMENT_DECISION_BASIS
        and card.parameters.get("replacement_source_outcome_id") == outcome_id
    ]
    return max(matches, key=lambda card: (card.created_at, card.card_id)) if matches else None


def _base_command() -> list[str]:
    script_arg = str(Path("run_forecast_loop.py"))
    if "\\" not in script_arg and "/" not in script_arg:
        script_arg = f".\\{script_arg}"
    return ["python", script_arg]
