from __future__ import annotations

from datetime import datetime

from forecast_loop.models import LeaderboardEntry, LockedEvaluationResult, PaperShadowOutcome
from forecast_loop.storage import ArtifactRepository


PASS_EXCESS_RETURN = 0.0
QUARANTINE_EXCESS_RETURN = -0.05
QUARANTINE_ADVERSE_EXCURSION = 0.10
HIGH_TURNOVER = 5.0


def record_paper_shadow_outcome(
    *,
    repository: ArtifactRepository,
    created_at: datetime,
    leaderboard_entry_id: str,
    window_start: datetime,
    window_end: datetime,
    observed_return: float,
    benchmark_return: float,
    max_adverse_excursion: float | None = None,
    turnover: float | None = None,
    note: str | None = None,
) -> PaperShadowOutcome:
    entry = _require_leaderboard_entry(repository, leaderboard_entry_id)
    if window_start < entry.created_at:
        raise ValueError("paper_shadow_window_starts_before_leaderboard_entry")
    evaluation = _require_locked_evaluation(repository, entry.evaluation_id)
    blocked = _link_blockers(repository, entry=entry, evaluation=evaluation)
    blocked = _unique([*_leaderboard_blockers(entry), *_evaluation_blockers(evaluation), *blocked])

    excess_return = round(observed_return - benchmark_return, 8)
    grade, promotion_stage, strategy_action, attributions = _classify_outcome(
        excess_return=excess_return,
        max_adverse_excursion=max_adverse_excursion,
        turnover=turnover,
        blocked_reasons=blocked,
    )
    outcome = PaperShadowOutcome(
        outcome_id=PaperShadowOutcome.build_id(
            leaderboard_entry_id=leaderboard_entry_id,
            window_start=window_start,
            window_end=window_end,
            observed_return=observed_return,
            benchmark_return=benchmark_return,
        ),
        created_at=created_at,
        leaderboard_entry_id=entry.entry_id,
        evaluation_id=entry.evaluation_id,
        strategy_card_id=entry.strategy_card_id,
        trial_id=entry.trial_id,
        symbol=entry.symbol,
        window_start=window_start,
        window_end=window_end,
        observed_return=observed_return,
        benchmark_return=benchmark_return,
        excess_return_after_costs=excess_return,
        max_adverse_excursion=max_adverse_excursion,
        turnover=turnover,
        outcome_grade=grade,
        failure_attributions=attributions,
        recommended_promotion_stage=promotion_stage,
        recommended_strategy_action=strategy_action,
        blocked_reasons=blocked,
        notes=[note] if note else [],
        decision_basis="paper_shadow_outcome_learning",
    )
    repository.save_paper_shadow_outcome(outcome)
    return outcome


def _require_leaderboard_entry(repository: ArtifactRepository, entry_id: str) -> LeaderboardEntry:
    for entry in repository.load_leaderboard_entries():
        if entry.entry_id == entry_id:
            return entry
    raise ValueError(f"leaderboard entry not found: {entry_id}")


def _require_locked_evaluation(repository: ArtifactRepository, evaluation_id: str) -> LockedEvaluationResult:
    for evaluation in repository.load_locked_evaluation_results():
        if evaluation.evaluation_id == evaluation_id:
            return evaluation
    raise ValueError(f"locked evaluation not found: {evaluation_id}")


def _link_blockers(
    repository: ArtifactRepository,
    *,
    entry: LeaderboardEntry,
    evaluation: LockedEvaluationResult,
) -> list[str]:
    blockers: list[str] = []
    strategy_card_ids = {card.card_id for card in repository.load_strategy_cards()}
    trial_ids = {trial.trial_id for trial in repository.load_experiment_trials()}
    if entry.strategy_card_id != evaluation.strategy_card_id:
        blockers.append("leaderboard_evaluation_strategy_card_mismatch")
    if entry.trial_id != evaluation.trial_id:
        blockers.append("leaderboard_evaluation_trial_mismatch")
    if entry.strategy_card_id not in strategy_card_ids:
        blockers.append("strategy_card_missing")
    if entry.trial_id not in trial_ids:
        blockers.append("experiment_trial_missing")
    if not evaluation.rankable:
        blockers.append("locked_evaluation_not_rankable")
    return blockers


def _leaderboard_blockers(entry: LeaderboardEntry) -> list[str]:
    blockers: list[str] = []
    if not entry.rankable:
        blockers.append("leaderboard_entry_not_rankable")
    if entry.promotion_stage == "BLOCKED":
        blockers.append("leaderboard_entry_promotion_stage_blocked")
    if entry.alpha_score is None:
        blockers.append("leaderboard_entry_alpha_score_missing")
    blockers.extend(entry.blocked_reasons)
    return _unique(blockers)


def _evaluation_blockers(evaluation: LockedEvaluationResult) -> list[str]:
    blockers: list[str] = []
    if not evaluation.passed:
        blockers.append("locked_evaluation_not_passed")
    if not evaluation.rankable:
        blockers.append("locked_evaluation_not_rankable")
    if evaluation.alpha_score is None:
        blockers.append("locked_evaluation_alpha_score_missing")
    blockers.extend(evaluation.blocked_reasons)
    return _unique(blockers)


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item and item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered


def _classify_outcome(
    *,
    excess_return: float,
    max_adverse_excursion: float | None,
    turnover: float | None,
    blocked_reasons: list[str],
) -> tuple[str, str, str, list[str]]:
    if blocked_reasons:
        return "BLOCKED", "PAPER_SHADOW_BLOCKED", "QUARANTINE", []

    attributions: list[str] = []
    if excess_return <= PASS_EXCESS_RETURN:
        attributions.append("negative_excess_return")
    if max_adverse_excursion is not None and max_adverse_excursion > QUARANTINE_ADVERSE_EXCURSION:
        attributions.append("adverse_excursion_breach")
    if turnover is not None and turnover > HIGH_TURNOVER:
        attributions.append("turnover_breach")

    if "adverse_excursion_breach" in attributions or excess_return <= QUARANTINE_EXCESS_RETURN:
        return "QUARANTINE", "PAPER_SHADOW_QUARANTINED", "QUARANTINE", attributions
    if attributions:
        return "FAIL", "PAPER_SHADOW_FAILED", "RETIRE", attributions
    return "PASS", "PAPER_SHADOW_PASSED", "PROMOTION_READY", []
