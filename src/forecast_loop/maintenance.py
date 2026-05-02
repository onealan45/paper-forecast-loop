from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import json
import re

from forecast_loop.models import (
    BacktestResult,
    BacktestRun,
    ExperimentTrial,
    Forecast,
    LeaderboardEntry,
    LockedEvaluationResult,
    PaperShadowOutcome,
    ResearchAutopilotRun,
    WalkForwardValidation,
)
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
    quarantined_retest_dependent_artifact_count: int
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
    quarantine_dir = storage_dir / "quarantine"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    quarantine_path = quarantine_dir / "legacy_forecasts.jsonl"
    retest_trial_quarantine_path = quarantine_dir / "retest_context_experiment_trials.jsonl"
    locked_evaluation_quarantine_path = quarantine_dir / "retest_context_locked_evaluation_results.jsonl"
    leaderboard_quarantine_path = quarantine_dir / "retest_context_leaderboard_entries.jsonl"
    paper_shadow_quarantine_path = quarantine_dir / "retest_context_paper_shadow_outcomes.jsonl"
    autopilot_quarantine_path = quarantine_dir / "retest_context_research_autopilot_runs.jsonl"
    report_path = storage_dir / "storage_repair_report.json"

    experiment_trials = repository.load_experiment_trials()
    backtest_runs = repository.load_backtest_runs()
    backtest_results = repository.load_backtest_results()
    walk_forward_validations = repository.load_walk_forward_validations()
    locked_evaluation_results = repository.load_locked_evaluation_results()
    leaderboard_entries = repository.load_leaderboard_entries()
    paper_shadow_outcomes = repository.load_paper_shadow_outcomes()
    research_autopilot_runs = repository.load_research_autopilot_runs()
    bad_retest_trials = _bad_retest_context_trials(
        experiment_trials=experiment_trials,
        backtest_runs=backtest_runs,
        backtest_results=backtest_results,
        walk_forward_validations=walk_forward_validations,
    )
    bad_retest_trial_ids = {
        *{trial.trial_id for trial in bad_retest_trials},
        *_existing_jsonl_ids(retest_trial_quarantine_path, identity_key="trial_id"),
    }
    active_experiment_trials = [
        trial for trial in experiment_trials if trial.trial_id not in bad_retest_trial_ids
    ]
    latest_experiment_trial_id = active_experiment_trials[-1].trial_id if active_experiment_trials else None
    bad_locked_evaluations, active_locked_evaluations = _split_locked_evaluations(
        locked_evaluation_results,
        bad_retest_trial_ids=bad_retest_trial_ids,
    )
    bad_locked_evaluation_ids = {
        *{result.evaluation_id for result in bad_locked_evaluations},
        *_existing_jsonl_ids(locked_evaluation_quarantine_path, identity_key="evaluation_id"),
    }
    bad_leaderboard_entries, active_leaderboard_entries = _split_leaderboard_entries(
        leaderboard_entries,
        bad_retest_trial_ids=bad_retest_trial_ids,
        bad_locked_evaluation_ids=bad_locked_evaluation_ids,
    )
    bad_leaderboard_entry_ids = {
        *{entry.entry_id for entry in bad_leaderboard_entries},
        *_existing_jsonl_ids(leaderboard_quarantine_path, identity_key="entry_id"),
    }
    bad_paper_shadow_outcomes, active_paper_shadow_outcomes = _split_paper_shadow_outcomes(
        paper_shadow_outcomes,
        bad_retest_trial_ids=bad_retest_trial_ids,
        bad_locked_evaluation_ids=bad_locked_evaluation_ids,
        bad_leaderboard_entry_ids=bad_leaderboard_entry_ids,
    )
    bad_paper_shadow_outcome_ids = {
        *{outcome.outcome_id for outcome in bad_paper_shadow_outcomes},
        *_existing_jsonl_ids(paper_shadow_quarantine_path, identity_key="outcome_id"),
    }
    bad_autopilot_runs, active_autopilot_runs = _split_research_autopilot_runs(
        research_autopilot_runs,
        bad_retest_trial_ids=bad_retest_trial_ids,
        bad_locked_evaluation_ids=bad_locked_evaluation_ids,
        bad_leaderboard_entry_ids=bad_leaderboard_entry_ids,
        bad_paper_shadow_outcome_ids=bad_paper_shadow_outcome_ids,
    )
    quarantined_dependent_count = (
        len(bad_locked_evaluations)
        + len(bad_leaderboard_entries)
        + len(bad_paper_shadow_outcomes)
        + len(bad_autopilot_runs)
    )

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
    if bad_locked_evaluations:
        _append_unique_jsonl(
            locked_evaluation_quarantine_path,
            bad_locked_evaluations,
            identity_key="evaluation_id",
        )
        repository.replace_locked_evaluation_results(active_locked_evaluations)
    if bad_leaderboard_entries:
        _append_unique_jsonl(
            leaderboard_quarantine_path,
            bad_leaderboard_entries,
            identity_key="entry_id",
        )
        repository.replace_leaderboard_entries(active_leaderboard_entries)
    if bad_paper_shadow_outcomes:
        _append_unique_jsonl(
            paper_shadow_quarantine_path,
            bad_paper_shadow_outcomes,
            identity_key="outcome_id",
        )
        repository.replace_paper_shadow_outcomes(active_paper_shadow_outcomes)
    if bad_autopilot_runs:
        _append_unique_jsonl(
            autopilot_quarantine_path,
            bad_autopilot_runs,
            identity_key="run_id",
        )
        repository.replace_research_autopilot_runs(active_autopilot_runs)

    status = _repair_status(
        quarantined_forecast_count=len(legacy_forecasts),
        quarantined_retest_trial_count=len(bad_retest_trials),
        quarantined_retest_dependent_artifact_count=quarantined_dependent_count,
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
        quarantined_retest_dependent_artifact_count=quarantined_dependent_count,
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
                "quarantined_retest_dependent_artifact_count": (
                    result.quarantined_retest_dependent_artifact_count
                ),
                "active_experiment_trial_count": result.active_experiment_trial_count,
                "latest_experiment_trial_id": result.latest_experiment_trial_id,
                "quarantine_path": str(quarantine_path.resolve()),
                "retest_trial_quarantine_path": str(retest_trial_quarantine_path.resolve()),
                "retest_dependent_quarantine_paths": {
                    "locked_evaluation_results": str(locked_evaluation_quarantine_path.resolve()),
                    "leaderboard_entries": str(leaderboard_quarantine_path.resolve()),
                    "paper_shadow_outcomes": str(paper_shadow_quarantine_path.resolve()),
                    "research_autopilot_runs": str(autopilot_quarantine_path.resolve()),
                },
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


def _split_locked_evaluations(
    results: list[LockedEvaluationResult],
    *,
    bad_retest_trial_ids: set[str],
) -> tuple[list[LockedEvaluationResult], list[LockedEvaluationResult]]:
    bad = [result for result in results if result.trial_id in bad_retest_trial_ids]
    bad_ids = {result.evaluation_id for result in bad}
    active = [result for result in results if result.evaluation_id not in bad_ids]
    return bad, active


def _split_leaderboard_entries(
    entries: list[LeaderboardEntry],
    *,
    bad_retest_trial_ids: set[str],
    bad_locked_evaluation_ids: set[str],
) -> tuple[list[LeaderboardEntry], list[LeaderboardEntry]]:
    bad = [
        entry
        for entry in entries
        if entry.trial_id in bad_retest_trial_ids or entry.evaluation_id in bad_locked_evaluation_ids
    ]
    bad_ids = {entry.entry_id for entry in bad}
    active = [entry for entry in entries if entry.entry_id not in bad_ids]
    return bad, active


def _split_paper_shadow_outcomes(
    outcomes: list[PaperShadowOutcome],
    *,
    bad_retest_trial_ids: set[str],
    bad_locked_evaluation_ids: set[str],
    bad_leaderboard_entry_ids: set[str],
) -> tuple[list[PaperShadowOutcome], list[PaperShadowOutcome]]:
    bad = [
        outcome
        for outcome in outcomes
        if outcome.trial_id in bad_retest_trial_ids
        or outcome.evaluation_id in bad_locked_evaluation_ids
        or outcome.leaderboard_entry_id in bad_leaderboard_entry_ids
    ]
    bad_ids = {outcome.outcome_id for outcome in bad}
    active = [outcome for outcome in outcomes if outcome.outcome_id not in bad_ids]
    return bad, active


def _split_research_autopilot_runs(
    runs: list[ResearchAutopilotRun],
    *,
    bad_retest_trial_ids: set[str],
    bad_locked_evaluation_ids: set[str],
    bad_leaderboard_entry_ids: set[str],
    bad_paper_shadow_outcome_ids: set[str],
) -> tuple[list[ResearchAutopilotRun], list[ResearchAutopilotRun]]:
    bad = [
        run
        for run in runs
        if run.experiment_trial_id in bad_retest_trial_ids
        or run.locked_evaluation_id in bad_locked_evaluation_ids
        or run.leaderboard_entry_id in bad_leaderboard_entry_ids
        or run.paper_shadow_outcome_id in bad_paper_shadow_outcome_ids
    ]
    bad_ids = {run.run_id for run in bad}
    active = [run for run in runs if run.run_id not in bad_ids]
    return bad, active


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


def _existing_jsonl_ids(path: Path, *, identity_key: str) -> set[str]:
    if not path.exists():
        return set()
    ids = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        identity = payload.get(identity_key)
        if isinstance(identity, str):
            ids.add(identity)
    return ids


def _repair_status(
    *,
    quarantined_forecast_count: int,
    quarantined_retest_trial_count: int,
    quarantined_retest_dependent_artifact_count: int,
) -> str:
    if (
        quarantined_forecast_count
        and (quarantined_retest_trial_count or quarantined_retest_dependent_artifact_count)
    ):
        return "storage_artifacts_quarantined"
    if quarantined_forecast_count:
        return "legacy_forecasts_quarantined"
    if quarantined_retest_trial_count:
        return "retest_context_trials_quarantined"
    if quarantined_retest_dependent_artifact_count:
        return "retest_context_dependent_artifacts_quarantined"
    return "no_legacy_forecasts_found"
