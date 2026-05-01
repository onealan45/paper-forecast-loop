from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from forecast_loop.models import AutomationRun
from forecast_loop.revision_retest_plan import RevisionRetestTaskPlan, build_revision_retest_task_plan
from forecast_loop.storage import ArtifactRepository


@dataclass(frozen=True, slots=True)
class RevisionRetestRunLogResult:
    automation_run: AutomationRun
    task_plan: RevisionRetestTaskPlan

    def to_dict(self) -> dict:
        return {
            "automation_run": self.automation_run.to_dict(),
            "revision_retest_task_plan": self.task_plan.to_dict(),
        }


def automation_run_matches_revision_retest_plan(
    run: AutomationRun,
    task_plan: RevisionRetestTaskPlan,
) -> bool:
    return (
        run.symbol == task_plan.symbol
        and run.provider == "research"
        and run.command == "revision-retest-plan"
        and run.decision_basis == "revision_retest_task_plan_run_log"
        and _step_artifact_id(run, "revision_card") == task_plan.strategy_card_id
        and _step_artifact_id(run, "source_outcome") == task_plan.source_outcome_id
    )


def record_revision_retest_task_run(
    *,
    repository: ArtifactRepository,
    storage_dir: Path | str,
    symbol: str,
    created_at: datetime,
    revision_card_id: str | None = None,
) -> RevisionRetestRunLogResult:
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("created_at must be timezone-aware")
    storage_path = Path(storage_dir)
    task_plan = build_revision_retest_task_plan(
        repository=repository,
        storage_dir=storage_path,
        symbol=symbol,
        revision_card_id=revision_card_id,
    )
    status = _run_status(task_plan)
    run = AutomationRun(
        automation_run_id=AutomationRun.build_id(
            started_at=created_at,
            completed_at=created_at,
            symbol=task_plan.symbol,
            provider="research",
            command="revision-retest-plan",
            status=status,
        ),
        started_at=created_at,
        completed_at=created_at,
        status=status,
        symbol=task_plan.symbol,
        provider="research",
        command="revision-retest-plan",
        steps=_steps(task_plan),
        health_check_id=None,
        decision_id=None,
        repair_request_id=None,
        decision_basis="revision_retest_task_plan_run_log",
    )
    repository.save_automation_run(run)
    return RevisionRetestRunLogResult(automation_run=run, task_plan=task_plan)


def _step_artifact_id(run: AutomationRun, step_name: str) -> str | None:
    for step in run.steps:
        if step.get("name") == step_name:
            return step.get("artifact_id")
    return None


def _run_status(task_plan: RevisionRetestTaskPlan) -> str:
    if task_plan.next_task_id is None:
        return "RETEST_TASK_COMPLETE"
    next_task = task_plan.task_by_id(task_plan.next_task_id)
    if next_task.status == "ready":
        return "RETEST_TASK_READY"
    if next_task.status == "blocked":
        return "RETEST_TASK_BLOCKED"
    return "RETEST_TASK_IN_PROGRESS"


def _steps(task_plan: RevisionRetestTaskPlan) -> list[dict[str, str | None]]:
    steps: list[dict[str, str | None]] = [
        {
            "name": "revision_card",
            "status": "completed",
            "artifact_id": task_plan.strategy_card_id,
        },
        {
            "name": "source_outcome",
            "status": "completed",
            "artifact_id": task_plan.source_outcome_id,
        },
    ]
    for task in task_plan.tasks:
        steps.append(
            {
                "name": task.task_id,
                "status": task.status,
                "artifact_id": task.artifact_id,
            }
        )
    if task_plan.next_task_id is not None:
        next_task = task_plan.task_by_id(task_plan.next_task_id)
        steps.extend(
            [
                {
                    "name": "next_task_required_artifact",
                    "status": next_task.status,
                    "artifact_id": next_task.required_artifact,
                },
                {
                    "name": "next_task_rationale",
                    "status": next_task.status,
                    "artifact_id": next_task.rationale,
                },
            ]
        )
        if next_task.blocked_reason is not None:
            steps.append(
                {
                    "name": "next_task_blocked_reason",
                    "status": next_task.status,
                    "artifact_id": next_task.blocked_reason,
                }
            )
        if next_task.missing_inputs:
            steps.append(
                {
                    "name": "next_task_missing_inputs",
                    "status": next_task.status,
                    "artifact_id": ", ".join(next_task.missing_inputs),
                }
            )
    return steps
