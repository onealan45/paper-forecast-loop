from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from forecast_loop.decision_research_agenda import (
    DECISION_BLOCKER_AGENDA_BASIS,
    extract_decision_research_blockers,
)
from forecast_loop.models import EventEdgeEvaluation, ResearchAgenda, StrategyDecision
from forecast_loop.storage import ArtifactRepository


@dataclass(frozen=True, slots=True)
class DecisionBlockerResearchTask:
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
class DecisionBlockerResearchTaskPlan:
    symbol: str
    agenda_id: str
    decision_id: str | None
    blockers: list[str]
    next_task_id: str | None
    tasks: list[DecisionBlockerResearchTask]

    def task_by_id(self, task_id: str) -> DecisionBlockerResearchTask:
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        raise KeyError(task_id)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "agenda_id": self.agenda_id,
            "decision_id": self.decision_id,
            "blockers": list(self.blockers),
            "next_task_id": self.next_task_id,
            "tasks": [task.to_dict() for task in self.tasks],
        }


def build_decision_blocker_research_task_plan(
    *,
    repository: ArtifactRepository,
    storage_dir: Path | str | None,
    symbol: str,
    now: datetime,
) -> DecisionBlockerResearchTaskPlan:
    symbol = symbol.upper()
    storage = Path(storage_dir) if storage_dir is not None else None
    agenda = _latest_decision_blocker_agenda(repository.load_research_agendas(), symbol)
    if agenda is None:
        raise ValueError(f"decision blocker research agenda not found for symbol: {symbol}")
    latest_decision = _latest_decision(repository.load_strategy_decisions(), symbol)
    blockers = extract_decision_research_blockers(latest_decision) if latest_decision else []
    if not blockers:
        blockers = _blockers_from_agenda(agenda)
    tasks = [_agenda_task(agenda, latest_decision, blockers)]
    event_edges = repository.load_event_edge_evaluations()
    tasks.extend(_evidence_tasks(agenda, storage, symbol, now, blockers, event_edges))
    next_task = next((task for task in tasks if task.status != "completed"), None)
    return DecisionBlockerResearchTaskPlan(
        symbol=symbol,
        agenda_id=agenda.agenda_id,
        decision_id=latest_decision.decision_id if latest_decision else _decision_id_from_text(agenda.hypothesis),
        blockers=blockers,
        next_task_id=next_task.task_id if next_task else None,
        tasks=tasks,
    )


def _latest_decision_blocker_agenda(
    agendas: list[ResearchAgenda],
    symbol: str,
) -> ResearchAgenda | None:
    candidates = [
        agenda
        for agenda in agendas
        if agenda.symbol == symbol and agenda.decision_basis == DECISION_BLOCKER_AGENDA_BASIS
    ]
    return max(candidates, key=lambda item: (item.created_at, item.agenda_id)) if candidates else None


def _latest_decision(
    decisions: list[StrategyDecision],
    symbol: str,
) -> StrategyDecision | None:
    matches = [decision for decision in decisions if decision.symbol == symbol]
    return max(matches, key=lambda decision: (decision.created_at, decision.decision_id)) if matches else None


def _agenda_task(
    agenda: ResearchAgenda,
    decision: StrategyDecision | None,
    blockers: list[str],
) -> DecisionBlockerResearchTask:
    decision_id = decision.decision_id if decision else _decision_id_from_text(agenda.hypothesis) or "unknown"
    return DecisionBlockerResearchTask(
        task_id="resolve_decision_blocker_research_agenda",
        title="Resolve decision blocker research agenda",
        status="completed",
        required_artifact="research_agenda",
        artifact_id=agenda.agenda_id,
        command_args=None,
        worker_prompt=(
            f"Use agenda {agenda.agenda_id} for decision {decision_id}. "
            f"Research blockers: {', '.join(blockers) if blockers else 'unknown'}."
        ),
        blocked_reason=None,
        missing_inputs=[],
        rationale="A decision-blocker agenda already exists and anchors this task plan.",
    )


def _evidence_tasks(
    agenda: ResearchAgenda,
    storage: Path | None,
    symbol: str,
    now: datetime,
    blockers: list[str],
    event_edges: list[EventEdgeEvaluation],
) -> list[DecisionBlockerResearchTask]:
    tasks: list[DecisionBlockerResearchTask] = []
    expected = set(agenda.expected_artifacts)
    if "event_edge_evaluation" in expected:
        tasks.append(_event_edge_task(agenda, storage, symbol, now, blockers, event_edges))
    if "backtest_result" in expected:
        tasks.append(_backtest_task(blockers))
    if "walk_forward_validation" in expected:
        tasks.append(_walk_forward_task(blockers))
    if "baseline_evaluation" in expected:
        tasks.append(_baseline_task(blockers))
    return tasks


def _event_edge_task(
    agenda: ResearchAgenda,
    storage: Path | None,
    symbol: str,
    now: datetime,
    blockers: list[str],
    event_edges: list[EventEdgeEvaluation],
) -> DecisionBlockerResearchTask:
    latest_edge = _latest_event_edge_after_agenda(event_edges, agenda)
    if latest_edge is not None:
        return DecisionBlockerResearchTask(
            task_id="build_event_edge_evaluation",
            title="Build event-edge evaluation for decision blocker",
            status="completed",
            required_artifact="event_edge_evaluation",
            artifact_id=latest_edge.evaluation_id,
            command_args=None,
            worker_prompt=_worker_prompt("event-edge evaluation", blockers),
            blocked_reason=None,
            missing_inputs=[],
            rationale="A same-symbol event-edge evaluation already exists after this blocker agenda.",
        )
    missing = [] if storage is not None else ["storage_dir"]
    command = None
    if storage is not None:
        command = _base_command() + [
            "build-event-edge",
            "--storage-dir",
            str(storage),
            "--symbol",
            symbol,
            "--created-at",
            now.isoformat(),
        ]
    return DecisionBlockerResearchTask(
        task_id="build_event_edge_evaluation",
        title="Build event-edge evaluation for decision blocker",
        status="ready" if not missing else "blocked",
        required_artifact="event_edge_evaluation",
        artifact_id=None,
        command_args=command,
        worker_prompt=_worker_prompt("event-edge evaluation", blockers),
        blocked_reason="missing_storage_dir" if missing else None,
        missing_inputs=missing,
        rationale="The latest decision is blocked by event-edge evidence, so event edge should be rebuilt first.",
    )


def _backtest_task(blockers: list[str]) -> DecisionBlockerResearchTask:
    return _window_blocked_task(
        task_id="run_backtest",
        title="Run blocker-focused backtest",
        required_artifact="backtest_result",
        blocked_reason="missing_backtest_window",
        worker_prompt=_worker_prompt("backtest", blockers),
        rationale="Backtest evidence needs explicit start/end windows before a safe command can be emitted.",
    )


def _walk_forward_task(blockers: list[str]) -> DecisionBlockerResearchTask:
    return _window_blocked_task(
        task_id="run_walk_forward_validation",
        title="Run blocker-focused walk-forward validation",
        required_artifact="walk_forward_validation",
        blocked_reason="missing_walk_forward_window",
        worker_prompt=_worker_prompt("walk-forward validation", blockers),
        rationale="Walk-forward validation needs explicit start/end windows before a safe command can be emitted.",
    )


def _baseline_task(blockers: list[str]) -> DecisionBlockerResearchTask:
    return DecisionBlockerResearchTask(
        task_id="refresh_baseline_evaluation",
        title="Refresh baseline comparison evidence",
        status="blocked",
        required_artifact="baseline_evaluation",
        artifact_id=None,
        command_args=None,
        worker_prompt=_worker_prompt("baseline evaluation", blockers),
        blocked_reason="baseline_refresh_command_not_available",
        missing_inputs=["baseline_refresh_command"],
        rationale="Baseline blocker is explicit, but this repo does not yet expose a standalone baseline refresh command.",
    )


def _window_blocked_task(
    *,
    task_id: str,
    title: str,
    required_artifact: str,
    blocked_reason: str,
    worker_prompt: str,
    rationale: str,
) -> DecisionBlockerResearchTask:
    return DecisionBlockerResearchTask(
        task_id=task_id,
        title=title,
        status="blocked",
        required_artifact=required_artifact,
        artifact_id=None,
        command_args=None,
        worker_prompt=worker_prompt,
        blocked_reason=blocked_reason,
        missing_inputs=["start", "end"],
        rationale=rationale,
    )


def _blockers_from_agenda(agenda: ResearchAgenda) -> list[str]:
    if " because " not in agenda.hypothesis:
        return []
    blocker_text = agenda.hypothesis.split(" because ", 1)[1].split(". Research", 1)[0]
    return [item.strip().rstrip(".") for item in blocker_text.split(",") if item.strip()]


def _latest_event_edge_after_agenda(
    event_edges: list[EventEdgeEvaluation],
    agenda: ResearchAgenda,
) -> EventEdgeEvaluation | None:
    candidates = [
        evaluation
        for evaluation in event_edges
        if evaluation.symbol == agenda.symbol and evaluation.created_at >= agenda.created_at
    ]
    return max(candidates, key=lambda item: (item.created_at, item.evaluation_id)) if candidates else None


def _decision_id_from_text(value: str) -> str | None:
    for token in value.split():
        if token.startswith("decision:"):
            return token.rstrip(".,;")
    return None


def _worker_prompt(evidence_name: str, blockers: list[str]) -> str:
    return (
        f"Build {evidence_name} for the latest decision blockers: "
        f"{', '.join(blockers) if blockers else 'unknown'}."
    )


def _base_command() -> list[str]:
    return ["python", "run_forecast_loop.py"]
