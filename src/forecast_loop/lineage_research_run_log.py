from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from forecast_loop.lineage_research_plan import LineageResearchTaskPlan, build_lineage_research_task_plan
from forecast_loop.models import AutomationRun
from forecast_loop.storage import ArtifactRepository


@dataclass(frozen=True, slots=True)
class LineageResearchRunLogResult:
    automation_run: AutomationRun
    task_plan: LineageResearchTaskPlan

    def to_dict(self) -> dict:
        return {
            "automation_run": self.automation_run.to_dict(),
            "lineage_research_task_plan": self.task_plan.to_dict(),
        }


def automation_run_matches_lineage_research_plan(
    run: AutomationRun,
    task_plan: LineageResearchTaskPlan,
) -> bool:
    return (
        run.symbol == task_plan.symbol
        and run.provider == "research"
        and run.command == "lineage-research-plan"
        and run.decision_basis == "lineage_research_task_plan_run_log"
        and _step_artifact_id(run, "lineage_agenda") == task_plan.agenda_id
        and _step_artifact_id(run, "root_strategy") == task_plan.root_card_id
        and _step_artifact_id(run, "latest_lineage_outcome") == task_plan.latest_outcome_id
    )


def record_lineage_research_task_run(
    *,
    repository: ArtifactRepository,
    storage_dir: Path | str,
    symbol: str,
    created_at: datetime,
) -> LineageResearchRunLogResult:
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("created_at must be timezone-aware")
    storage_path = Path(storage_dir)
    task_plan = build_lineage_research_task_plan(
        repository=repository,
        storage_dir=storage_path,
        symbol=symbol,
    )
    status = _run_status(task_plan)
    run = AutomationRun(
        automation_run_id=AutomationRun.build_id(
            started_at=created_at,
            completed_at=created_at,
            symbol=task_plan.symbol,
            provider="research",
            command="lineage-research-plan",
            status=status,
        ),
        started_at=created_at,
        completed_at=created_at,
        status=status,
        symbol=task_plan.symbol,
        provider="research",
        command="lineage-research-plan",
        steps=_steps(task_plan),
        health_check_id=None,
        decision_id=None,
        repair_request_id=None,
        decision_basis="lineage_research_task_plan_run_log",
    )
    repository.save_automation_run(run)
    return LineageResearchRunLogResult(automation_run=run, task_plan=task_plan)


def _step_artifact_id(run: AutomationRun, step_name: str) -> str | None:
    for step in run.steps:
        if step.get("name") == step_name:
            return step.get("artifact_id")
    return None


def _run_status(task_plan: LineageResearchTaskPlan) -> str:
    if task_plan.next_task_id is None:
        return "LINEAGE_RESEARCH_TASK_COMPLETE"
    next_task = task_plan.task_by_id(task_plan.next_task_id)
    if next_task.status == "ready":
        return "LINEAGE_RESEARCH_TASK_READY"
    if next_task.status == "blocked":
        return "LINEAGE_RESEARCH_TASK_BLOCKED"
    return "LINEAGE_RESEARCH_TASK_IN_PROGRESS"


def _steps(task_plan: LineageResearchTaskPlan) -> list[dict[str, str | None]]:
    steps: list[dict[str, str | None]] = [
        {
            "name": "lineage_agenda",
            "status": "completed",
            "artifact_id": task_plan.agenda_id,
        },
        {
            "name": "root_strategy",
            "status": "completed",
            "artifact_id": task_plan.root_card_id,
        },
    ]
    if task_plan.latest_outcome_id is not None:
        steps.append(
            {
                "name": "latest_lineage_outcome",
                "status": "completed",
                "artifact_id": task_plan.latest_outcome_id,
            }
        )
    for task in task_plan.tasks:
        steps.append(
            {
                "name": task.task_id,
                "status": task.status,
                "artifact_id": task.artifact_id,
            }
        )
    return steps
