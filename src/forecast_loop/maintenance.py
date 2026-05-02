from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import json
import re

from forecast_loop.models import BacktestResult, BacktestRun, ExperimentTrial, Forecast, WalkForwardValidation
from forecast_loop.revision_retest import RETEST_PROTOCOL_VERSION
from forecast_loop.storage import JsonFileRepository


@dataclass(slots=True)
class StorageRepairResult:
    storage_dir: Path
    generated_at_utc: datetime
    total_forecast_count: int
    quarantined_forecast_count: int
    kept_forecast_count: int
    active_forecast_count: int
    latest_forecast_id: str | None
    quarantined_retest_trial_count: int
    active_experiment_trial_count: int
    latest_experiment_trial_id: str | None
    quarantine_path: Path
    retest_trial_quarantine_path: Path
    report_path: Path
    status: str


def repair_storage(storage_dir: Path | str) -> StorageRepairResult:
    storage_dir = Path(storage_dir)
    generated_at_utc = datetime.now(tz=UTC)
    repository = JsonFileRepository(storage_dir)
    forecasts = repository.load_forecasts()
    legacy_forecasts = [forecast for forecast in forecasts if _is_legacy_forecast(forecast)]
    current_forecasts = [forecast for forecast in forecasts if not _is_legacy_forecast(forecast)]
    latest_forecast_id = current_forecasts[-1].forecast_id if current_forecasts else None
    experiment_trials = repository.load_experiment_trials()
    backtest_runs = repository.load_backtest_runs()
    backtest_results = repository.load_backtest_results()
    walk_forward_validations = repository.load_walk_forward_validations()
    bad_retest_trials = _bad_retest_context_trials(
        experiment_trials=experiment_trials,
        backtest_runs=backtest_runs,
        backtest_results=backtest_results,
        walk_forward_validations=walk_forward_validations,
    )
    bad_retest_trial_ids = {trial.trial_id for trial in bad_retest_trials}
    active_experiment_trials = [
        trial for trial in experiment_trials if trial.trial_id not in bad_retest_trial_ids
    ]
    latest_experiment_trial_id = active_experiment_trials[-1].trial_id if active_experiment_trials else None

    quarantine_dir = storage_dir / "quarantine"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    quarantine_path = quarantine_dir / "legacy_forecasts.jsonl"
    retest_trial_quarantine_path = quarantine_dir / "retest_context_experiment_trials.jsonl"
    report_path = storage_dir / "storage_repair_report.json"

    if legacy_forecasts:
        _append_unique_jsonl(quarantine_path, legacy_forecasts, identity_key="forecast_id")

        repository.replace_forecasts(current_forecasts)
    if bad_retest_trials:
        _append_unique_jsonl(
            retest_trial_quarantine_path,
            bad_retest_trials,
            identity_key="trial_id",
        )
        repository.replace_experiment_trials(active_experiment_trials)

    status = _repair_status(
        quarantined_forecast_count=len(legacy_forecasts),
        quarantined_retest_trial_count=len(bad_retest_trials),
    )

    result = StorageRepairResult(
        storage_dir=storage_dir,
        generated_at_utc=generated_at_utc,
        total_forecast_count=len(forecasts),
        quarantined_forecast_count=len(legacy_forecasts),
        kept_forecast_count=len(current_forecasts),
        active_forecast_count=len(current_forecasts),
        latest_forecast_id=latest_forecast_id,
        quarantined_retest_trial_count=len(bad_retest_trials),
        active_experiment_trial_count=len(active_experiment_trials),
        latest_experiment_trial_id=latest_experiment_trial_id,
        quarantine_path=quarantine_path,
        retest_trial_quarantine_path=retest_trial_quarantine_path,
        report_path=report_path,
        status=status,
    )
    report_path.write_text(
        json.dumps(
            {
                "storage_dir": str(storage_dir.resolve()),
                "generated_at_utc": result.generated_at_utc.isoformat(),
                "total_forecast_count": result.total_forecast_count,
                "quarantined_forecast_count": result.quarantined_forecast_count,
                "kept_forecast_count": result.kept_forecast_count,
                "active_forecast_count": result.active_forecast_count,
                "latest_forecast_id": result.latest_forecast_id,
                "quarantined_retest_trial_count": result.quarantined_retest_trial_count,
                "active_experiment_trial_count": result.active_experiment_trial_count,
                "latest_experiment_trial_id": result.latest_experiment_trial_id,
                "quarantine_path": str(quarantine_path.resolve()),
                "retest_trial_quarantine_path": str(retest_trial_quarantine_path.resolve()),
                "status": result.status,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return result


def _is_legacy_forecast(forecast: Forecast) -> bool:
    if not _is_hour_aligned(forecast.anchor_time):
        return True
    if forecast.target_window_start != forecast.anchor_time:
        return True
    if not _is_hour_aligned(forecast.target_window_end):
        return True
    return False


def _is_hour_aligned(value) -> bool:
    return value.minute == 0 and value.second == 0 and value.microsecond == 0


def _bad_retest_context_trials(
    *,
    experiment_trials: list[ExperimentTrial],
    backtest_runs: list[BacktestRun],
    backtest_results: list[BacktestResult],
    walk_forward_validations: list[WalkForwardValidation],
) -> list[ExperimentTrial]:
    backtest_results_by_id = {result.result_id: result for result in backtest_results}
    backtest_runs_by_id = {run.backtest_id: run for run in backtest_runs}
    walk_forwards_by_id = {validation.validation_id: validation for validation in walk_forward_validations}
    bad_trials = []
    for trial in experiment_trials:
        if not _is_revision_retest_passed_trial(trial):
            continue
        valid_contexts = _valid_revision_retest_contexts(trial, experiment_trials)
        if not valid_contexts:
            bad_trials.append(trial)
            continue
        if _trial_has_bad_backtest_context(
            trial=trial,
            valid_contexts=valid_contexts,
            backtest_results_by_id=backtest_results_by_id,
            backtest_runs_by_id=backtest_runs_by_id,
        ):
            bad_trials.append(trial)
            continue
        if _trial_has_bad_walk_forward_context(
            trial=trial,
            valid_contexts=valid_contexts,
            walk_forwards_by_id=walk_forwards_by_id,
        ):
            bad_trials.append(trial)
    return bad_trials


def _trial_has_bad_backtest_context(
    *,
    trial: ExperimentTrial,
    valid_contexts: list[str],
    backtest_results_by_id: dict[str, BacktestResult],
    backtest_runs_by_id: dict[str, BacktestRun],
) -> bool:
    if not trial.backtest_result_id:
        return False
    backtest_result = backtest_results_by_id.get(trial.backtest_result_id)
    backtest_run = backtest_runs_by_id.get(backtest_result.backtest_id) if backtest_result is not None else None
    return backtest_run is not None and not _decision_basis_has_any_id_context(
        backtest_run.decision_basis,
        valid_contexts,
    )


def _trial_has_bad_walk_forward_context(
    *,
    trial: ExperimentTrial,
    valid_contexts: list[str],
    walk_forwards_by_id: dict[str, WalkForwardValidation],
) -> bool:
    if not trial.walk_forward_validation_id:
        return False
    walk_forward = walk_forwards_by_id.get(trial.walk_forward_validation_id)
    return walk_forward is not None and not _decision_basis_has_any_id_context(
        walk_forward.decision_basis,
        valid_contexts,
    )


def _is_revision_retest_passed_trial(trial: ExperimentTrial) -> bool:
    return (
        trial.status == "PASSED"
        and trial.parameters.get("revision_retest_protocol") == RETEST_PROTOCOL_VERSION
        and (trial.backtest_result_id is not None or trial.walk_forward_validation_id is not None)
    )


def _valid_revision_retest_contexts(
    trial: ExperimentTrial,
    experiment_trials: list[ExperimentTrial],
) -> list[str]:
    source_outcome_id = trial.parameters.get("revision_source_outcome_id")
    if not isinstance(source_outcome_id, str) or not source_outcome_id:
        return []
    contexts = [f"revision_retest:{trial.strategy_card_id}:{trial.trial_id}:{source_outcome_id}"]
    for candidate in experiment_trials:
        if candidate.trial_id == trial.trial_id:
            continue
        if candidate.status != "PENDING":
            continue
        if not _same_revision_retest_chain(candidate, trial, source_outcome_id=source_outcome_id):
            continue
        contexts.append(f"revision_retest:{candidate.strategy_card_id}:{candidate.trial_id}:{source_outcome_id}")
    return list(dict.fromkeys(contexts))


def _same_revision_retest_chain(
    candidate: ExperimentTrial,
    trial: ExperimentTrial,
    *,
    source_outcome_id: str,
) -> bool:
    return (
        candidate.strategy_card_id == trial.strategy_card_id
        and candidate.symbol == trial.symbol
        and candidate.dataset_id == trial.dataset_id
        and candidate.trial_index == trial.trial_index
        and candidate.parameters.get("revision_retest_protocol") == RETEST_PROTOCOL_VERSION
        and candidate.parameters.get("revision_retest_source_card_id") == trial.strategy_card_id
        and candidate.parameters.get("revision_source_outcome_id") == source_outcome_id
    )


def _decision_basis_has_any_id_context(decision_basis: str, contexts: list[str]) -> bool:
    return bool(set(contexts) & set(_id_context_tokens(decision_basis)))


def _id_context_tokens(decision_basis: str) -> list[str]:
    return re.findall(r"(?:^|[;,\s])id_context=([^;,\s]+)", decision_basis)


def _append_unique_jsonl(path: Path, items: list, *, identity_key: str) -> None:
    existing_ids = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            existing_ids.add(json.loads(line)[identity_key])

    with path.open("a", encoding="utf-8") as handle:
        for item in items:
            payload = item.to_dict()
            if payload[identity_key] in existing_ids:
                continue
            handle.write(json.dumps(payload) + "\n")


def _repair_status(*, quarantined_forecast_count: int, quarantined_retest_trial_count: int) -> str:
    if quarantined_forecast_count and quarantined_retest_trial_count:
        return "storage_artifacts_quarantined"
    if quarantined_forecast_count:
        return "legacy_forecasts_quarantined"
    if quarantined_retest_trial_count:
        return "retest_context_trials_quarantined"
    return "no_legacy_forecasts_found"
