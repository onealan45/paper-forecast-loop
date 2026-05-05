from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from forecast_loop.backtest import run_backtest
from forecast_loop.decision_research_plan import (
    DecisionBlockerResearchTask,
    DecisionBlockerResearchTaskPlan,
    build_decision_blocker_research_task_plan,
)
from forecast_loop.event_edge import build_event_edge_evaluations
from forecast_loop.models import AutomationRun
from forecast_loop.storage import ArtifactRepository
from forecast_loop.walk_forward import run_walk_forward_validation


@dataclass(frozen=True, slots=True)
class DecisionBlockerResearchTaskExecutionResult:
    executed_task_id: str
    before_plan: DecisionBlockerResearchTaskPlan
    after_plan: DecisionBlockerResearchTaskPlan
    automation_run: AutomationRun
    created_artifact_ids: list[str]

    def to_dict(self) -> dict:
        return {
            "executed_task_id": self.executed_task_id,
            "before_plan": self.before_plan.to_dict(),
            "after_plan": self.after_plan.to_dict(),
            "automation_run": self.automation_run.to_dict(),
            "created_artifact_ids": list(self.created_artifact_ids),
        }


def execute_decision_blocker_research_next_task(
    *,
    repository: ArtifactRepository,
    storage_dir: Path | str,
    symbol: str,
    created_at: datetime,
) -> DecisionBlockerResearchTaskExecutionResult:
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("created_at must be timezone-aware")
    storage_path = Path(storage_dir)
    before_plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=storage_path,
        symbol=symbol,
        now=created_at,
    )
    if before_plan.next_task_id is None:
        raise ValueError("decision_blocker_research_task_plan_complete")
    task = before_plan.task_by_id(before_plan.next_task_id)
    if task.status != "ready":
        raise ValueError(
            f"decision_blocker_research_next_task_not_ready:{task.task_id}:"
            f"{task.blocked_reason or task.status}"
        )
    agenda_created_at = _agenda_created_at(repository, before_plan.agenda_id)
    if agenda_created_at is None:
        raise ValueError(f"decision_blocker_research_agenda_missing:{before_plan.agenda_id}")
    if created_at < agenda_created_at:
        raise ValueError(
            "decision_blocker_research_execution_before_agenda:"
            f"created_at={created_at.isoformat()}:agenda_created_at={agenda_created_at.isoformat()}"
        )

    if task.task_id == "build_event_edge_evaluation":
        created_artifact_ids = _execute_build_event_edge_evaluation(
            storage_dir=storage_path,
            symbol=before_plan.symbol,
            created_at=created_at,
        )
    elif task.task_id == "run_backtest":
        created_artifact_ids = _execute_run_backtest(
            storage_dir=storage_path,
            symbol=before_plan.symbol,
            task=task,
            created_at=created_at,
        )
    elif task.task_id == "run_walk_forward_validation":
        created_artifact_ids = _execute_run_walk_forward_validation(
            storage_dir=storage_path,
            symbol=before_plan.symbol,
            task=task,
            created_at=created_at,
        )
    else:
        raise ValueError(f"unsupported_decision_blocker_research_task_execution:{task.task_id}")
    if not created_artifact_ids:
        raise ValueError(f"decision_blocker_research_task_created_no_artifacts:{task.task_id}")
    after_plan = build_decision_blocker_research_task_plan(
        repository=repository,
        storage_dir=storage_path,
        symbol=before_plan.symbol,
        now=created_at,
    )
    completed_task = after_plan.task_by_id(task.task_id)
    if completed_task.status != "completed" or completed_task.artifact_id not in created_artifact_ids:
        raise ValueError(
            "decision_blocker_research_task_not_completed_after_execution:"
            f"{task.task_id}:{completed_task.artifact_id or 'missing_artifact'}"
        )
    run = AutomationRun(
        automation_run_id=AutomationRun.build_id(
            started_at=created_at,
            completed_at=created_at,
            symbol=before_plan.symbol,
            provider="research",
            command="execute-decision-blocker-research-next-task",
            status="DECISION_BLOCKER_RESEARCH_TASK_EXECUTED",
        ),
        started_at=created_at,
        completed_at=created_at,
        status="DECISION_BLOCKER_RESEARCH_TASK_EXECUTED",
        symbol=before_plan.symbol,
        provider="research",
        command="execute-decision-blocker-research-next-task",
        steps=_automation_steps(before_plan, task.task_id, completed_task.artifact_id),
        health_check_id=None,
        decision_id=before_plan.decision_id,
        repair_request_id=None,
        decision_basis="decision_blocker_research_task_execution",
    )
    repository.save_automation_run(run)
    return DecisionBlockerResearchTaskExecutionResult(
        executed_task_id=task.task_id,
        before_plan=before_plan,
        after_plan=after_plan,
        automation_run=run,
        created_artifact_ids=created_artifact_ids,
    )


def _agenda_created_at(repository: ArtifactRepository, agenda_id: str) -> datetime | None:
    for agenda in repository.load_research_agendas():
        if agenda.agenda_id == agenda_id:
            return agenda.created_at
    return None


def _execute_build_event_edge_evaluation(
    *,
    storage_dir: Path,
    symbol: str,
    created_at: datetime,
) -> list[str]:
    result = build_event_edge_evaluations(
        storage_dir=storage_dir,
        created_at=created_at,
        symbol=symbol,
        horizon_hours=24,
        min_sample_size=3,
        estimated_cost_bps=10.0,
    )
    return list(result.evaluation_ids)


def _execute_run_backtest(
    *,
    storage_dir: Path,
    symbol: str,
    task: DecisionBlockerResearchTask,
    created_at: datetime,
) -> list[str]:
    result = run_backtest(
        storage_dir=storage_dir,
        symbol=symbol,
        start=_datetime_arg(task, "--start"),
        end=_datetime_arg(task, "--end"),
        created_at=created_at,
        as_of=_datetime_arg(task, "--as-of"),
        id_context=_decision_blocker_id_context(task),
    )
    return [result.result.result_id]


def _execute_run_walk_forward_validation(
    *,
    storage_dir: Path,
    symbol: str,
    task: DecisionBlockerResearchTask,
    created_at: datetime,
) -> list[str]:
    result = run_walk_forward_validation(
        storage_dir=storage_dir,
        symbol=symbol,
        start=_datetime_arg(task, "--start"),
        end=_datetime_arg(task, "--end"),
        created_at=created_at,
        as_of=_datetime_arg(task, "--as-of"),
        train_size=_int_arg(task, "--train-size"),
        validation_size=_int_arg(task, "--validation-size"),
        test_size=_int_arg(task, "--test-size"),
        step_size=_int_arg(task, "--step-size"),
        id_context=_decision_blocker_id_context(task),
    )
    return [result.validation.validation_id]


def _datetime_arg(task: DecisionBlockerResearchTask, name: str) -> datetime:
    value = _required_arg(task, name)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"decision_blocker_research_task_arg_must_be_timezone_aware:{task.task_id}:{name}")
    return parsed


def _int_arg(task: DecisionBlockerResearchTask, name: str) -> int:
    return int(_required_arg(task, name))


def _required_arg(task: DecisionBlockerResearchTask, name: str) -> str:
    args = task.command_args or []
    try:
        index = args.index(name)
    except ValueError as exc:
        raise ValueError(f"decision_blocker_research_task_arg_missing:{task.task_id}:{name}") from exc
    if index + 1 >= len(args):
        raise ValueError(f"decision_blocker_research_task_arg_missing_value:{task.task_id}:{name}")
    return args[index + 1]


def _decision_blocker_id_context(task: DecisionBlockerResearchTask) -> str:
    return f"decision_blocker_research:{task.task_id}:{task.required_artifact}"


def _automation_steps(
    plan: DecisionBlockerResearchTaskPlan,
    executed_task_id: str,
    created_artifact_id: str,
) -> list[dict[str, str | None]]:
    steps: list[dict[str, str | None]] = [
        {
            "name": "decision_blocker_research_agenda",
            "status": "completed",
            "artifact_id": plan.agenda_id,
        }
    ]
    if plan.decision_id is not None:
        steps.append(
            {
                "name": "strategy_decision",
                "status": "linked",
                "artifact_id": plan.decision_id,
            }
        )
    steps.append(
        {
            "name": executed_task_id,
            "status": "executed",
            "artifact_id": created_artifact_id,
        }
    )
    return steps
