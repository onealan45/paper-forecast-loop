from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from forecast_loop.locked_evaluation import lock_evaluation_protocol
from forecast_loop.models import CostModelSnapshot, ExperimentTrial, PaperShadowOutcome, SplitManifest, StrategyCard
from forecast_loop.storage import ArtifactRepository
from forecast_loop.strategy_evolution import REPLACEMENT_DECISION_BASIS, REVISION_DECISION_BASIS
from forecast_loop.strategy_research import REVISION_REQUIRED_ACTIONS


RETEST_PROTOCOL_VERSION = "pr14-v1"
REPLACEMENT_REQUIRED_ACTIONS = {"QUARANTINE", "QUARANTINE_STRATEGY"}


@dataclass(frozen=True, slots=True)
class RevisionRetestScaffold:
    strategy_card: StrategyCard
    source_outcome: PaperShadowOutcome
    experiment_trial: ExperimentTrial
    split_manifest: SplitManifest | None
    cost_model_snapshot: CostModelSnapshot | None
    next_required_artifacts: list[str]

    def to_dict(self) -> dict:
        return {
            "strategy_card_id": self.strategy_card.card_id,
            "source_outcome_id": self.source_outcome.outcome_id,
            "experiment_trial": self.experiment_trial.to_dict(),
            "split_manifest": self.split_manifest.to_dict() if self.split_manifest else None,
            "cost_model_snapshot": self.cost_model_snapshot.to_dict() if self.cost_model_snapshot else None,
            "next_required_artifacts": list(self.next_required_artifacts),
        }


def create_revision_retest_scaffold(
    *,
    repository: ArtifactRepository,
    created_at: datetime,
    symbol: str,
    dataset_id: str,
    max_trials: int,
    revision_card_id: str | None = None,
    seed: int | None = None,
    train_start: datetime | None = None,
    train_end: datetime | None = None,
    validation_start: datetime | None = None,
    validation_end: datetime | None = None,
    holdout_start: datetime | None = None,
    holdout_end: datetime | None = None,
    embargo_hours: int = 24,
    fee_bps: float = 5.0,
    slippage_bps: float = 10.0,
    max_turnover: float = 5.0,
    max_drawdown: float = 0.10,
    baseline_suite_version: str = "m4b-v1",
    locked_by: str = "codex",
) -> RevisionRetestScaffold:
    symbol = symbol.upper()
    card = _revision_card(repository, revision_card_id=revision_card_id, symbol=symbol)
    outcome = _source_outcome(repository, card=card, symbol=symbol)
    existing_trial = _existing_pending_retest(repository.load_experiment_trials(), card.card_id, outcome.outcome_id)
    if existing_trial is None:
        trial = _save_pending_retest_trial(
            repository=repository,
            created_at=created_at,
            card=card,
            outcome=outcome,
            symbol=symbol,
            dataset_id=dataset_id,
            max_trials=max_trials,
            seed=seed,
        )
    else:
        trial = existing_trial

    split_manifest: SplitManifest | None = None
    cost_model_snapshot: CostModelSnapshot | None = None
    if _has_any_protocol_window(
        train_start,
        train_end,
        validation_start,
        validation_end,
        holdout_start,
        holdout_end,
    ):
        _require_complete_protocol_window(
            train_start=train_start,
            train_end=train_end,
            validation_start=validation_start,
            validation_end=validation_end,
            holdout_start=holdout_start,
            holdout_end=holdout_end,
        )
        assert train_start is not None
        assert train_end is not None
        assert validation_start is not None
        assert validation_end is not None
        assert holdout_start is not None
        assert holdout_end is not None
        created_split, created_cost = lock_evaluation_protocol(
            repository=repository,
            created_at=created_at,
            strategy_card_id=card.card_id,
            dataset_id=dataset_id,
            symbol=symbol,
            train_start=train_start,
            train_end=train_end,
            validation_start=validation_start,
            validation_end=validation_end,
            holdout_start=holdout_start,
            holdout_end=holdout_end,
            embargo_hours=embargo_hours,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            max_turnover=max_turnover,
            max_drawdown=max_drawdown,
            baseline_suite_version=baseline_suite_version,
            locked_by=locked_by,
        )
        split_manifest = _persisted_split_manifest(repository, created_split)
        cost_model_snapshot = _persisted_cost_model_snapshot(repository, created_cost)

    return RevisionRetestScaffold(
        strategy_card=card,
        source_outcome=outcome,
        experiment_trial=trial,
        split_manifest=split_manifest,
        cost_model_snapshot=cost_model_snapshot,
        next_required_artifacts=_next_required_artifacts(split_manifest, cost_model_snapshot),
    )


def _revision_card(
    repository: ArtifactRepository,
    *,
    revision_card_id: str | None,
    symbol: str,
) -> StrategyCard:
    cards = repository.load_strategy_cards()
    if revision_card_id is None:
        candidates = [
            card
            for card in cards
            if _is_revision_card(card) and symbol in card.symbols
        ]
        if not candidates:
            raise ValueError(f"no DRAFT strategy revision card found for symbol: {symbol}")
        return max(candidates, key=lambda item: item.created_at)
    card = next((item for item in cards if item.card_id == revision_card_id), None)
    if card is None:
        raise ValueError(f"missing strategy card: {revision_card_id}")
    if not _is_revision_card(card):
        raise ValueError(f"not a DRAFT strategy revision card: {revision_card_id}")
    if symbol not in card.symbols:
        raise ValueError(f"strategy revision card does not cover symbol {symbol}: {revision_card_id}")
    return card


def _is_revision_card(card: StrategyCard) -> bool:
    return _is_revision_candidate(card) or _is_lineage_replacement_card(card)


def _is_revision_candidate(card: StrategyCard) -> bool:
    return (
        card.status == "DRAFT"
        and card.decision_basis == REVISION_DECISION_BASIS
        and isinstance(card.parameters.get("revision_source_outcome_id"), str)
        and isinstance(card.parent_card_id, str)
        and bool(card.parent_card_id)
    )


def _is_lineage_replacement_card(card: StrategyCard) -> bool:
    return (
        card.status == "DRAFT"
        and card.decision_basis == REPLACEMENT_DECISION_BASIS
        and isinstance(card.parameters.get("replacement_source_outcome_id"), str)
        and isinstance(card.parameters.get("replacement_source_lineage_root_card_id"), str)
        and card.parent_card_id is None
    )


def _source_outcome(
    repository: ArtifactRepository,
    *,
    card: StrategyCard,
    symbol: str,
) -> PaperShadowOutcome:
    outcome_id = _source_outcome_id(card)
    outcome = next((item for item in repository.load_paper_shadow_outcomes() if item.outcome_id == outcome_id), None)
    if outcome is None:
        raise ValueError(f"missing source paper shadow outcome: {outcome_id}")
    if outcome.symbol != symbol:
        raise ValueError(f"source paper shadow outcome symbol mismatch: {outcome_id}")
    if _is_revision_candidate(card) and outcome.strategy_card_id != card.parent_card_id:
        raise ValueError(f"source paper shadow outcome does not match revision parent: {outcome_id}")
    if _is_lineage_replacement_card(card) and not _outcome_belongs_to_replacement_lineage(
        repository.load_strategy_cards(),
        outcome,
        card,
    ):
        raise ValueError(f"source paper shadow outcome does not match replacement lineage: {outcome_id}")
    if _is_revision_candidate(card) and outcome.recommended_strategy_action not in REVISION_REQUIRED_ACTIONS:
        raise ValueError(f"source paper shadow outcome does not require revision: {outcome_id}")
    if _is_lineage_replacement_card(card) and outcome.recommended_strategy_action not in REPLACEMENT_REQUIRED_ACTIONS:
        raise ValueError(f"source paper shadow outcome does not require replacement: {outcome_id}")
    return outcome


def _source_outcome_id(card: StrategyCard) -> str:
    if _is_lineage_replacement_card(card):
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


def _existing_pending_retest(
    trials: list[ExperimentTrial],
    strategy_card_id: str,
    outcome_id: str,
) -> ExperimentTrial | None:
    candidates = [
        trial
        for trial in trials
        if trial.strategy_card_id == strategy_card_id
        and trial.status == "PENDING"
        and trial.parameters.get("revision_retest_protocol") == RETEST_PROTOCOL_VERSION
        and trial.parameters.get("revision_source_outcome_id") == outcome_id
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.created_at)


def _save_pending_retest_trial(
    *,
    repository: ArtifactRepository,
    created_at: datetime,
    card: StrategyCard,
    outcome: PaperShadowOutcome,
    symbol: str,
    dataset_id: str,
    max_trials: int,
    seed: int | None,
) -> ExperimentTrial:
    parameters = {
        "revision_retest_protocol": RETEST_PROTOCOL_VERSION,
        "revision_retest_source_card_id": card.card_id,
        "revision_source_outcome_id": outcome.outcome_id,
        "revision_parent_card_id": card.parent_card_id,
        "max_trials": max_trials,
    }
    if _is_lineage_replacement_card(card):
        parameters.update(
            {
                "revision_retest_kind": "lineage_replacement",
                "replacement_source_lineage_root_card_id": card.parameters["replacement_source_lineage_root_card_id"],
            }
        )
    else:
        parameters["revision_retest_kind"] = "revision"
    trial = ExperimentTrial(
        trial_id=ExperimentTrial.build_id(
            strategy_card_id=card.card_id,
            trial_index=_next_trial_index(repository.load_experiment_trials(), card.card_id),
            status="PENDING",
            seed=seed,
            prompt_hash=None,
            code_hash=None,
            parameters=parameters,
        ),
        created_at=created_at,
        strategy_card_id=card.card_id,
        trial_index=_next_trial_index(repository.load_experiment_trials(), card.card_id),
        status="PENDING",
        symbol=symbol,
        seed=seed,
        dataset_id=dataset_id,
        backtest_result_id=None,
        walk_forward_validation_id=None,
        event_edge_evaluation_id=None,
        prompt_hash=None,
        code_hash=None,
        parameters=parameters,
        metric_summary={},
        failure_reason=None,
        started_at=created_at,
        completed_at=None,
        decision_basis="revision_retest_scaffold",
    )
    repository.save_experiment_trial(trial)
    return next(
        (
            item
            for item in repository.load_experiment_trials()
            if item.trial_id == trial.trial_id
        ),
        trial,
    )


def _persisted_split_manifest(
    repository: ArtifactRepository,
    candidate: SplitManifest,
) -> SplitManifest:
    return next(
        (
            item
            for item in repository.load_split_manifests()
            if item.manifest_id == candidate.manifest_id
        ),
        candidate,
    )


def _persisted_cost_model_snapshot(
    repository: ArtifactRepository,
    candidate: CostModelSnapshot,
) -> CostModelSnapshot:
    return next(
        (
            item
            for item in repository.load_cost_model_snapshots()
            if item.cost_model_id == candidate.cost_model_id
        ),
        candidate,
    )


def _next_trial_index(trials: list[ExperimentTrial], strategy_card_id: str) -> int:
    indexes = [trial.trial_index for trial in trials if trial.strategy_card_id == strategy_card_id]
    return max(indexes, default=0) + 1


def _has_any_protocol_window(*values: datetime | None) -> bool:
    return any(value is not None for value in values)


def _require_complete_protocol_window(
    *,
    train_start: datetime | None,
    train_end: datetime | None,
    validation_start: datetime | None,
    validation_end: datetime | None,
    holdout_start: datetime | None,
    holdout_end: datetime | None,
) -> None:
    fields = {
        "train_start": train_start,
        "train_end": train_end,
        "validation_start": validation_start,
        "validation_end": validation_end,
        "holdout_start": holdout_start,
        "holdout_end": holdout_end,
    }
    missing = [name for name, value in fields.items() if value is None]
    if missing:
        raise ValueError(f"split protocol window is incomplete; missing: {', '.join(missing)}")


def _next_required_artifacts(
    split_manifest: SplitManifest | None,
    cost_model_snapshot: CostModelSnapshot | None,
) -> list[str]:
    artifacts: list[str] = []
    if split_manifest is None:
        artifacts.append("split_manifest")
    if cost_model_snapshot is None:
        artifacts.append("cost_model_snapshot")
    artifacts.extend(
        [
            "baseline_evaluation",
            "backtest_result",
            "walk_forward_validation",
            "locked_evaluation_result",
            "leaderboard_entry",
            "paper_shadow_outcome",
        ]
    )
    return artifacts
