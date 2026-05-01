from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path

from forecast_loop.backtest import run_backtest
from forecast_loop.baselines import build_baseline_evaluation
from forecast_loop.experiment_registry import record_experiment_trial
from forecast_loop.locked_evaluation import evaluate_leaderboard_gate, lock_evaluation_protocol
from forecast_loop.models import AutomationRun, BacktestResult, MarketCandleRecord, WalkForwardValidation
from forecast_loop.paper_shadow import record_paper_shadow_outcome
from forecast_loop.revision_retest import RETEST_PROTOCOL_VERSION, create_revision_retest_scaffold
from forecast_loop.revision_retest_plan import RevisionRetestTaskPlan, build_revision_retest_task_plan
from forecast_loop.storage import ArtifactRepository
from forecast_loop.walk_forward import run_walk_forward_validation


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
    shadow_window_start: datetime | None = None,
    shadow_window_end: datetime | None = None,
    shadow_observed_return: float | None = None,
    shadow_benchmark_return: float | None = None,
    shadow_max_adverse_excursion: float | None = None,
    shadow_turnover: float | None = None,
    shadow_note: str | None = None,
    derive_shadow_returns_from_candles: bool = False,
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
    shadow_observation_override = _can_execute_shadow_observation_task(
        task=task,
        shadow_window_start=shadow_window_start,
        shadow_window_end=shadow_window_end,
        shadow_observed_return=shadow_observed_return,
        shadow_benchmark_return=shadow_benchmark_return,
        derive_shadow_returns_from_candles=derive_shadow_returns_from_candles,
    )
    if task.status != "ready" and not shadow_observation_override:
        raise ValueError(f"revision_retest_next_task_not_ready:{task.task_id}:{task.blocked_reason or task.status}")
    if task.task_id == "create_revision_retest_scaffold":
        created_artifact_ids = _execute_create_revision_retest_scaffold(
            repository=repository,
            plan=before_plan,
            created_at=created_at,
        )
    elif task.task_id == "lock_evaluation_protocol":
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
    elif task.task_id == "run_walk_forward":
        created_artifact_ids = _execute_run_walk_forward(
            repository=repository,
            storage_dir=storage_path,
            plan=before_plan,
            created_at=created_at,
        )
    elif task.task_id == "record_passed_retest_trial":
        created_artifact_ids = _execute_record_passed_retest_trial(
            repository=repository,
            plan=before_plan,
            created_at=created_at,
        )
    elif task.task_id == "evaluate_leaderboard_gate":
        created_artifact_ids = _execute_evaluate_leaderboard_gate(
            repository=repository,
            plan=before_plan,
            created_at=created_at,
        )
    elif task.task_id == "record_paper_shadow_outcome":
        created_artifact_ids = _execute_record_paper_shadow_outcome(
            repository=repository,
            storage_dir=storage_path,
            plan=before_plan,
            created_at=created_at,
            shadow_window_start=shadow_window_start,
            shadow_window_end=shadow_window_end,
            shadow_observed_return=shadow_observed_return,
            shadow_benchmark_return=shadow_benchmark_return,
            shadow_max_adverse_excursion=shadow_max_adverse_excursion,
            shadow_turnover=shadow_turnover,
            shadow_note=shadow_note,
            derive_shadow_returns_from_candles=derive_shadow_returns_from_candles,
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


def _execute_create_revision_retest_scaffold(
    *,
    repository: ArtifactRepository,
    plan: RevisionRetestTaskPlan,
    created_at: datetime,
) -> list[str]:
    if plan.dataset_id is None:
        raise ValueError("revision_retest_dataset_missing")
    scaffold = create_revision_retest_scaffold(
        repository=repository,
        created_at=created_at,
        symbol=plan.symbol,
        revision_card_id=plan.strategy_card_id,
        dataset_id=plan.dataset_id,
        max_trials=20,
    )
    return [scaffold.experiment_trial.trial_id]


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
        id_context=_retest_evidence_context(plan),
    )
    return [result.result.result_id]


def _execute_run_walk_forward(
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
    result = run_walk_forward_validation(
        storage_dir=storage_dir,
        symbol=plan.symbol,
        start=split.train_start,
        end=split.holdout_end,
        created_at=created_at,
        id_context=_retest_evidence_context(plan),
    )
    validation = _link_holdout_backtest_to_walk_forward(
        repository=repository,
        validation=result.validation,
        backtest_result_id=plan.backtest_result_id,
    )
    return [validation.validation_id]


def _link_holdout_backtest_to_walk_forward(
    *,
    repository: ArtifactRepository,
    validation: WalkForwardValidation,
    backtest_result_id: str | None,
) -> WalkForwardValidation:
    if backtest_result_id is None or backtest_result_id in validation.backtest_result_ids:
        return validation
    backtest_result_ids = list(dict.fromkeys([*validation.backtest_result_ids, backtest_result_id]))
    linked_validation = replace(
        validation,
        validation_id=WalkForwardValidation.build_id(
            symbol=validation.symbol,
            start=validation.start,
            end=validation.end,
            train_size=validation.train_size,
            validation_size=validation.validation_size,
            test_size=validation.test_size,
            step_size=validation.step_size,
            moving_average_window=validation.moving_average_window,
            backtest_result_ids=backtest_result_ids,
        ),
        backtest_result_ids=backtest_result_ids,
        decision_basis=(
            f"{validation.decision_basis}; revision retest holdout backtest linked "
            "for selected split evidence"
        ),
    )
    repository.save_walk_forward_validation(linked_validation)
    return linked_validation


def _execute_record_passed_retest_trial(
    *,
    repository: ArtifactRepository,
    plan: RevisionRetestTaskPlan,
    created_at: datetime,
) -> list[str]:
    if plan.pending_trial_id is None:
        raise ValueError("revision_retest_pending_trial_missing")
    if plan.dataset_id is None:
        raise ValueError("revision_retest_dataset_missing")
    if plan.backtest_result_id is None:
        raise ValueError("revision_retest_backtest_result_missing")
    if plan.walk_forward_validation_id is None:
        raise ValueError("revision_retest_walk_forward_validation_missing")
    pending_trial = next(
        (item for item in repository.load_experiment_trials() if item.trial_id == plan.pending_trial_id),
        None,
    )
    if pending_trial is None:
        raise ValueError(f"missing_pending_retest_trial:{plan.pending_trial_id}")
    _ensure_trial_budget_available(
        repository=repository,
        strategy_card_id=plan.strategy_card_id,
        trial_index=pending_trial.trial_index,
        max_trials=int(pending_trial.parameters.get("max_trials", 20)),
    )
    revision_card = next(
        (item for item in repository.load_strategy_cards() if item.card_id == plan.strategy_card_id),
        None,
    )
    if revision_card is None:
        raise ValueError(f"missing_revision_strategy_card:{plan.strategy_card_id}")
    trial = record_experiment_trial(
        repository=repository,
        created_at=created_at,
        strategy_card_id=plan.strategy_card_id,
        trial_index=pending_trial.trial_index,
        status="PASSED",
        symbol=plan.symbol,
        max_trials=int(pending_trial.parameters.get("max_trials", 20)),
        seed=pending_trial.seed,
        dataset_id=plan.dataset_id,
        backtest_result_id=plan.backtest_result_id,
        walk_forward_validation_id=plan.walk_forward_validation_id,
        parameters={
            "revision_retest_protocol": RETEST_PROTOCOL_VERSION,
            "revision_retest_source_card_id": plan.strategy_card_id,
            "revision_source_outcome_id": plan.source_outcome_id,
            "revision_parent_card_id": revision_card.parent_card_id,
        },
        started_at=pending_trial.started_at,
        completed_at=created_at,
    )
    if trial.status != "PASSED":
        raise ValueError(f"revision_retest_passed_trial_not_recorded:{trial.status}")
    return [trial.trial_id]


def _ensure_trial_budget_available(
    *,
    repository: ArtifactRepository,
    strategy_card_id: str,
    trial_index: int,
    max_trials: int,
) -> None:
    consumed_indexes: set[int] = set()
    for trial in repository.load_experiment_trials():
        if trial.strategy_card_id != strategy_card_id:
            continue
        if trial.status in {"PENDING", "RUNNING"}:
            continue
        if trial.status == "ABORTED" and trial.failure_reason == "trial_budget_exhausted":
            continue
        consumed_indexes.add(trial.trial_index)
    if trial_index not in consumed_indexes and len(consumed_indexes) >= max_trials:
        raise ValueError("revision_retest_trial_budget_exhausted")


def _execute_evaluate_leaderboard_gate(
    *,
    repository: ArtifactRepository,
    plan: RevisionRetestTaskPlan,
    created_at: datetime,
) -> list[str]:
    missing = []
    if plan.passed_trial_id is None:
        missing.append("passed_retest_trial")
    if plan.split_manifest_id is None:
        missing.append("split_manifest")
    if plan.cost_model_id is None:
        missing.append("cost_model_snapshot")
    if plan.baseline_id is None:
        missing.append("baseline_evaluation")
    if plan.backtest_result_id is None:
        missing.append("backtest_result")
    if plan.walk_forward_validation_id is None:
        missing.append("walk_forward_validation")
    if missing:
        raise ValueError(f"revision_retest_leaderboard_gate_inputs_missing:{','.join(missing)}")
    assert plan.passed_trial_id is not None
    assert plan.split_manifest_id is not None
    assert plan.cost_model_id is not None
    assert plan.baseline_id is not None
    assert plan.backtest_result_id is not None
    assert plan.walk_forward_validation_id is not None
    evaluation, entry = evaluate_leaderboard_gate(
        repository=repository,
        created_at=created_at,
        strategy_card_id=plan.strategy_card_id,
        trial_id=plan.passed_trial_id,
        split_manifest_id=plan.split_manifest_id,
        cost_model_id=plan.cost_model_id,
        baseline_id=plan.baseline_id,
        backtest_result_id=plan.backtest_result_id,
        walk_forward_validation_id=plan.walk_forward_validation_id,
        event_edge_evaluation_id=None,
    )
    return [evaluation.evaluation_id, entry.entry_id]


def _can_execute_shadow_observation_task(
    *,
    task,
    shadow_window_start: datetime | None,
    shadow_window_end: datetime | None,
    shadow_observed_return: float | None,
    shadow_benchmark_return: float | None,
    derive_shadow_returns_from_candles: bool,
) -> bool:
    return (
        task.task_id == "record_paper_shadow_outcome"
        and task.status == "blocked"
        and task.blocked_reason == "shadow_window_observation_required"
        and shadow_window_start is not None
        and shadow_window_end is not None
        and (
            derive_shadow_returns_from_candles
            or (shadow_observed_return is not None and shadow_benchmark_return is not None)
        )
    )


def _execute_record_paper_shadow_outcome(
    *,
    repository: ArtifactRepository,
    storage_dir: Path,
    plan: RevisionRetestTaskPlan,
    created_at: datetime,
    shadow_window_start: datetime | None,
    shadow_window_end: datetime | None,
    shadow_observed_return: float | None,
    shadow_benchmark_return: float | None,
    shadow_max_adverse_excursion: float | None,
    shadow_turnover: float | None,
    shadow_note: str | None,
    derive_shadow_returns_from_candles: bool,
) -> list[str]:
    if plan.leaderboard_entry_id is None:
        raise ValueError("revision_retest_leaderboard_entry_missing")
    missing = []
    if shadow_window_start is None:
        missing.append("shadow_window_start")
    if shadow_window_end is None:
        missing.append("shadow_window_end")
    if shadow_observed_return is None and not derive_shadow_returns_from_candles:
        missing.append("shadow_observed_return")
    if shadow_benchmark_return is None and not derive_shadow_returns_from_candles:
        missing.append("shadow_benchmark_return")
    if missing:
        raise ValueError(f"revision_retest_shadow_observation_inputs_missing:{','.join(missing)}")
    assert shadow_window_start is not None
    assert shadow_window_end is not None
    if shadow_window_end <= shadow_window_start:
        raise ValueError("revision_retest_shadow_window_invalid")
    if shadow_window_end > created_at:
        raise ValueError("revision_retest_shadow_window_not_complete")
    if derive_shadow_returns_from_candles:
        derived = _derive_shadow_observation_from_stored_candles(
            repository=repository,
            storage_dir=storage_dir,
            symbol=plan.symbol,
            created_at=created_at,
            window_start=shadow_window_start,
            window_end=shadow_window_end,
        )
        shadow_observed_return = derived.strategy_return
        shadow_benchmark_return = derived.benchmark_return
        shadow_max_adverse_excursion = (
            derived.max_drawdown
            if shadow_max_adverse_excursion is None
            else shadow_max_adverse_excursion
        )
        shadow_turnover = derived.turnover if shadow_turnover is None else shadow_turnover
        shadow_note = (
            "derived_from_stored_candles"
            if shadow_note is None
            else f"{shadow_note}; derived_from_stored_candles"
        )
    assert shadow_observed_return is not None
    assert shadow_benchmark_return is not None
    outcome = record_paper_shadow_outcome(
        repository=repository,
        created_at=created_at,
        leaderboard_entry_id=plan.leaderboard_entry_id,
        window_start=shadow_window_start,
        window_end=shadow_window_end,
        observed_return=shadow_observed_return,
        benchmark_return=shadow_benchmark_return,
        max_adverse_excursion=shadow_max_adverse_excursion,
        turnover=shadow_turnover,
        note=shadow_note,
    )
    return [outcome.outcome_id]


def _derive_shadow_observation_from_stored_candles(
    *,
    repository: ArtifactRepository,
    storage_dir: Path,
    symbol: str,
    created_at: datetime,
    window_start: datetime,
    window_end: datetime,
) -> BacktestResult:
    all_symbol_candles = [
        candle
        for candle in repository.load_market_candles()
        if candle.symbol == symbol
    ]
    all_symbol_candles.sort(key=lambda candle: candle.timestamp)
    candles = [
        candle
        for candle in all_symbol_candles
        if window_start <= candle.timestamp <= window_end
    ]
    if (
        len(candles) < 2
        or candles[0].timestamp != window_start
        or candles[-1].timestamp != window_end
    ):
        raise ValueError("revision_retest_shadow_window_candles_incomplete")
    _ensure_complete_shadow_candle_window(candles, all_symbol_candles=all_symbol_candles)
    return run_backtest(
        storage_dir=storage_dir,
        symbol=symbol,
        start=window_start,
        end=window_end,
        created_at=created_at,
    ).result


def _ensure_complete_shadow_candle_window(
    candles: list[MarketCandleRecord],
    *,
    all_symbol_candles: list[MarketCandleRecord],
) -> None:
    cadence = _infer_candle_cadence(all_symbol_candles)
    if cadence is None or cadence <= timedelta(0):
        raise ValueError("revision_retest_shadow_window_candles_incomplete")
    timestamps = {candle.timestamp for candle in candles}
    current = candles[0].timestamp
    while current <= candles[-1].timestamp:
        if current not in timestamps:
            raise ValueError("revision_retest_shadow_window_candles_incomplete")
        current += cadence


def _infer_candle_cadence(candles: list[MarketCandleRecord]) -> timedelta | None:
    timestamps = sorted({candle.timestamp for candle in candles})
    deltas = [
        current - previous
        for previous, current in zip(timestamps, timestamps[1:])
        if current > previous
    ]
    if not deltas:
        return None
    return min(deltas)


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


def _retest_evidence_context(plan: RevisionRetestTaskPlan) -> str:
    trial_id = plan.pending_trial_id or plan.passed_trial_id or "no-trial"
    return f"revision_retest:{plan.strategy_card_id}:{trial_id}:{plan.source_outcome_id}"
