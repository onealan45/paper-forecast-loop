from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from forecast_loop.models import ResearchAgenda, StrategyDecision, StrategyResearchDigest
from forecast_loop.storage import ArtifactRepository


DECISION_BLOCKER_AGENDA_BASIS = "decision_blocker_research_agenda"
_BLOCKER_MARKER = "主要研究阻擋："


@dataclass(frozen=True, slots=True)
class DecisionBlockerResearchAgendaResult:
    research_agenda: ResearchAgenda
    strategy_decision: StrategyDecision

    def to_dict(self) -> dict:
        return {
            "research_agenda": self.research_agenda.to_dict(),
            "strategy_decision": self.strategy_decision.to_dict(),
        }


def create_decision_blocker_research_agenda(
    *,
    repository: ArtifactRepository,
    created_at: datetime,
    symbol: str,
) -> DecisionBlockerResearchAgendaResult:
    symbol = symbol.upper()
    decision = _latest_decision(repository.load_strategy_decisions(), symbol)
    if decision is None:
        raise ValueError(f"strategy decision not found for symbol: {symbol}")
    blockers = extract_decision_research_blockers(decision)
    if not blockers:
        raise ValueError(f"latest decision has no research blocker summary for symbol: {symbol}")

    digest = _latest_digest_for_decision(repository.load_strategy_research_digests(), decision)
    strategy_card_ids = [digest.strategy_card_id] if digest and digest.strategy_card_id else []
    title = f"Decision blocker research: {symbol} {decision.action}"
    hypothesis = (
        f"Latest decision {decision.decision_id} is {decision.action} because "
        f"{', '.join(blockers)}. Research should remove these blockers before "
        "BUY/SELL directionality is treated as usable."
    )
    agenda = ResearchAgenda(
        agenda_id=ResearchAgenda.build_id(
            symbol=symbol,
            title=title,
            hypothesis=hypothesis,
            target_strategy_family="decision_blocker_research",
            strategy_card_ids=strategy_card_ids,
        ),
        created_at=created_at,
        symbol=symbol,
        title=title,
        hypothesis=hypothesis,
        priority=_priority(decision, blockers),
        status="OPEN",
        target_strategy_family="decision_blocker_research",
        strategy_card_ids=strategy_card_ids,
        expected_artifacts=_expected_artifacts(blockers),
        acceptance_criteria=[
            "research blockers are explicitly tested with fresh artifacts",
            "model edge, event edge, backtest, and walk-forward evidence are compared against baselines",
            "BUY/SELL gate must remain blocked until blockers improve",
            "updated strategy decision links the new evidence artifacts",
        ],
        blocked_actions=[
            "directional_buy_sell_without_research_evidence",
            "automatic_strategy_promotion_without_retest",
        ],
        decision_basis=DECISION_BLOCKER_AGENDA_BASIS,
    )
    repository.save_research_agenda(agenda)
    return DecisionBlockerResearchAgendaResult(research_agenda=agenda, strategy_decision=decision)


def extract_decision_research_blockers(decision: StrategyDecision) -> list[str]:
    if _BLOCKER_MARKER not in decision.reason_summary:
        return []
    blocker_text = decision.reason_summary.split(_BLOCKER_MARKER, 1)[1].split("。", 1)[0]
    return [item.strip() for item in blocker_text.split("、") if item.strip()]


def _latest_decision(decisions: list[StrategyDecision], symbol: str) -> StrategyDecision | None:
    matches = [decision for decision in decisions if decision.symbol == symbol]
    return max(matches, key=lambda decision: (decision.created_at, decision.decision_id)) if matches else None


def _latest_digest_for_decision(
    digests: list[StrategyResearchDigest],
    decision: StrategyDecision,
) -> StrategyResearchDigest | None:
    matches = [
        digest
        for digest in digests
        if digest.symbol == decision.symbol and digest.decision_id == decision.decision_id
    ]
    return max(matches, key=lambda digest: (digest.created_at, digest.digest_id)) if matches else None


def _priority(decision: StrategyDecision, blockers: list[str]) -> str:
    if decision.action in {"STOP_NEW_ENTRIES", "REDUCE_RISK"}:
        return "HIGH"
    if any("缺失" in blocker or "overfit" in blocker for blocker in blockers):
        return "HIGH"
    return "MEDIUM"


def _expected_artifacts(blockers: list[str]) -> list[str]:
    artifacts = ["strategy_decision", "research_dataset"]
    for blocker in blockers:
        blocker_lower = blocker.lower()
        if "event edge" in blocker_lower:
            _append_unique(artifacts, "event_edge_evaluation")
        if "backtest" in blocker_lower:
            _append_unique(artifacts, "backtest_result")
        if "walk-forward" in blocker_lower:
            _append_unique(artifacts, "walk_forward_validation")
        if "model edge" in blocker_lower or "baseline" in blocker_lower:
            _append_unique(artifacts, "baseline_evaluation")
        if "樣本" in blocker:
            _append_unique(artifacts, "forecast_score")
        if "近期" in blocker:
            _append_unique(artifacts, "recent_score_review")
    return artifacts


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)
