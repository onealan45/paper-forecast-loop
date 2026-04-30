from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from forecast_loop.lineage_research_plan import LineageResearchTaskPlan, build_lineage_research_task_plan
from forecast_loop.models import AutomationRun
from forecast_loop.storage import ArtifactRepository
from forecast_loop.strategy_evolution import draft_replacement_strategy_hypothesis


@dataclass(frozen=True, slots=True)
class LineageResearchTaskExecutionResult:
    executed_task_id: str
    before_plan: LineageResearchTaskPlan
    after_plan: LineageResearchTaskPlan
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


def execute_lineage_research_next_task(
    *,
    repository: ArtifactRepository,
    storage_dir: Path | str,
    symbol: str,
    created_at: datetime,
    author: str = "codex-strategy-evolution",
) -> LineageResearchTaskExecutionResult:
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("created_at must be timezone-aware")
    storage_path = Path(storage_dir)
    before_plan = build_lineage_research_task_plan(
        repository=repository,
        storage_dir=storage_path,
        symbol=symbol,
    )
    if before_plan.next_task_id is None:
        raise ValueError("lineage_research_task_plan_complete")
    task = before_plan.task_by_id(before_plan.next_task_id)
    if task.status != "ready":
        raise ValueError(f"lineage_research_next_task_not_ready:{task.task_id}:{task.blocked_reason or task.status}")
    if task.task_id == "draft_replacement_strategy_hypothesis":
        created_artifact_ids = _execute_draft_replacement_strategy_hypothesis(
            repository=repository,
            plan=before_plan,
            created_at=created_at,
            author=author,
        )
    else:
        raise ValueError(f"unsupported_lineage_research_task_execution:{task.task_id}")
    after_plan = build_lineage_research_task_plan(
        repository=repository,
        storage_dir=storage_path,
        symbol=before_plan.symbol,
    )
    run = AutomationRun(
        automation_run_id=AutomationRun.build_id(
            started_at=created_at,
            completed_at=created_at,
            symbol=before_plan.symbol,
            provider="research",
            command="execute-lineage-research-next-task",
            status="LINEAGE_RESEARCH_TASK_EXECUTED",
        ),
        started_at=created_at,
        completed_at=created_at,
        status="LINEAGE_RESEARCH_TASK_EXECUTED",
        symbol=before_plan.symbol,
        provider="research",
        command="execute-lineage-research-next-task",
        steps=_automation_steps(before_plan, task.task_id, created_artifact_ids[-1] if created_artifact_ids else None),
        health_check_id=None,
        decision_id=None,
        repair_request_id=None,
        decision_basis="lineage_research_task_execution",
    )
    repository.save_automation_run(run)
    return LineageResearchTaskExecutionResult(
        executed_task_id=task.task_id,
        before_plan=before_plan,
        after_plan=after_plan,
        automation_run=run,
        created_artifact_ids=created_artifact_ids,
    )


def _execute_draft_replacement_strategy_hypothesis(
    *,
    repository: ArtifactRepository,
    plan: LineageResearchTaskPlan,
    created_at: datetime,
    author: str,
) -> list[str]:
    if plan.latest_outcome_id is None:
        raise ValueError("lineage_research_latest_outcome_missing")
    result = draft_replacement_strategy_hypothesis(
        repository=repository,
        created_at=created_at,
        root_card_id=plan.root_card_id,
        paper_shadow_outcome_id=plan.latest_outcome_id,
        author=author,
    )
    return [result.strategy_card.card_id]


def _automation_steps(
    plan: LineageResearchTaskPlan,
    executed_task_id: str,
    created_artifact_id: str | None,
) -> list[dict[str, str | None]]:
    steps: list[dict[str, str | None]] = [
        {
            "name": "lineage_agenda",
            "status": "completed",
            "artifact_id": plan.agenda_id,
        },
        {
            "name": "root_strategy",
            "status": "completed",
            "artifact_id": plan.root_card_id,
        },
    ]
    if plan.latest_outcome_id is not None:
        steps.append(
            {
                "name": "latest_lineage_outcome",
                "status": "completed",
                "artifact_id": plan.latest_outcome_id,
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
