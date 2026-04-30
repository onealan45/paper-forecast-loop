from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from forecast_loop.lineage_research_plan import LineageResearchTaskPlan, build_lineage_research_task_plan
from forecast_loop.models import AutomationRun, ResearchAgenda
from forecast_loop.storage import ArtifactRepository
from forecast_loop.strategy_evolution import REPLACEMENT_DECISION_BASIS, draft_replacement_strategy_hypothesis


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
    elif task.task_id == "verify_cross_sample_persistence":
        created_artifact_ids = _execute_verify_cross_sample_persistence(
            repository=repository,
            plan=before_plan,
            created_at=created_at,
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


def _execute_verify_cross_sample_persistence(
    *,
    repository: ArtifactRepository,
    plan: LineageResearchTaskPlan,
    created_at: datetime,
) -> list[str]:
    task = plan.task_by_id("verify_cross_sample_persistence")
    title = f"Cross-sample validation for lineage {plan.root_card_id}"
    hypothesis = (
        f"{task.worker_prompt} "
        f"Latest lineage outcome: {plan.latest_outcome_id or 'none'}. "
        f"Performance verdict: {plan.performance_verdict}."
    )
    strategy_card_ids = _cross_sample_strategy_card_ids(repository, plan)
    agenda = ResearchAgenda(
        agenda_id=ResearchAgenda.build_id(
            symbol=plan.symbol,
            title=title,
            hypothesis=hypothesis,
            target_strategy_family="lineage_cross_sample_validation",
            strategy_card_ids=strategy_card_ids,
        ),
        created_at=created_at,
        symbol=plan.symbol,
        title=title,
        hypothesis=hypothesis,
        priority="MEDIUM",
        status="OPEN",
        target_strategy_family="lineage_cross_sample_validation",
        strategy_card_ids=strategy_card_ids,
        expected_artifacts=[
            "locked_evaluation",
            "walk_forward_validation",
            "paper_shadow_outcome",
        ],
        acceptance_criteria=[
            f"latest_lineage_outcome={plan.latest_outcome_id or 'none'}",
            "replacement or lineage improvement is validated on a fresh sample",
            "locked evaluation and walk-forward evidence are linked before confidence increases",
            task.rationale,
        ],
        blocked_actions=["real_order_submission", "automatic_live_execution"],
        decision_basis="lineage_cross_sample_validation_agenda",
    )
    repository.save_research_agenda(agenda)
    return [agenda.agenda_id]


def _cross_sample_strategy_card_ids(
    repository: ArtifactRepository,
    plan: LineageResearchTaskPlan,
) -> list[str]:
    card_ids = [plan.root_card_id]
    if plan.latest_outcome_id is None:
        return card_ids
    latest_outcome = next(
        (
            outcome
            for outcome in repository.load_paper_shadow_outcomes()
            if outcome.outcome_id == plan.latest_outcome_id
        ),
        None,
    )
    if latest_outcome is None:
        return card_ids
    latest_card = next(
        (card for card in repository.load_strategy_cards() if card.card_id == latest_outcome.strategy_card_id),
        None,
    )
    if (
        latest_card is not None
        and latest_card.decision_basis == REPLACEMENT_DECISION_BASIS
        and latest_card.parameters.get("replacement_source_lineage_root_card_id") == plan.root_card_id
        and latest_card.card_id not in card_ids
    ):
        card_ids.append(latest_card.card_id)
    return card_ids


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
