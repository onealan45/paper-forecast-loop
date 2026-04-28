from __future__ import annotations

from datetime import datetime

from forecast_loop.models import ExperimentBudget, ExperimentTrial, StrategyCard
from forecast_loop.storage import ArtifactRepository


def register_strategy_card(
    *,
    repository: ArtifactRepository,
    created_at: datetime,
    strategy_name: str,
    strategy_family: str,
    version: str,
    symbols: list[str],
    hypothesis: str,
    signal_description: str,
    entry_rules: list[str],
    exit_rules: list[str],
    risk_rules: list[str],
    parameters: dict[str, object] | None = None,
    data_requirements: list[str] | None = None,
    feature_snapshot_ids: list[str] | None = None,
    backtest_result_ids: list[str] | None = None,
    walk_forward_validation_ids: list[str] | None = None,
    event_edge_evaluation_ids: list[str] | None = None,
    parent_card_id: str | None = None,
    author: str = "codex",
    status: str = "ACTIVE",
) -> StrategyCard:
    parameters = parameters or {}
    card_id = StrategyCard.build_id(
        strategy_name=strategy_name,
        strategy_family=strategy_family,
        version=version,
        symbols=symbols,
        hypothesis=hypothesis,
        parameters=parameters,
    )
    for existing in repository.load_strategy_cards():
        if existing.card_id == card_id:
            return existing

    card = StrategyCard(
        card_id=card_id,
        created_at=created_at,
        strategy_name=strategy_name,
        strategy_family=strategy_family,
        version=version,
        status=status,
        symbols=symbols,
        hypothesis=hypothesis,
        signal_description=signal_description,
        entry_rules=entry_rules,
        exit_rules=exit_rules,
        risk_rules=risk_rules,
        parameters=parameters,
        data_requirements=data_requirements or [],
        feature_snapshot_ids=feature_snapshot_ids or [],
        backtest_result_ids=backtest_result_ids or [],
        walk_forward_validation_ids=walk_forward_validation_ids or [],
        event_edge_evaluation_ids=event_edge_evaluation_ids or [],
        parent_card_id=parent_card_id,
        author=author,
        decision_basis="strategy_card_registered",
    )
    repository.save_strategy_card(card)
    return card


def record_experiment_trial(
    *,
    repository: ArtifactRepository,
    created_at: datetime,
    strategy_card_id: str,
    trial_index: int,
    status: str,
    symbol: str,
    max_trials: int,
    seed: int | None = None,
    dataset_id: str | None = None,
    backtest_result_id: str | None = None,
    walk_forward_validation_id: str | None = None,
    event_edge_evaluation_id: str | None = None,
    prompt_hash: str | None = None,
    code_hash: str | None = None,
    parameters: dict[str, object] | None = None,
    metric_summary: dict[str, object] | None = None,
    failure_reason: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> ExperimentTrial:
    parameters = parameters or {}
    status = status.upper()
    existing_trials = repository.load_experiment_trials()
    consumed_trial_indexes = _consumed_trial_indexes(existing_trials, strategy_card_id)
    consumed_trials = len(consumed_trial_indexes)
    final_statuses = {"PASSED", "FAILED", "ABORTED", "INVALID"}
    consumes_budget = status in final_statuses and trial_index not in consumed_trial_indexes
    budget_exhausted = consumes_budget and consumed_trials >= max_trials
    recorded_status = "ABORTED" if budget_exhausted else status
    recorded_failure_reason = "trial_budget_exhausted" if budget_exhausted else failure_reason

    trial = ExperimentTrial(
        trial_id=ExperimentTrial.build_id(
            strategy_card_id=strategy_card_id,
            trial_index=trial_index,
            status=recorded_status,
            seed=seed,
            prompt_hash=prompt_hash,
            code_hash=code_hash,
            parameters=parameters,
        ),
        created_at=created_at,
        strategy_card_id=strategy_card_id,
        trial_index=trial_index,
        status=recorded_status,
        symbol=symbol,
        seed=seed,
        dataset_id=dataset_id,
        backtest_result_id=backtest_result_id,
        walk_forward_validation_id=walk_forward_validation_id,
        event_edge_evaluation_id=event_edge_evaluation_id,
        prompt_hash=prompt_hash,
        code_hash=code_hash,
        parameters=parameters,
        metric_summary=metric_summary or {},
        failure_reason=recorded_failure_reason,
        started_at=started_at or created_at,
        completed_at=completed_at or created_at,
        decision_basis="experiment_trial_recorded",
    )
    repository.save_experiment_trial(trial)

    used_trials = consumed_trials
    if consumes_budget and not budget_exhausted:
        used_trials += 1
    remaining_trials = max(0, max_trials - used_trials)
    budget_status = "EXHAUSTED" if remaining_trials == 0 else "OPEN"
    budget = ExperimentBudget(
        budget_id=ExperimentBudget.build_id(
            strategy_card_id=strategy_card_id,
            max_trials=max_trials,
            used_trials=used_trials,
            remaining_trials=remaining_trials,
            status=budget_status,
        ),
        created_at=created_at,
        strategy_card_id=strategy_card_id,
        max_trials=max_trials,
        used_trials=used_trials,
        remaining_trials=remaining_trials,
        status=budget_status,
        budget_scope="strategy_card",
        decision_basis="experiment_budget_snapshot",
    )
    repository.save_experiment_budget(budget)
    return trial


def _consumed_trial_indexes(trials: list[ExperimentTrial], strategy_card_id: str) -> set[int]:
    consumed_indexes: set[int] = set()
    for trial in trials:
        if trial.strategy_card_id != strategy_card_id:
            continue
        if trial.status in {"PENDING", "RUNNING"}:
            continue
        if trial.status == "ABORTED" and trial.failure_reason == "trial_budget_exhausted":
            continue
        consumed_indexes.add(trial.trial_index)
    return consumed_indexes
