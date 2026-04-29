from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from forecast_loop.backtest import run_backtest
from forecast_loop.baselines import build_baseline_evaluation
from forecast_loop.locked_evaluation import lock_evaluation_protocol
from forecast_loop.models import AutomationRun
from forecast_loop.revision_retest_plan import RevisionRetestTaskPlan, build_revision_retest_task_plan
from forecast_loop.storage import ArtifactRepository


@dataclass(frozen=True, slots=True)
class RevisionRetestTaskExecutionResult:
    executed_task_id: str
    before_plan: RevisionRetestTaskPlan
    after_plan: RevisionRetestTaskPlan
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


def execute_revision_retest_next_task(
    *,
    repository: ArtifactRepository,
    storage_dir: Path | str,
    symbol: str,
    created_at: datetime,
    revision_card_id: str | None = None,
) -> RevisionRetestTaskExecutionResult:
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("created_at must be timezone-aware")
    storage_path = Path(storage_dir)
    before_plan = build_revision_retest_task_plan(
        repository=repository,
        storage_dir=storage_path,
        symbol=symbol,
        revision_card_id=revision_card_id,
    )
    if before_plan.next_task_id is None:
        raise ValueError("revision_retest_task_plan_complete")
    task = before_plan.task_by_id(before_plan.next_task_id)
    if task.status != "ready":
        raise ValueError(f"revision_retest_next_task_not_ready:{task.task_id}:{task.blocked_reason or task.status}")
    if task.task_id == "lock_evaluation_protocol":
        created_artifact_ids = _execute_lock_evaluation_protocol(
            repository=repository,
            plan=before_plan,
            created_at=created_at,
        )
    elif task.task_id == "generate_baseline_evaluation":
        created_artifact_ids = _execute_generate_baseline_evaluation(
            repository=repository,
            plan=before_plan,
            created_at=created_at,
        )
    elif task.task_id == "run_backtest":
        created_artifact_ids = _execute_run_backtest(
            repository=repository,
            storage_dir=storage_path,
            plan=before_plan,
            created_at=created_at,
        )
    else:
        raise ValueError(f"unsupported_revision_retest_task_execution:{task.task_id}")
    after_plan = build_revision_retest_task_plan(
        repository=repository,
        storage_dir=storage_path,
        symbol=symbol,
        revision_card_id=before_plan.strategy_card_id,
    )
    run = AutomationRun(
        automation_run_id=AutomationRun.build_id(
            started_at=created_at,
            completed_at=created_at,
            symbol=before_plan.symbol,
            provider="research",
            command="execute-revision-retest-next-task",
            status="RETEST_TASK_EXECUTED",
        ),
        started_at=created_at,
        completed_at=created_at,
        status="RETEST_TASK_EXECUTED",
        symbol=before_plan.symbol,
        provider="research",
        command="execute-revision-retest-next-task",
        steps=[
            {
                "name": "revision_card",
                "status": "completed",
                "artifact_id": before_plan.strategy_card_id,
            },
            {
                "name": "source_outcome",
                "status": "completed",
                "artifact_id": before_plan.source_outcome_id,
            },
            {
                "name": task.task_id,
                "status": "executed",
                "artifact_id": created_artifact_ids[-1] if created_artifact_ids else None,
            },
        ],
        health_check_id=None,
        decision_id=None,
        repair_request_id=None,
        decision_basis="revision_retest_task_execution",
    )
    repository.save_automation_run(run)
    return RevisionRetestTaskExecutionResult(
        executed_task_id=task.task_id,
        before_plan=before_plan,
        after_plan=after_plan,
        automation_run=run,
        created_artifact_ids=created_artifact_ids,
    )


def _execute_generate_baseline_evaluation(
    *,
    repository: ArtifactRepository,
    plan: RevisionRetestTaskPlan,
    created_at: datetime,
) -> list[str]:
    forecasts = [forecast for forecast in repository.load_forecasts() if forecast.symbol == plan.symbol]
    baseline = build_baseline_evaluation(
        symbol=plan.symbol,
        generated_at=created_at,
        forecasts=forecasts,
        scores=repository.load_scores(),
    )
    repository.save_baseline_evaluation(baseline)
    return [baseline.baseline_id]


def _execute_run_backtest(
    *,
    repository: ArtifactRepository,
    storage_dir: Path,
    plan: RevisionRetestTaskPlan,
    created_at: datetime,
) -> list[str]:
    if plan.split_manifest_id is None:
        raise ValueError("revision_retest_split_manifest_missing")
    split = next(
        (item for item in repository.load_split_manifests() if item.manifest_id == plan.split_manifest_id),
        None,
    )
    if split is None:
        raise ValueError(f"missing_split_manifest:{plan.split_manifest_id}")
    result = run_backtest(
        storage_dir=storage_dir,
        symbol=plan.symbol,
        start=split.holdout_start,
        end=split.holdout_end,
        created_at=created_at,
    )
    return [result.result.result_id]


def _execute_lock_evaluation_protocol(
    *,
    repository: ArtifactRepository,
    plan: RevisionRetestTaskPlan,
    created_at: datetime,
) -> list[str]:
    if plan.dataset_id is None:
        raise ValueError("revision_retest_dataset_missing")
    if plan.split_manifest_id is None:
        raise ValueError("revision_retest_split_manifest_missing")
    split = next(
        (item for item in repository.load_split_manifests() if item.manifest_id == plan.split_manifest_id),
        None,
    )
    if split is None:
        raise ValueError(f"missing_split_manifest:{plan.split_manifest_id}")
    locked_split, cost_model = lock_evaluation_protocol(
        repository=repository,
        created_at=created_at,
        strategy_card_id=plan.strategy_card_id,
        dataset_id=plan.dataset_id,
        symbol=plan.symbol,
        train_start=split.train_start,
        train_end=split.train_end,
        validation_start=split.validation_start,
        validation_end=split.validation_end,
        holdout_start=split.holdout_start,
        holdout_end=split.holdout_end,
        embargo_hours=split.embargo_hours,
    )
    return [locked_split.manifest_id, cost_model.cost_model_id]
