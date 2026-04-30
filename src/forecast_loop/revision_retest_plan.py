from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from forecast_loop.models import (
    BacktestResult,
    BaselineEvaluation,
    CostModelSnapshot,
    ExperimentTrial,
    LeaderboardEntry,
    LockedEvaluationResult,
    PaperShadowOutcome,
    ResearchDataset,
    SplitManifest,
    StrategyCard,
    WalkForwardValidation,
)
from forecast_loop.revision_retest import RETEST_PROTOCOL_VERSION
from forecast_loop.storage import ArtifactRepository
from forecast_loop.strategy_evolution import REPLACEMENT_DECISION_BASIS
from forecast_loop.strategy_research import REVISION_CARD_BASIS


@dataclass(frozen=True, slots=True)
class RevisionRetestTask:
    task_id: str
    title: str
    status: str
    required_artifact: str
    artifact_id: str | None
    command_args: list[str] | None
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
            "blocked_reason": self.blocked_reason,
            "missing_inputs": list(self.missing_inputs),
            "rationale": self.rationale,
        }


@dataclass(frozen=True, slots=True)
class RevisionRetestTaskPlan:
    symbol: str
    strategy_card_id: str
    source_outcome_id: str
    pending_trial_id: str | None
    passed_trial_id: str | None
    dataset_id: str | None
    split_manifest_id: str | None
    cost_model_id: str | None
    baseline_id: str | None
    backtest_result_id: str | None
    walk_forward_validation_id: str | None
    locked_evaluation_id: str | None
    leaderboard_entry_id: str | None
    paper_shadow_outcome_id: str | None
    next_task_id: str | None
    tasks: list[RevisionRetestTask]

    def task_by_id(self, task_id: str) -> RevisionRetestTask:
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        raise KeyError(task_id)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "strategy_card_id": self.strategy_card_id,
            "source_outcome_id": self.source_outcome_id,
            "pending_trial_id": self.pending_trial_id,
            "passed_trial_id": self.passed_trial_id,
            "dataset_id": self.dataset_id,
            "split_manifest_id": self.split_manifest_id,
            "cost_model_id": self.cost_model_id,
            "baseline_id": self.baseline_id,
            "backtest_result_id": self.backtest_result_id,
            "walk_forward_validation_id": self.walk_forward_validation_id,
            "locked_evaluation_id": self.locked_evaluation_id,
            "leaderboard_entry_id": self.leaderboard_entry_id,
            "paper_shadow_outcome_id": self.paper_shadow_outcome_id,
            "next_task_id": self.next_task_id,
            "tasks": [task.to_dict() for task in self.tasks],
        }


def build_revision_retest_task_plan(
    *,
    repository: ArtifactRepository,
    storage_dir: Path | str | None,
    symbol: str,
    revision_card_id: str | None = None,
) -> RevisionRetestTaskPlan:
    symbol = symbol.upper()
    storage = Path(storage_dir) if storage_dir is not None else None
    card = _revision_card(
        repository.load_strategy_cards(),
        symbol=symbol,
        revision_card_id=revision_card_id,
    )
    source_outcome = _source_outcome(
        repository.load_paper_shadow_outcomes(),
        cards=repository.load_strategy_cards(),
        card=card,
        symbol=symbol,
    )
    research_dataset = _latest_research_dataset(repository.load_research_datasets(), symbol)
    experiment_trials = repository.load_experiment_trials()
    backtest_results = repository.load_backtest_results()
    walk_forward_validations = repository.load_walk_forward_validations()
    pending_trial = _latest_retest_trial(
        experiment_trials,
        card,
        source_outcome,
        "PENDING",
        symbol=symbol,
    )
    pending_dataset_id = pending_trial.dataset_id if pending_trial is not None else None
    pending_split = _latest_split_manifest(
        repository.load_split_manifests(),
        card=card,
        symbol=symbol,
        dataset_id=pending_dataset_id,
    )
    passed_trial = _latest_valid_passed_retest_trial(
        experiment_trials,
        backtest_results=backtest_results,
        walk_forward_validations=walk_forward_validations,
        split_manifests=repository.load_split_manifests(),
        card=card,
        source_outcome=source_outcome,
        symbol=symbol,
    )
    dataset_id = _first_present(
        passed_trial.dataset_id if passed_trial is not None else None,
        pending_trial.dataset_id if pending_trial is not None else None,
        research_dataset.dataset_id if research_dataset is not None else None,
    )
    split = _latest_split_manifest(
        repository.load_split_manifests(),
        card=card,
        symbol=symbol,
        dataset_id=dataset_id,
    )
    if split is None:
        split = pending_split
    cost_model = _latest_cost_model(repository.load_cost_model_snapshots(), symbol)
    baseline = _latest_baseline(repository.load_baseline_evaluations(), symbol)
    backtest = _selected_backtest(
        backtest_results,
        passed_trial=passed_trial,
        split=split,
        symbol=symbol,
    )
    walk_forward = _selected_walk_forward(
        walk_forward_validations,
        passed_trial=passed_trial,
        split=split,
        symbol=symbol,
    )
    locked_evaluation = _latest_locked_evaluation(
        repository.load_locked_evaluation_results(),
        card=card,
        trial=passed_trial,
        split=split,
        cost_model=cost_model,
        baseline=baseline,
        backtest=backtest,
        walk_forward=walk_forward,
    )
    leaderboard_entry = _latest_leaderboard_entry(
        repository.load_leaderboard_entries(),
        card=card,
        trial=passed_trial,
        evaluation=locked_evaluation,
        symbol=symbol,
    )
    shadow_outcome = _latest_shadow_outcome(
        repository.load_paper_shadow_outcomes(),
        leaderboard_entry=leaderboard_entry,
        symbol=symbol,
    )
    tasks = _build_tasks(
        storage=storage,
        symbol=symbol,
        card=card,
        source_outcome=source_outcome,
        pending_trial=pending_trial,
        passed_trial=passed_trial,
        dataset_id=dataset_id,
        split=split,
        cost_model=cost_model,
        baseline=baseline,
        backtest=backtest,
        walk_forward=walk_forward,
        locked_evaluation=locked_evaluation,
        leaderboard_entry=leaderboard_entry,
        shadow_outcome=shadow_outcome,
    )
    next_task = next((task for task in tasks if task.status != "completed"), None)
    return RevisionRetestTaskPlan(
        symbol=symbol,
        strategy_card_id=card.card_id,
        source_outcome_id=source_outcome.outcome_id,
        pending_trial_id=pending_trial.trial_id if pending_trial else None,
        passed_trial_id=passed_trial.trial_id if passed_trial else None,
        dataset_id=dataset_id,
        split_manifest_id=split.manifest_id if split else None,
        cost_model_id=cost_model.cost_model_id if cost_model else None,
        baseline_id=baseline.baseline_id if baseline else None,
        backtest_result_id=backtest.result_id if backtest else None,
        walk_forward_validation_id=walk_forward.validation_id if walk_forward else None,
        locked_evaluation_id=locked_evaluation.evaluation_id if locked_evaluation else None,
        leaderboard_entry_id=leaderboard_entry.entry_id if leaderboard_entry else None,
        paper_shadow_outcome_id=shadow_outcome.outcome_id if shadow_outcome else None,
        next_task_id=next_task.task_id if next_task else None,
        tasks=tasks,
    )


def _build_tasks(
    *,
    storage: Path | None,
    symbol: str,
    card: StrategyCard,
    source_outcome: PaperShadowOutcome,
    pending_trial: ExperimentTrial | None,
    passed_trial: ExperimentTrial | None,
    dataset_id: str | None,
    split: SplitManifest | None,
    cost_model: CostModelSnapshot | None,
    baseline: BaselineEvaluation | None,
    backtest: BacktestResult | None,
    walk_forward: WalkForwardValidation | None,
    locked_evaluation: LockedEvaluationResult | None,
    leaderboard_entry: LeaderboardEntry | None,
    shadow_outcome: PaperShadowOutcome | None,
) -> list[RevisionRetestTask]:
    tasks = [
        _scaffold_task(
            storage=storage,
            symbol=symbol,
            card=card,
            pending_trial=pending_trial,
            passed_trial=passed_trial,
            dataset_id=dataset_id,
        ),
        _lock_protocol_task(
            storage=storage,
            symbol=symbol,
            card=card,
            trial=passed_trial or pending_trial,
            dataset_id=dataset_id,
            split=split,
            cost_model=cost_model,
        ),
        _baseline_task(storage=storage, symbol=symbol, baseline=baseline),
        _backtest_task(storage=storage, symbol=symbol, split=split, backtest=backtest),
        _walk_forward_task(storage=storage, symbol=symbol, split=split, walk_forward=walk_forward),
        _passed_trial_task(
            storage=storage,
            symbol=symbol,
            card=card,
            source_outcome=source_outcome,
            pending_trial=pending_trial,
            passed_trial=passed_trial,
            dataset_id=dataset_id,
            backtest=backtest,
            walk_forward=walk_forward,
        ),
        _leaderboard_gate_task(
            storage=storage,
            card=card,
            trial=passed_trial,
            split=split,
            cost_model=cost_model,
            baseline=baseline,
            backtest=backtest,
            walk_forward=walk_forward,
            locked_evaluation=locked_evaluation,
        ),
        _paper_shadow_task(
            storage=storage,
            leaderboard_entry=leaderboard_entry,
            shadow_outcome=shadow_outcome,
        ),
    ]
    return tasks


def _scaffold_task(
    *,
    storage: Path | None,
    symbol: str,
    card: StrategyCard,
    pending_trial: ExperimentTrial | None,
    passed_trial: ExperimentTrial | None,
    dataset_id: str | None,
) -> RevisionRetestTask:
    trial = pending_trial or passed_trial
    if trial is not None:
        return _task(
            "create_revision_retest_scaffold",
            "Create revision retest scaffold",
            "completed",
            "experiment_trial",
            trial.trial_id,
            None,
            None,
            [],
            "A revision retest trial already exists for the source paper shadow outcome.",
        )
    if dataset_id is None or storage is None:
        missing = []
        if dataset_id is None:
            missing.append("dataset_id")
        if storage is None:
            missing.append("storage_dir")
        return _task(
            "create_revision_retest_scaffold",
            "Create revision retest scaffold",
            "blocked",
            "experiment_trial",
            None,
            None,
            "dataset_id_required",
            missing,
            "A retest trial needs a concrete research dataset before it can be scaffolded.",
        )
    return _task(
        "create_revision_retest_scaffold",
        "Create revision retest scaffold",
        "ready",
        "experiment_trial",
        None,
        _base_command(storage)
        + [
            "create-revision-retest-scaffold",
            "--storage-dir",
            str(storage),
            "--revision-card-id",
            card.card_id,
            "--symbol",
            symbol,
            "--dataset-id",
            dataset_id,
            "--max-trials",
            "20",
        ],
        None,
        [],
        "A DRAFT revision exists and a research dataset is available.",
    )


def _lock_protocol_task(
    *,
    storage: Path | None,
    symbol: str,
    card: StrategyCard,
    trial: ExperimentTrial | None,
    dataset_id: str | None,
    split: SplitManifest | None,
    cost_model: CostModelSnapshot | None,
) -> RevisionRetestTask:
    if split is not None and cost_model is not None:
        return _task(
            "lock_evaluation_protocol",
            "Lock evaluation protocol",
            "completed",
            "split_manifest",
            split.manifest_id,
            None,
            None,
            [],
            "A locked split manifest and cost model are available for the retest.",
        )
    if trial is None:
        return _task(
            "lock_evaluation_protocol",
            "Lock evaluation protocol",
            "blocked",
            "split_manifest",
            split.manifest_id if split else None,
            None,
            "experiment_trial_missing",
            ["experiment_trial"],
            "The split protocol should be locked after the revision retest trial exists.",
        )
    if dataset_id is None:
        return _task(
            "lock_evaluation_protocol",
            "Lock evaluation protocol",
            "blocked",
            "split_manifest",
            split.manifest_id if split else None,
            None,
            "dataset_id_missing",
            ["dataset_id"],
            "The split protocol needs the same dataset ID as the retest trial.",
        )
    if split is None or storage is None:
        missing = [
            "train_start",
            "train_end",
            "validation_start",
            "validation_end",
            "holdout_start",
            "holdout_end",
        ]
        if storage is None:
            missing.append("storage_dir")
        return _task(
            "lock_evaluation_protocol",
            "Lock evaluation protocol",
            "blocked",
            "split_manifest",
            None,
            None,
            "split_window_inputs_required",
            missing,
            "The planner refuses to invent train, validation, or holdout windows.",
        )
    return _task(
        "lock_evaluation_protocol",
        "Lock evaluation protocol",
        "ready",
        "cost_model_snapshot",
        None,
        _lock_protocol_command(storage=storage, symbol=symbol, card=card, dataset_id=dataset_id, split=split),
        None,
        [],
        "The split exists but a matching locked cost model snapshot is missing.",
    )


def _baseline_task(
    *,
    storage: Path | None,
    symbol: str,
    baseline: BaselineEvaluation | None,
) -> RevisionRetestTask:
    if baseline is not None:
        return _task(
            "generate_baseline_evaluation",
            "Generate baseline evaluation",
            "completed",
            "baseline_evaluation",
            baseline.baseline_id,
            None,
            None,
            [],
            "A baseline evaluation already exists for the symbol.",
        )
    if storage is None:
        return _task(
            "generate_baseline_evaluation",
            "Generate baseline evaluation",
            "blocked",
            "baseline_evaluation",
            None,
            None,
            "storage_dir_required",
            ["storage_dir"],
            "The existing decide command writes baseline evaluation evidence.",
        )
    return _task(
        "generate_baseline_evaluation",
        "Generate baseline evaluation",
        "ready",
        "baseline_evaluation",
        None,
        _base_command(storage)
        + [
            "decide",
            "--storage-dir",
            str(storage),
            "--symbol",
            symbol,
            "--horizon-hours",
            "24",
        ],
        None,
        [],
        "The decide command refreshes baseline evidence without running retest evaluation.",
    )


def _backtest_task(
    *,
    storage: Path | None,
    symbol: str,
    split: SplitManifest | None,
    backtest: BacktestResult | None,
) -> RevisionRetestTask:
    if backtest is not None:
        return _task(
            "run_backtest",
            "Run holdout backtest",
            "completed",
            "backtest_result",
            backtest.result_id,
            None,
            None,
            [],
            "A backtest result matching the revision retest window is available.",
        )
    if split is None or storage is None:
        missing = ["split_manifest"] if split is None else []
        if storage is None:
            missing.append("storage_dir")
        return _task(
            "run_backtest",
            "Run holdout backtest",
            "blocked",
            "backtest_result",
            None,
            None,
            "split_manifest_missing",
            missing,
            "The holdout backtest uses the locked split holdout window.",
        )
    return _task(
        "run_backtest",
        "Run holdout backtest",
        "ready",
        "backtest_result",
        None,
        _base_command(storage)
        + [
            "backtest",
            "--storage-dir",
            str(storage),
            "--symbol",
            symbol,
            "--start",
            split.holdout_start.isoformat(),
            "--end",
            split.holdout_end.isoformat(),
        ],
        None,
        [],
        "The locked holdout window is ready for paper backtest evaluation.",
    )


def _walk_forward_task(
    *,
    storage: Path | None,
    symbol: str,
    split: SplitManifest | None,
    walk_forward: WalkForwardValidation | None,
) -> RevisionRetestTask:
    if walk_forward is not None:
        return _task(
            "run_walk_forward",
            "Run walk-forward validation",
            "completed",
            "walk_forward_validation",
            walk_forward.validation_id,
            None,
            None,
            [],
            "A walk-forward validation matching the revision retest window is available.",
        )
    if split is None or storage is None:
        missing = ["split_manifest"] if split is None else []
        if storage is None:
            missing.append("storage_dir")
        return _task(
            "run_walk_forward",
            "Run walk-forward validation",
            "blocked",
            "walk_forward_validation",
            None,
            None,
            "split_manifest_missing",
            missing,
            "Walk-forward validation uses the locked full split window.",
        )
    return _task(
        "run_walk_forward",
        "Run walk-forward validation",
        "ready",
        "walk_forward_validation",
        None,
        _base_command(storage)
        + [
            "walk-forward",
            "--storage-dir",
            str(storage),
            "--symbol",
            symbol,
            "--start",
            split.train_start.isoformat(),
            "--end",
            split.holdout_end.isoformat(),
        ],
        None,
        [],
        "The locked full split window is ready for walk-forward validation.",
    )


def _passed_trial_task(
    *,
    storage: Path | None,
    symbol: str,
    card: StrategyCard,
    source_outcome: PaperShadowOutcome,
    pending_trial: ExperimentTrial | None,
    passed_trial: ExperimentTrial | None,
    dataset_id: str | None,
    backtest: BacktestResult | None,
    walk_forward: WalkForwardValidation | None,
) -> RevisionRetestTask:
    if passed_trial is not None:
        return _task(
            "record_passed_retest_trial",
            "Record passed retest trial",
            "completed",
            "experiment_trial",
            passed_trial.trial_id,
            None,
            None,
            [],
            "A PASSED retest trial already links the required research evidence.",
        )
    missing = []
    if pending_trial is None:
        missing.append("pending_retest_trial")
    if dataset_id is None:
        missing.append("dataset_id")
    if backtest is None:
        missing.append("backtest_result")
    if walk_forward is None:
        missing.append("walk_forward_validation")
    if (
        backtest is not None
        and walk_forward is not None
        and backtest.result_id not in walk_forward.backtest_result_ids
    ):
        missing.append("linked_backtest_walk_forward_pair")
    if storage is None:
        missing.append("storage_dir")
    if missing:
        return _task(
            "record_passed_retest_trial",
            "Record passed retest trial",
            "blocked",
            "experiment_trial",
            None,
            None,
            "missing_retest_results",
            missing,
            "The PASSED trial should only be recorded after backtest and walk-forward evidence exists.",
        )
    assert pending_trial is not None
    assert dataset_id is not None
    assert backtest is not None
    assert walk_forward is not None
    assert storage is not None
    command = _base_command(storage) + [
        "record-experiment-trial",
        "--storage-dir",
        str(storage),
        "--strategy-card-id",
        card.card_id,
        "--trial-index",
        str(pending_trial.trial_index),
        "--status",
        "PASSED",
        "--symbol",
        symbol,
        "--max-trials",
        str(pending_trial.parameters.get("max_trials", 20)),
        "--dataset-id",
        dataset_id,
        "--backtest-result-id",
        backtest.result_id,
        "--walk-forward-validation-id",
        walk_forward.validation_id,
        "--parameter",
        f"revision_retest_protocol={RETEST_PROTOCOL_VERSION}",
        "--parameter",
        f"revision_retest_source_card_id={card.card_id}",
        "--parameter",
        f"revision_source_outcome_id={source_outcome.outcome_id}",
        "--parameter",
        f"revision_parent_card_id={card.parent_card_id}",
    ]
    if pending_trial.seed is not None:
        command.extend(["--seed", str(pending_trial.seed)])
    return _task(
        "record_passed_retest_trial",
        "Record passed retest trial",
        "ready",
        "experiment_trial",
        None,
        command,
        None,
        [],
        "Backtest and walk-forward evidence are ready to be linked into a PASSED retest trial.",
    )


def _leaderboard_gate_task(
    *,
    storage: Path | None,
    card: StrategyCard,
    trial: ExperimentTrial | None,
    split: SplitManifest | None,
    cost_model: CostModelSnapshot | None,
    baseline: BaselineEvaluation | None,
    backtest: BacktestResult | None,
    walk_forward: WalkForwardValidation | None,
    locked_evaluation: LockedEvaluationResult | None,
) -> RevisionRetestTask:
    if locked_evaluation is not None:
        return _task(
            "evaluate_leaderboard_gate",
            "Evaluate leaderboard gate",
            "completed",
            "locked_evaluation_result",
            locked_evaluation.evaluation_id,
            None,
            None,
            [],
            "A locked evaluation result exists for the passed retest trial.",
        )
    missing = []
    if trial is None:
        missing.append("passed_retest_trial")
    if split is None:
        missing.append("split_manifest")
    if cost_model is None:
        missing.append("cost_model_snapshot")
    if baseline is None:
        missing.append("baseline_evaluation")
    if backtest is None:
        missing.append("backtest_result")
    if walk_forward is None:
        missing.append("walk_forward_validation")
    if storage is None:
        missing.append("storage_dir")
    if missing:
        return _task(
            "evaluate_leaderboard_gate",
            "Evaluate leaderboard gate",
            "blocked",
            "locked_evaluation_result",
            None,
            None,
            "missing_locked_evaluation_inputs",
            missing,
            "The locked evaluation gate needs every evidence ID before it can be run.",
        )
    assert trial is not None
    assert split is not None
    assert cost_model is not None
    assert baseline is not None
    assert backtest is not None
    assert walk_forward is not None
    assert storage is not None
    return _task(
        "evaluate_leaderboard_gate",
        "Evaluate leaderboard gate",
        "ready",
        "locked_evaluation_result",
        None,
        _base_command(storage)
        + [
            "evaluate-leaderboard-gate",
            "--storage-dir",
            str(storage),
            "--strategy-card-id",
            card.card_id,
            "--trial-id",
            trial.trial_id,
            "--split-manifest-id",
            split.manifest_id,
            "--cost-model-id",
            cost_model.cost_model_id,
            "--baseline-id",
            baseline.baseline_id,
            "--backtest-result-id",
            backtest.result_id,
            "--walk-forward-validation-id",
            walk_forward.validation_id,
        ],
        None,
        [],
        "All locked evaluation inputs exist and can be evaluated without inventing results.",
    )


def _paper_shadow_task(
    *,
    storage: Path | None,
    leaderboard_entry: LeaderboardEntry | None,
    shadow_outcome: PaperShadowOutcome | None,
) -> RevisionRetestTask:
    if shadow_outcome is not None:
        return _task(
            "record_paper_shadow_outcome",
            "Record paper shadow outcome",
            "completed",
            "paper_shadow_outcome",
            shadow_outcome.outcome_id,
            None,
            None,
            [],
            "A paper shadow outcome already exists for the leaderboard entry.",
        )
    missing = []
    if leaderboard_entry is None:
        missing.append("leaderboard_entry")
    if storage is None:
        missing.append("storage_dir")
    if missing:
        return _task(
            "record_paper_shadow_outcome",
            "Record paper shadow outcome",
            "blocked",
            "paper_shadow_outcome",
            None,
            None,
            "leaderboard_entry_missing",
            missing,
            "Shadow outcome recording requires a concrete leaderboard entry.",
        )
    return _task(
        "record_paper_shadow_outcome",
        "Record paper shadow outcome",
        "blocked",
        "paper_shadow_outcome",
        None,
        None,
        "shadow_window_observation_required",
        [
            "window_start",
            "window_end",
            "observed_return",
            "benchmark_return",
        ],
        "The planner does not fabricate future shadow-window returns.",
    )


def _task(
    task_id: str,
    title: str,
    status: str,
    required_artifact: str,
    artifact_id: str | None,
    command_args: list[str] | None,
    blocked_reason: str | None,
    missing_inputs: list[str],
    rationale: str,
) -> RevisionRetestTask:
    return RevisionRetestTask(
        task_id=task_id,
        title=title,
        status=status,
        required_artifact=required_artifact,
        artifact_id=artifact_id,
        command_args=command_args,
        blocked_reason=blocked_reason,
        missing_inputs=missing_inputs,
        rationale=rationale,
    )


def _revision_card(
    cards: list[StrategyCard],
    *,
    symbol: str,
    revision_card_id: str | None,
) -> StrategyCard:
    if revision_card_id is not None:
        card = next((item for item in cards if item.card_id == revision_card_id), None)
        if card is None:
            raise ValueError(f"missing strategy revision card: {revision_card_id}")
        if not _is_revision_card(card, symbol):
            raise ValueError(f"not a DRAFT strategy revision card for {symbol}: {revision_card_id}")
        return card
    candidates = [card for card in cards if _is_revision_card(card, symbol)]
    card = _latest(candidates)
    if card is None:
        raise ValueError(f"no DRAFT strategy revision card found for symbol: {symbol}")
    return card


def _is_revision_card(card: StrategyCard, symbol: str) -> bool:
    return _is_revision_candidate(card, symbol) or _is_lineage_replacement_card(card, symbol)


def _is_revision_candidate(card: StrategyCard, symbol: str) -> bool:
    return (
        card.status == "DRAFT"
        and card.decision_basis == REVISION_CARD_BASIS
        and symbol in card.symbols
        and isinstance(card.parameters.get("revision_source_outcome_id"), str)
        and isinstance(card.parent_card_id, str)
        and bool(card.parent_card_id)
    )


def _is_lineage_replacement_card(card: StrategyCard, symbol: str) -> bool:
    return (
        card.status == "DRAFT"
        and card.decision_basis == REPLACEMENT_DECISION_BASIS
        and symbol in card.symbols
        and isinstance(card.parameters.get("replacement_source_outcome_id"), str)
        and isinstance(card.parameters.get("replacement_source_lineage_root_card_id"), str)
        and card.parent_card_id is None
    )


def _source_outcome(
    outcomes: list[PaperShadowOutcome],
    *,
    cards: list[StrategyCard],
    card: StrategyCard,
    symbol: str,
) -> PaperShadowOutcome:
    outcome_id = _source_outcome_id(card, symbol)
    outcome = next((item for item in outcomes if item.outcome_id == outcome_id), None)
    if outcome is None:
        raise ValueError(f"missing source paper shadow outcome: {outcome_id}")
    if outcome.symbol != symbol:
        raise ValueError(f"source paper shadow outcome symbol mismatch: {outcome_id}")
    if _is_revision_candidate(card, symbol) and outcome.strategy_card_id != card.parent_card_id:
        raise ValueError(f"source paper shadow outcome does not match revision parent: {outcome_id}")
    if _is_lineage_replacement_card(card, symbol) and not _outcome_belongs_to_replacement_lineage(
        cards,
        outcome,
        card,
    ):
        raise ValueError(f"source paper shadow outcome does not match replacement lineage: {outcome_id}")
    if _is_lineage_replacement_card(card, symbol) and outcome.recommended_strategy_action != "QUARANTINE_STRATEGY":
        raise ValueError(f"source paper shadow outcome does not require replacement: {outcome_id}")
    return outcome


def _source_outcome_id(card: StrategyCard, symbol: str) -> str:
    if _is_lineage_replacement_card(card, symbol):
        return str(card.parameters["replacement_source_outcome_id"])
    return str(card.parameters["revision_source_outcome_id"])


def _outcome_belongs_to_replacement_lineage(
    cards: list[StrategyCard],
    outcome: PaperShadowOutcome,
    replacement: StrategyCard,
) -> bool:
    root_card_id = str(replacement.parameters["replacement_source_lineage_root_card_id"])
    by_id = {card.card_id: card for card in cards}
    current_id: str | None = outcome.strategy_card_id
    while current_id:
        if current_id == root_card_id:
            return True
        current = by_id.get(current_id)
        if current is None:
            return False
        current_id = current.parent_card_id
    return False


def _latest_retest_trial(
    trials: list[ExperimentTrial],
    card: StrategyCard,
    source_outcome: PaperShadowOutcome,
    status: str,
    *,
    symbol: str,
) -> ExperimentTrial | None:
    return _latest(
        [
            trial
            for trial in trials
            if trial.strategy_card_id == card.card_id
            and trial.symbol == symbol
            and trial.status == status
            and trial.parameters.get("revision_retest_protocol") == RETEST_PROTOCOL_VERSION
            and trial.parameters.get("revision_retest_source_card_id") == card.card_id
            and trial.parameters.get("revision_source_outcome_id") == source_outcome.outcome_id
        ]
    )


def _latest_valid_passed_retest_trial(
    trials: list[ExperimentTrial],
    *,
    backtest_results: list[BacktestResult],
    walk_forward_validations: list[WalkForwardValidation],
    split_manifests: list[SplitManifest],
    card: StrategyCard,
    source_outcome: PaperShadowOutcome,
    symbol: str,
) -> ExperimentTrial | None:
    backtests_by_id = {result.result_id: result for result in backtest_results}
    walk_forwards_by_id = {validation.validation_id: validation for validation in walk_forward_validations}
    valid_trials = []
    for trial in trials:
        if trial.strategy_card_id != card.card_id:
            continue
        if trial.symbol != symbol:
            continue
        if trial.status != "PASSED":
            continue
        if trial.dataset_id is None:
            continue
        if trial.parameters.get("revision_retest_protocol") != RETEST_PROTOCOL_VERSION:
            continue
        if trial.parameters.get("revision_retest_source_card_id") != card.card_id:
            continue
        if trial.parameters.get("revision_source_outcome_id") != source_outcome.outcome_id:
            continue
        if trial.backtest_result_id is None or trial.walk_forward_validation_id is None:
            continue
        split = _latest_split_manifest(
            split_manifests,
            card=card,
            symbol=symbol,
            dataset_id=trial.dataset_id,
        )
        if split is None:
            continue
        backtest = backtests_by_id.get(trial.backtest_result_id)
        walk_forward = walk_forwards_by_id.get(trial.walk_forward_validation_id)
        if backtest is None or walk_forward is None:
            continue
        if backtest.symbol != symbol or walk_forward.symbol != symbol:
            continue
        if backtest.start != split.holdout_start or backtest.end != split.holdout_end:
            continue
        if walk_forward.start != split.train_start or walk_forward.end != split.holdout_end:
            continue
        if backtest.result_id not in walk_forward.backtest_result_ids:
            continue
        valid_trials.append(trial)
    return _latest(valid_trials)


def _latest_research_dataset(
    datasets: list[ResearchDataset],
    symbol: str,
) -> ResearchDataset | None:
    return _latest([dataset for dataset in datasets if dataset.symbol == symbol])


def _latest_split_manifest(
    manifests: list[SplitManifest],
    *,
    card: StrategyCard,
    symbol: str,
    dataset_id: str | None,
) -> SplitManifest | None:
    if dataset_id is None:
        return None
    return _latest(
        [
            manifest
            for manifest in manifests
            if manifest.strategy_card_id == card.card_id
            and manifest.dataset_id == dataset_id
            and manifest.symbol == symbol
            and manifest.status == "LOCKED"
        ]
    )


def _latest_cost_model(
    snapshots: list[CostModelSnapshot],
    symbol: str,
) -> CostModelSnapshot | None:
    return _latest(
        [
            snapshot
            for snapshot in snapshots
            if snapshot.symbol == symbol and snapshot.status == "LOCKED"
        ]
    )


def _latest_baseline(
    baselines: list[BaselineEvaluation],
    symbol: str,
) -> BaselineEvaluation | None:
    return _latest([baseline for baseline in baselines if baseline.symbol == symbol])


def _selected_backtest(
    results: list[BacktestResult],
    *,
    passed_trial: ExperimentTrial | None,
    split: SplitManifest | None,
    symbol: str,
) -> BacktestResult | None:
    if passed_trial is not None and passed_trial.backtest_result_id is not None:
        linked = next((item for item in results if item.result_id == passed_trial.backtest_result_id), None)
        if linked is not None:
            return linked
    if split is None:
        return None
    return _latest(
        [
            result
            for result in results
            if result.symbol == symbol
            and result.start == split.holdout_start
            and result.end == split.holdout_end
        ]
    )


def _selected_walk_forward(
    validations: list[WalkForwardValidation],
    *,
    passed_trial: ExperimentTrial | None,
    split: SplitManifest | None,
    symbol: str,
) -> WalkForwardValidation | None:
    if passed_trial is not None and passed_trial.walk_forward_validation_id is not None:
        linked = next(
            (
                item
                for item in validations
                if item.validation_id == passed_trial.walk_forward_validation_id
            ),
            None,
        )
        if linked is not None:
            return linked
    if split is None:
        return None
    return _latest(
        [
            validation
            for validation in validations
            if validation.symbol == symbol
            and validation.start == split.train_start
            and validation.end == split.holdout_end
        ]
    )


def _latest_locked_evaluation(
    evaluations: list[LockedEvaluationResult],
    *,
    card: StrategyCard,
    trial: ExperimentTrial | None,
    split: SplitManifest | None,
    cost_model: CostModelSnapshot | None,
    baseline: BaselineEvaluation | None,
    backtest: BacktestResult | None,
    walk_forward: WalkForwardValidation | None,
) -> LockedEvaluationResult | None:
    if (
        trial is None
        or split is None
        or cost_model is None
        or baseline is None
        or backtest is None
        or walk_forward is None
    ):
        return None
    return _latest(
        [
            evaluation
            for evaluation in evaluations
            if evaluation.strategy_card_id == card.card_id
            and evaluation.trial_id == trial.trial_id
            and evaluation.split_manifest_id == split.manifest_id
            and evaluation.cost_model_id == cost_model.cost_model_id
            and evaluation.baseline_id == baseline.baseline_id
            and evaluation.backtest_result_id == backtest.result_id
            and evaluation.walk_forward_validation_id == walk_forward.validation_id
        ]
    )


def _latest_leaderboard_entry(
    entries: list[LeaderboardEntry],
    *,
    card: StrategyCard,
    trial: ExperimentTrial | None,
    evaluation: LockedEvaluationResult | None,
    symbol: str,
) -> LeaderboardEntry | None:
    if trial is None or evaluation is None:
        return None
    return _latest(
        [
            entry
            for entry in entries
            if entry.strategy_card_id == card.card_id
            and entry.trial_id == trial.trial_id
            and entry.evaluation_id == evaluation.evaluation_id
            and entry.symbol == symbol
        ]
    )


def _latest_shadow_outcome(
    outcomes: list[PaperShadowOutcome],
    *,
    leaderboard_entry: LeaderboardEntry | None,
    symbol: str,
) -> PaperShadowOutcome | None:
    if leaderboard_entry is None:
        return None
    return _latest(
        [
            outcome
            for outcome in outcomes
            if outcome.leaderboard_entry_id == leaderboard_entry.entry_id
            and outcome.symbol == symbol
        ]
    )


def _lock_protocol_command(
    *,
    storage: Path,
    symbol: str,
    card: StrategyCard,
    dataset_id: str,
    split: SplitManifest,
) -> list[str]:
    return _base_command(storage) + [
        "lock-evaluation-protocol",
        "--storage-dir",
        str(storage),
        "--strategy-card-id",
        card.card_id,
        "--dataset-id",
        dataset_id,
        "--symbol",
        symbol,
        "--train-start",
        split.train_start.isoformat(),
        "--train-end",
        split.train_end.isoformat(),
        "--validation-start",
        split.validation_start.isoformat(),
        "--validation-end",
        split.validation_end.isoformat(),
        "--holdout-start",
        split.holdout_start.isoformat(),
        "--holdout-end",
        split.holdout_end.isoformat(),
        "--embargo-hours",
        str(split.embargo_hours),
    ]


def _base_command(storage: Path) -> list[str]:
    script = Path("run_forecast_loop.py")
    script_arg = str(script)
    if "\\" not in script_arg and "/" not in script_arg:
        script_arg = f".\\{script_arg}"
    return ["python", script_arg]


def _first_present(*values: str | None) -> str | None:
    for value in values:
        if value:
            return value
    return None


def _latest(items):
    return max(items, key=lambda item: item.created_at) if items else None
