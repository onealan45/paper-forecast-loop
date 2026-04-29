from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from forecast_loop.models import ResearchAgenda
from forecast_loop.storage import ArtifactRepository
from forecast_loop.strategy_lineage import StrategyLineageSummary, build_strategy_lineage_summary
from forecast_loop.strategy_research import resolve_latest_strategy_research_chain


@dataclass(frozen=True, slots=True)
class LineageResearchAgendaResult:
    research_agenda: ResearchAgenda
    strategy_lineage: StrategyLineageSummary

    def to_dict(self) -> dict:
        return {
            "research_agenda": self.research_agenda.to_dict(),
            "strategy_lineage": asdict(self.strategy_lineage),
        }


def create_lineage_research_agenda(
    *,
    repository: ArtifactRepository,
    created_at: datetime,
    symbol: str,
) -> LineageResearchAgendaResult:
    symbol = symbol.upper()
    strategy_cards = [item for item in repository.load_strategy_cards() if symbol in item.symbols]
    paper_shadow_outcomes = [item for item in repository.load_paper_shadow_outcomes() if item.symbol == symbol]
    chain = resolve_latest_strategy_research_chain(
        symbol=symbol,
        strategy_cards=strategy_cards,
        experiment_trials=repository.load_experiment_trials(),
        locked_evaluations=repository.load_locked_evaluation_results(),
        split_manifests=repository.load_split_manifests(),
        leaderboard_entries=repository.load_leaderboard_entries(),
        paper_shadow_outcomes=paper_shadow_outcomes,
        research_agendas=repository.load_research_agendas(),
        research_autopilot_runs=repository.load_research_autopilot_runs(),
    )
    summary = build_strategy_lineage_summary(
        root_card=chain.strategy_card,
        strategy_cards=strategy_cards,
        paper_shadow_outcomes=paper_shadow_outcomes,
    )
    if summary is None:
        raise ValueError(f"strategy lineage not found for symbol: {symbol}")
    root_card = next(item for item in strategy_cards if item.card_id == summary.root_card_id)
    title = f"Lineage 研究焦點：{root_card.strategy_name}"
    hypothesis = _hypothesis(summary)
    strategy_card_ids = [summary.root_card_id, *summary.revision_card_ids]
    agenda = ResearchAgenda(
        agenda_id=ResearchAgenda.build_id(
            symbol=symbol,
            title=title,
            hypothesis=hypothesis,
            target_strategy_family=root_card.strategy_family,
            strategy_card_ids=strategy_card_ids,
        ),
        created_at=created_at,
        symbol=symbol,
        title=title,
        hypothesis=hypothesis,
        priority=_priority(summary),
        status="OPEN",
        target_strategy_family=root_card.strategy_family,
        strategy_card_ids=strategy_card_ids,
        expected_artifacts=[
            "strategy_revision_or_new_strategy",
            "locked_evaluation",
            "leaderboard_entry",
            "paper_shadow_outcome",
        ],
        acceptance_criteria=[
            "research focus is derived from latest strategy lineage evidence",
            "candidate strategy is evaluated through locked protocol",
            "paper-shadow outcome updates lineage verdict",
        ],
        blocked_actions=["real_order_submission", "automatic_live_execution"],
        decision_basis="strategy_lineage_research_agenda",
    )
    repository.save_research_agenda(agenda)
    return LineageResearchAgendaResult(research_agenda=agenda, strategy_lineage=summary)


def _hypothesis(summary: StrategyLineageSummary) -> str:
    latest_action = summary.latest_recommended_strategy_action or "UNKNOWN"
    return (
        f"下一步研究焦點：{summary.next_research_focus} "
        f"Lineage verdict：{summary.performance_verdict}；"
        f"latest action：{latest_action}。"
    )


def _priority(summary: StrategyLineageSummary) -> str:
    if summary.latest_recommended_strategy_action in {"QUARANTINE_STRATEGY", "REVISE_STRATEGY"}:
        return "HIGH"
    if summary.performance_verdict in {"惡化", "偏弱", "證據不足"}:
        return "HIGH"
    if summary.performance_verdict in {"改善", "偏強"}:
        return "MEDIUM"
    return "LOW"
