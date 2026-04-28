from __future__ import annotations

from datetime import datetime

from forecast_loop.models import (
    BacktestResult,
    BaselineEvaluation,
    CostModelSnapshot,
    EventEdgeEvaluation,
    ExperimentTrial,
    LeaderboardEntry,
    LockedEvaluationResult,
    SplitManifest,
)
from forecast_loop.storage import ArtifactRepository


LEADERBOARD_RULES_VERSION = "pr7-v1"


def lock_evaluation_protocol(
    *,
    repository: ArtifactRepository,
    created_at: datetime,
    strategy_card_id: str,
    dataset_id: str,
    symbol: str,
    train_start: datetime,
    train_end: datetime,
    validation_start: datetime,
    validation_end: datetime,
    holdout_start: datetime,
    holdout_end: datetime,
    embargo_hours: int = 24,
    fee_bps: float = 5.0,
    slippage_bps: float = 10.0,
    max_turnover: float = 5.0,
    max_drawdown: float = 0.10,
    baseline_suite_version: str = "m4b-v1",
    locked_by: str = "codex",
) -> tuple[SplitManifest, CostModelSnapshot]:
    manifest = SplitManifest(
        manifest_id=SplitManifest.build_id(
            symbol=symbol,
            strategy_card_id=strategy_card_id,
            dataset_id=dataset_id,
            train_start=train_start,
            train_end=train_end,
            validation_start=validation_start,
            validation_end=validation_end,
            holdout_start=holdout_start,
            holdout_end=holdout_end,
            embargo_hours=embargo_hours,
        ),
        created_at=created_at,
        symbol=symbol,
        strategy_card_id=strategy_card_id,
        dataset_id=dataset_id,
        train_start=train_start,
        train_end=train_end,
        validation_start=validation_start,
        validation_end=validation_end,
        holdout_start=holdout_start,
        holdout_end=holdout_end,
        embargo_hours=embargo_hours,
        status="LOCKED",
        locked_by=locked_by,
        decision_basis="locked_evaluation_protocol",
    )
    cost_model = CostModelSnapshot(
        cost_model_id=CostModelSnapshot.build_id(
            symbol=symbol,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            max_turnover=max_turnover,
            max_drawdown=max_drawdown,
            baseline_suite_version=baseline_suite_version,
        ),
        created_at=created_at,
        symbol=symbol,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        max_turnover=max_turnover,
        max_drawdown=max_drawdown,
        baseline_suite_version=baseline_suite_version,
        status="LOCKED",
        decision_basis="locked_cost_model_snapshot",
    )
    repository.save_split_manifest(manifest)
    repository.save_cost_model_snapshot(cost_model)
    return manifest, cost_model


def evaluate_leaderboard_gate(
    *,
    repository: ArtifactRepository,
    created_at: datetime,
    strategy_card_id: str,
    trial_id: str,
    split_manifest_id: str,
    cost_model_id: str,
    baseline_id: str,
    backtest_result_id: str,
    walk_forward_validation_id: str,
    event_edge_evaluation_id: str | None = None,
) -> tuple[LockedEvaluationResult, LeaderboardEntry]:
    cards = {card.card_id: card for card in repository.load_strategy_cards()}
    trials = {trial.trial_id: trial for trial in repository.load_experiment_trials()}
    split_manifests = {manifest.manifest_id: manifest for manifest in repository.load_split_manifests()}
    cost_models = {cost.cost_model_id: cost for cost in repository.load_cost_model_snapshots()}
    baselines = {baseline.baseline_id: baseline for baseline in repository.load_baseline_evaluations()}
    backtests = {result.result_id: result for result in repository.load_backtest_results()}
    walk_forwards = {
        validation.validation_id: validation
        for validation in repository.load_walk_forward_validations()
    }
    event_edges = {
        evaluation.evaluation_id: evaluation
        for evaluation in repository.load_event_edge_evaluations()
    }

    blocked: list[str] = []
    card = cards.get(strategy_card_id)
    trial = trials.get(trial_id)
    split = split_manifests.get(split_manifest_id)
    cost_model = cost_models.get(cost_model_id)
    baseline = baselines.get(baseline_id)
    backtest = backtests.get(backtest_result_id)
    walk_forward = walk_forwards.get(walk_forward_validation_id)
    event_edge = event_edges.get(event_edge_evaluation_id) if event_edge_evaluation_id else None

    if card is None:
        blocked.append("strategy_card_missing")
    if trial is None:
        blocked.append("experiment_trial_missing")
    elif trial.strategy_card_id != strategy_card_id:
        blocked.append("experiment_trial_strategy_card_mismatch")
    elif trial.status != "PASSED":
        blocked.append("experiment_trial_not_passed")
    if split is None:
        blocked.append("split_manifest_missing")
    elif split.status != "LOCKED":
        blocked.append("split_manifest_not_locked")
    if cost_model is None:
        blocked.append("cost_model_missing")
    elif cost_model.status != "LOCKED":
        blocked.append("cost_model_not_locked")
    if baseline is None:
        blocked.append("baseline_missing")
    else:
        _check_baseline(baseline, blocked)
    if backtest is None:
        blocked.append("backtest_result_missing")
    if walk_forward is None:
        blocked.append("walk_forward_validation_missing")
    if event_edge_evaluation_id and event_edge is None:
        blocked.append("event_edge_evaluation_missing")
    elif event_edge is not None and not event_edge.passed:
        blocked.append("event_edge_not_passed")
    _check_artifact_alignment(
        card=card,
        trial=trial,
        split=split,
        cost_model=cost_model,
        baseline=baseline,
        backtest=backtest,
        walk_forward=walk_forward,
        event_edge=event_edge,
        strategy_card_id=strategy_card_id,
        backtest_result_id=backtest_result_id,
        walk_forward_validation_id=walk_forward_validation_id,
        event_edge_evaluation_id=event_edge_evaluation_id,
        blocked=blocked,
    )

    gate_metrics = _gate_metrics(
        baseline=baseline,
        backtest=backtest,
        walk_forward=walk_forward,
        event_edge=event_edge,
    )
    if backtest is not None and cost_model is not None:
        _check_backtest(backtest, cost_model, blocked)
    if walk_forward is not None:
        _check_walk_forward(walk_forward, blocked)

    rankable = not blocked
    alpha_score = _alpha_score(gate_metrics) if rankable else None
    evaluation = LockedEvaluationResult(
        evaluation_id=LockedEvaluationResult.build_id(
            strategy_card_id=strategy_card_id,
            trial_id=trial_id,
            split_manifest_id=split_manifest_id,
            cost_model_id=cost_model_id,
            baseline_id=baseline_id,
            backtest_result_id=backtest_result_id,
            walk_forward_validation_id=walk_forward_validation_id,
            event_edge_evaluation_id=event_edge_evaluation_id,
        ),
        created_at=created_at,
        strategy_card_id=strategy_card_id,
        trial_id=trial_id,
        split_manifest_id=split_manifest_id,
        cost_model_id=cost_model_id,
        baseline_id=baseline_id,
        backtest_result_id=backtest_result_id,
        walk_forward_validation_id=walk_forward_validation_id,
        event_edge_evaluation_id=event_edge_evaluation_id,
        passed=rankable,
        rankable=rankable,
        alpha_score=alpha_score,
        blocked_reasons=blocked,
        gate_metrics=gate_metrics,
        decision_basis="locked_evaluation_gate",
    )
    entry = LeaderboardEntry(
        entry_id=LeaderboardEntry.build_id(
            strategy_card_id=strategy_card_id,
            evaluation_id=evaluation.evaluation_id,
            trial_id=trial_id,
            leaderboard_rules_version=LEADERBOARD_RULES_VERSION,
        ),
        created_at=created_at,
        strategy_card_id=strategy_card_id,
        evaluation_id=evaluation.evaluation_id,
        trial_id=trial_id,
        symbol=_symbol(trial=trial, baseline=baseline, backtest=backtest, split=split),
        rankable=rankable,
        alpha_score=alpha_score,
        promotion_stage="CANDIDATE" if rankable else "BLOCKED",
        blocked_reasons=blocked,
        leaderboard_rules_version=LEADERBOARD_RULES_VERSION,
        decision_basis="leaderboard_hard_gate",
    )
    repository.save_locked_evaluation_result(evaluation)
    repository.save_leaderboard_entry(entry)
    return evaluation, entry


def _check_baseline(baseline: BaselineEvaluation, blocked: list[str]) -> None:
    if baseline.sample_size < 2:
        blocked.append("baseline_sample_too_low")
    if baseline.model_edge <= 0:
        blocked.append("baseline_edge_not_positive")
    if baseline.evidence_grade in {"D", "INSUFFICIENT"}:
        blocked.append("baseline_evidence_grade_too_weak")


def _check_artifact_alignment(
    *,
    card,
    trial: ExperimentTrial | None,
    split: SplitManifest | None,
    cost_model: CostModelSnapshot | None,
    baseline: BaselineEvaluation | None,
    backtest: BacktestResult | None,
    walk_forward,
    event_edge: EventEdgeEvaluation | None,
    strategy_card_id: str,
    backtest_result_id: str,
    walk_forward_validation_id: str,
    event_edge_evaluation_id: str | None,
    blocked: list[str],
) -> None:
    if card is not None and trial is not None and trial.symbol not in card.symbols:
        blocked.append("strategy_card_symbol_mismatch")
    if split is not None:
        if split.strategy_card_id != strategy_card_id:
            blocked.append("split_manifest_strategy_card_mismatch")
        if trial is not None:
            if trial.dataset_id is None:
                blocked.append("experiment_trial_dataset_missing")
            elif split.dataset_id != trial.dataset_id:
                blocked.append("split_manifest_dataset_mismatch")
            if split.symbol != trial.symbol:
                blocked.append("split_manifest_symbol_mismatch")
    if cost_model is not None and trial is not None and cost_model.symbol != trial.symbol:
        blocked.append("cost_model_symbol_mismatch")
    if baseline is not None and trial is not None and baseline.symbol != trial.symbol:
        blocked.append("baseline_symbol_mismatch")
    if backtest is not None and trial is not None:
        if trial.backtest_result_id != backtest_result_id:
            blocked.append("experiment_trial_backtest_result_mismatch")
        if backtest.symbol != trial.symbol:
            blocked.append("backtest_symbol_mismatch")
    if walk_forward is not None and trial is not None:
        if trial.walk_forward_validation_id != walk_forward_validation_id:
            blocked.append("experiment_trial_walk_forward_validation_mismatch")
        if walk_forward.symbol != trial.symbol:
            blocked.append("walk_forward_symbol_mismatch")
        if backtest is not None and backtest.result_id not in walk_forward.backtest_result_ids:
            blocked.append("walk_forward_backtest_result_mismatch")
    if event_edge_evaluation_id is not None and trial is not None:
        if trial.event_edge_evaluation_id != event_edge_evaluation_id:
            blocked.append("experiment_trial_event_edge_evaluation_mismatch")
        if event_edge is not None and event_edge.symbol != trial.symbol:
            blocked.append("event_edge_symbol_mismatch")


def _check_backtest(backtest: BacktestResult, cost_model: CostModelSnapshot, blocked: list[str]) -> None:
    if backtest.strategy_return <= backtest.benchmark_return:
        blocked.append("holdout_excess_not_positive")
    if backtest.max_drawdown > cost_model.max_drawdown:
        blocked.append("drawdown_limit_exceeded")
    if backtest.turnover > cost_model.max_turnover:
        blocked.append("turnover_limit_exceeded")


def _check_walk_forward(walk_forward, blocked: list[str]) -> None:
    if walk_forward.average_excess_return <= 0:
        blocked.append("walk_forward_excess_not_positive")
    if walk_forward.overfit_risk_flags:
        blocked.append("overfit_risk_flagged")


def _gate_metrics(
    *,
    baseline: BaselineEvaluation | None,
    backtest: BacktestResult | None,
    walk_forward,
    event_edge: EventEdgeEvaluation | None,
) -> dict[str, object]:
    holdout_excess = None
    if backtest is not None:
        holdout_excess = backtest.strategy_return - backtest.benchmark_return
    return {
        "model_edge": baseline.model_edge if baseline else None,
        "holdout_excess_return": holdout_excess,
        "walk_forward_excess_return": walk_forward.average_excess_return if walk_forward else None,
        "event_edge_after_cost": event_edge.average_excess_return_after_costs if event_edge else None,
    }


def _alpha_score(metrics: dict[str, object]) -> float:
    values = [
        value
        for value in [
            metrics.get("model_edge"),
            metrics.get("holdout_excess_return"),
            metrics.get("walk_forward_excess_return"),
            metrics.get("event_edge_after_cost"),
        ]
        if isinstance(value, int | float)
    ]
    return round(sum(float(value) for value in values), 8)


def _symbol(
    *,
    trial: ExperimentTrial | None,
    baseline: BaselineEvaluation | None,
    backtest: BacktestResult | None,
    split: SplitManifest | None,
) -> str:
    if trial is not None:
        return trial.symbol
    if baseline is not None:
        return baseline.symbol
    if backtest is not None:
        return backtest.symbol
    if split is not None:
        return split.symbol
    return "UNKNOWN"
