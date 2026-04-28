from __future__ import annotations

from datetime import datetime

from forecast_loop.models import (
    LeaderboardEntry,
    LockedEvaluationResult,
    PaperShadowOutcome,
    ResearchAgenda,
    ResearchAutopilotRun,
)
from forecast_loop.storage import ArtifactRepository


def create_research_agenda(
    *,
    repository: ArtifactRepository,
    created_at: datetime,
    symbol: str,
    title: str,
    hypothesis: str,
    strategy_family: str,
    strategy_card_ids: list[str] | None = None,
    priority: str = "HIGH",
) -> ResearchAgenda:
    strategy_card_ids = strategy_card_ids or []
    agenda = ResearchAgenda(
        agenda_id=ResearchAgenda.build_id(
            symbol=symbol,
            title=title,
            hypothesis=hypothesis,
            target_strategy_family=strategy_family,
            strategy_card_ids=strategy_card_ids,
        ),
        created_at=created_at,
        symbol=symbol,
        title=title,
        hypothesis=hypothesis,
        priority=priority,
        status="OPEN",
        target_strategy_family=strategy_family,
        strategy_card_ids=strategy_card_ids,
        expected_artifacts=[
            "strategy_card",
            "experiment_trial",
            "locked_evaluation",
            "leaderboard_entry",
            "strategy_decision",
            "paper_shadow_outcome",
        ],
        acceptance_criteria=[
            "linked artifacts exist",
            "locked evaluation and leaderboard entry are rankable",
            "paper-shadow outcome determines next research action",
        ],
        blocked_actions=["real_order_submission", "automatic_strategy_mutation"],
        decision_basis="research_autopilot_agenda",
    )
    repository.save_research_agenda(agenda)
    return agenda


def record_research_autopilot_run(
    *,
    repository: ArtifactRepository,
    created_at: datetime,
    agenda_id: str,
    strategy_card_id: str,
    experiment_trial_id: str,
    locked_evaluation_id: str,
    leaderboard_entry_id: str,
    strategy_decision_id: str | None = None,
    paper_shadow_outcome_id: str | None = None,
) -> ResearchAutopilotRun:
    agenda = _find(repository.load_research_agendas(), "agenda_id", agenda_id)
    card = _find(repository.load_strategy_cards(), "card_id", strategy_card_id)
    trial = _find(repository.load_experiment_trials(), "trial_id", experiment_trial_id)
    evaluation = _find(repository.load_locked_evaluation_results(), "evaluation_id", locked_evaluation_id)
    entry = _find(repository.load_leaderboard_entries(), "entry_id", leaderboard_entry_id)
    decision = (
        _find(repository.load_strategy_decisions(), "decision_id", strategy_decision_id)
        if strategy_decision_id
        else None
    )
    outcome = (
        _find(repository.load_paper_shadow_outcomes(), "outcome_id", paper_shadow_outcome_id)
        if paper_shadow_outcome_id
        else None
    )

    blocked = _blocked_reasons(
        agenda=agenda,
        card=card,
        trial=trial,
        evaluation=evaluation,
        entry=entry,
        decision=decision,
        outcome=outcome,
        agenda_id=agenda_id,
        strategy_card_id=strategy_card_id,
        experiment_trial_id=experiment_trial_id,
        locked_evaluation_id=locked_evaluation_id,
        leaderboard_entry_id=leaderboard_entry_id,
        strategy_decision_id=strategy_decision_id,
        paper_shadow_outcome_id=paper_shadow_outcome_id,
    )
    loop_status, next_action = _loop_status_and_action(blocked, evaluation, entry, outcome)
    steps = [
        _step("agenda", agenda_id, agenda is not None),
        _step("strategy_card", strategy_card_id, card is not None),
        _step("experiment_trial", experiment_trial_id, trial is not None),
        _step("locked_evaluation", locked_evaluation_id, evaluation is not None and evaluation.rankable),
        _step("leaderboard", leaderboard_entry_id, entry is not None and entry.rankable),
        _step("paper_decision", strategy_decision_id, decision is not None),
        _step("paper_shadow_outcome", paper_shadow_outcome_id, outcome is not None),
        {"name": "next_research_action", "status": "completed", "artifact_id": next_action},
    ]
    run = ResearchAutopilotRun(
        run_id=ResearchAutopilotRun.build_id(
            agenda_id=agenda_id,
            strategy_card_id=strategy_card_id,
            experiment_trial_id=experiment_trial_id,
            locked_evaluation_id=locked_evaluation_id,
            leaderboard_entry_id=leaderboard_entry_id,
            strategy_decision_id=strategy_decision_id,
            paper_shadow_outcome_id=paper_shadow_outcome_id,
            loop_status=loop_status,
        ),
        created_at=created_at,
        symbol=_symbol(card, entry, outcome),
        agenda_id=agenda_id,
        strategy_card_id=strategy_card_id,
        experiment_trial_id=experiment_trial_id,
        locked_evaluation_id=locked_evaluation_id,
        leaderboard_entry_id=leaderboard_entry_id,
        strategy_decision_id=strategy_decision_id,
        paper_shadow_outcome_id=paper_shadow_outcome_id,
        steps=steps,
        loop_status=loop_status,
        next_research_action=next_action,
        blocked_reasons=blocked,
        decision_basis="research_paper_autopilot_loop",
    )
    repository.save_research_autopilot_run(run)
    return run


def _find(items: list[object], attr: str, value: str | None) -> object | None:
    if value is None:
        return None
    return next((item for item in items if getattr(item, attr) == value), None)


def _blocked_reasons(
    *,
    agenda,
    card,
    trial,
    evaluation: LockedEvaluationResult | None,
    entry: LeaderboardEntry | None,
    decision,
    outcome: PaperShadowOutcome | None,
    agenda_id: str,
    strategy_card_id: str,
    experiment_trial_id: str,
    locked_evaluation_id: str,
    leaderboard_entry_id: str,
    strategy_decision_id: str | None,
    paper_shadow_outcome_id: str | None,
) -> list[str]:
    blocked: list[str] = []
    if agenda is None:
        blocked.append(f"missing_agenda:{agenda_id}")
    if card is None:
        blocked.append(f"missing_strategy_card:{strategy_card_id}")
    if trial is None:
        blocked.append(f"missing_experiment_trial:{experiment_trial_id}")
    if evaluation is None:
        blocked.append(f"missing_locked_evaluation:{locked_evaluation_id}")
    if entry is None:
        blocked.append(f"missing_leaderboard_entry:{leaderboard_entry_id}")
    if strategy_decision_id and decision is None:
        blocked.append(f"missing_strategy_decision:{strategy_decision_id}")
    if strategy_decision_id is None:
        blocked.append("strategy_decision_missing")
    if decision is not None:
        if entry is not None and decision.symbol != entry.symbol:
            blocked.append("strategy_decision_symbol_mismatch")
        if not decision.tradeable:
            blocked.append("strategy_decision_not_tradeable")
        if decision.action in {"STOP_NEW_ENTRIES", "REDUCE_RISK"}:
            blocked.append("strategy_decision_fail_closed_action")
        if decision.blocked_reason:
            blocked.append("strategy_decision_blocked")
    if paper_shadow_outcome_id and outcome is None:
        blocked.append(f"missing_paper_shadow_outcome:{paper_shadow_outcome_id}")
    if agenda is not None and strategy_card_id not in agenda.strategy_card_ids:
        blocked.append("agenda_strategy_card_mismatch")
    if trial is not None:
        if trial.strategy_card_id != strategy_card_id:
            blocked.append("experiment_trial_strategy_card_mismatch")
    if evaluation is not None:
        if evaluation.strategy_card_id != strategy_card_id:
            blocked.append("locked_evaluation_strategy_card_mismatch")
        if evaluation.trial_id != experiment_trial_id:
            blocked.append("locked_evaluation_trial_mismatch")
    if evaluation is not None:
        if not evaluation.rankable:
            blocked.append("locked_evaluation_not_rankable")
        if not evaluation.passed:
            blocked.append("locked_evaluation_not_passed")
        blocked.extend(evaluation.blocked_reasons)
    if entry is not None:
        if entry.strategy_card_id != strategy_card_id:
            blocked.append("leaderboard_entry_strategy_card_mismatch")
        if entry.trial_id != experiment_trial_id:
            blocked.append("leaderboard_entry_trial_mismatch")
        if entry.evaluation_id != locked_evaluation_id:
            blocked.append("leaderboard_entry_evaluation_mismatch")
        if not entry.rankable:
            blocked.append("leaderboard_entry_not_rankable")
        if entry.promotion_stage == "BLOCKED":
            blocked.append("leaderboard_entry_blocked")
        blocked.extend(entry.blocked_reasons)
    if outcome is not None:
        if outcome.leaderboard_entry_id != leaderboard_entry_id:
            blocked.append("paper_shadow_outcome_leaderboard_mismatch")
        if outcome.evaluation_id != locked_evaluation_id:
            blocked.append("paper_shadow_outcome_evaluation_mismatch")
        if outcome.strategy_card_id != strategy_card_id:
            blocked.append("paper_shadow_outcome_strategy_card_mismatch")
        if outcome.trial_id != experiment_trial_id:
            blocked.append("paper_shadow_outcome_trial_mismatch")
        blocked.extend(outcome.blocked_reasons)
        if outcome.recommended_strategy_action in {"RETIRE", "REVISE"}:
            blocked.extend(outcome.failure_attributions)
    return _unique(blocked)


def _loop_status_and_action(
    blocked: list[str],
    evaluation: LockedEvaluationResult | None,
    entry: LeaderboardEntry | None,
    outcome: PaperShadowOutcome | None,
) -> tuple[str, str]:
    evidence_blocked = [
        item
        for item in blocked
        if item.startswith("missing_")
        or item in {"locked_evaluation_not_rankable", "locked_evaluation_not_passed", "leaderboard_entry_not_rankable", "leaderboard_entry_blocked"}
        or "mismatch" in item
        or item == "strategy_decision_missing"
        or item.startswith("strategy_decision_")
    ]
    if evidence_blocked or evaluation is None or entry is None:
        return "BLOCKED", "REPAIR_EVIDENCE_CHAIN"
    if outcome is None:
        return "WAITING_FOR_SHADOW_OUTCOME", "WAIT_FOR_SHADOW_OUTCOME"
    if outcome.recommended_strategy_action == "PROMOTION_READY":
        return "READY_FOR_OPERATOR_REVIEW", "OPERATOR_REVIEW_FOR_PROMOTION"
    if outcome.recommended_strategy_action == "QUARANTINE":
        return "QUARANTINED", "QUARANTINE_STRATEGY_CARD"
    if outcome.recommended_strategy_action in {"RETIRE", "REVISE"}:
        return "REVISION_REQUIRED", "CREATE_REVISION_AGENDA"
    return "WAITING_FOR_SHADOW_OUTCOME", "WAIT_FOR_SHADOW_OUTCOME"


def _step(name: str, artifact_id: str | None, ok: bool) -> dict[str, str | None]:
    if artifact_id is None:
        status = "skipped"
    else:
        status = "completed" if ok else "blocked"
    return {"name": name, "status": status, "artifact_id": artifact_id}


def _symbol(card, entry: LeaderboardEntry | None, outcome: PaperShadowOutcome | None) -> str:
    if outcome is not None:
        return outcome.symbol
    if entry is not None:
        return entry.symbol
    if card is not None and card.symbols:
        return card.symbols[0]
    return "UNKNOWN"


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item and item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered
