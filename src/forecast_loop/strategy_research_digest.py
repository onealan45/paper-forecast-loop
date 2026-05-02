from __future__ import annotations

from datetime import UTC, datetime

from forecast_loop.models import (
    BacktestResult,
    EventEdgeEvaluation,
    StrategyCard,
    StrategyDecision,
    StrategyResearchDigest,
    WalkForwardValidation,
)
from forecast_loop.storage import ArtifactRepository
from forecast_loop.decision_research_agenda import extract_decision_research_blockers
from forecast_loop.strategy_lineage import build_strategy_lineage_summary
from forecast_loop.strategy_research import resolve_latest_strategy_research_chain
from forecast_loop.strategy_research_display import (
    build_strategy_research_conclusion,
    format_failure_attributions,
    format_research_action,
)


_MAX_RULE_SUMMARY_CHARS = 180


def record_strategy_research_digest(
    *,
    repository: ArtifactRepository,
    symbol: str,
    created_at: datetime | None = None,
) -> StrategyResearchDigest:
    digest = build_strategy_research_digest(
        repository=repository,
        symbol=symbol,
        created_at=created_at,
    )
    repository.save_strategy_research_digest(digest)
    return digest


def build_strategy_research_digest(
    *,
    repository: ArtifactRepository,
    symbol: str,
    created_at: datetime | None = None,
) -> StrategyResearchDigest:
    created_at = created_at or datetime.now(tz=UTC)
    symbol = symbol.upper()
    strategy_cards = [
        card for card in _artifacts_as_of(repository.load_strategy_cards(), created_at) if symbol in card.symbols
    ]
    paper_shadow_outcomes = [
        outcome
        for outcome in _artifacts_as_of(repository.load_paper_shadow_outcomes(), created_at)
        if outcome.symbol == symbol
    ]
    chain = resolve_latest_strategy_research_chain(
        symbol=symbol,
        strategy_cards=strategy_cards,
        experiment_trials=_artifacts_as_of(repository.load_experiment_trials(), created_at),
        locked_evaluations=_artifacts_as_of(
            repository.load_locked_evaluation_results(),
            created_at,
        ),
        split_manifests=_artifacts_as_of(repository.load_split_manifests(), created_at),
        leaderboard_entries=_artifacts_as_of(repository.load_leaderboard_entries(), created_at),
        paper_shadow_outcomes=paper_shadow_outcomes,
        research_agendas=_artifacts_as_of(repository.load_research_agendas(), created_at),
        research_autopilot_runs=_artifacts_as_of(
            repository.load_research_autopilot_runs(),
            created_at,
        ),
        prefer_latest_anchor=True,
    )
    lineage = build_strategy_lineage_summary(
        root_card=chain.strategy_card,
        strategy_cards=strategy_cards,
        paper_shadow_outcomes=paper_shadow_outcomes,
    )
    top_failure_attributions = _top_failure_attributions(
        lineage.failure_attribution_counts if lineage else {},
        chain.paper_shadow_outcome.failure_attributions if chain.paper_shadow_outcome else [],
    )
    next_research_action = _next_research_action(chain, lineage)
    evidence_artifact_ids = _evidence_artifact_ids(chain, lineage)
    latest_decision = _latest_strategy_decision(
        _artifacts_as_of(repository.load_strategy_decisions(), created_at),
        symbol,
    )
    decision_research_blockers = (
        extract_decision_research_blockers(latest_decision) if latest_decision else []
    )
    if latest_decision is not None:
        _append_id(evidence_artifact_ids, latest_decision.decision_id)
    latest_event_edge = _latest_symbol_artifact(
        repository.load_event_edge_evaluations(),
        symbol=symbol,
        as_of=created_at,
    )
    latest_backtest = _latest_symbol_artifact(
        repository.load_backtest_results(),
        symbol=symbol,
        as_of=created_at,
    )
    latest_walk_forward = _latest_symbol_artifact(
        repository.load_walk_forward_validations(),
        symbol=symbol,
        as_of=created_at,
    )
    _append_id(
        evidence_artifact_ids,
        latest_event_edge.evaluation_id if latest_event_edge else None,
    )
    _append_id(
        evidence_artifact_ids,
        latest_backtest.result_id if latest_backtest else None,
    )
    _append_id(
        evidence_artifact_ids,
        latest_walk_forward.validation_id if latest_walk_forward else None,
    )
    lineage_latest_outcome_id = lineage.latest_outcome_id if lineage else None
    research_summary = build_strategy_research_conclusion(
        card=chain.strategy_card,
        outcome=chain.paper_shadow_outcome,
        autopilot=chain.research_autopilot_run,
        next_research_action=next_research_action,
    )
    evidence_summary = _research_evidence_summary(
        latest_event_edge=latest_event_edge,
        latest_backtest=latest_backtest,
        latest_walk_forward=latest_walk_forward,
    )
    if evidence_summary:
        research_summary = f"{research_summary} 研究證據：{evidence_summary}"

    return StrategyResearchDigest(
        digest_id=StrategyResearchDigest.build_id(
            created_at=created_at,
            symbol=symbol,
            strategy_card_id=chain.strategy_card.card_id if chain.strategy_card else None,
            paper_shadow_outcome_id=(
                chain.paper_shadow_outcome.outcome_id if chain.paper_shadow_outcome else None
            ),
            autopilot_run_id=chain.research_autopilot_run.run_id if chain.research_autopilot_run else None,
            lineage_latest_outcome_id=lineage_latest_outcome_id,
        ),
        created_at=created_at,
        symbol=symbol,
        strategy_card_id=chain.strategy_card.card_id if chain.strategy_card else None,
        strategy_name=chain.strategy_card.strategy_name if chain.strategy_card else "no_strategy_card",
        strategy_status=chain.strategy_card.status if chain.strategy_card else None,
        hypothesis=chain.strategy_card.hypothesis if chain.strategy_card else "",
        paper_shadow_outcome_id=(
            chain.paper_shadow_outcome.outcome_id if chain.paper_shadow_outcome else None
        ),
        outcome_grade=chain.paper_shadow_outcome.outcome_grade if chain.paper_shadow_outcome else None,
        excess_return_after_costs=(
            chain.paper_shadow_outcome.excess_return_after_costs if chain.paper_shadow_outcome else None
        ),
        recommended_strategy_action=(
            chain.paper_shadow_outcome.recommended_strategy_action if chain.paper_shadow_outcome else None
        ),
        top_failure_attributions=top_failure_attributions,
        lineage_root_card_id=lineage.root_card_id if lineage else None,
        lineage_revision_count=lineage.revision_count if lineage else 0,
        lineage_outcome_count=lineage.outcome_count if lineage else 0,
        lineage_primary_failure_attribution=(
            lineage.primary_failure_attribution if lineage else None
        ),
        lineage_next_research_focus=lineage.next_research_focus if lineage else None,
        next_research_action=next_research_action,
        autopilot_run_id=chain.research_autopilot_run.run_id if chain.research_autopilot_run else None,
        evidence_artifact_ids=evidence_artifact_ids,
        research_summary=research_summary,
        next_step_rationale=_next_step_rationale(
            next_research_action=next_research_action,
            lineage_focus=lineage.next_research_focus if lineage else None,
            primary_failure=lineage.primary_failure_attribution if lineage else None,
        ),
        decision_basis="strategy_research_digest_v1",
        strategy_rule_summary=_strategy_rule_summary(chain.strategy_card),
        decision_id=latest_decision.decision_id if latest_decision else None,
        decision_action=latest_decision.action if latest_decision else None,
        decision_blocked_reason=latest_decision.blocked_reason if latest_decision else None,
        decision_research_blockers=decision_research_blockers,
        decision_reason_summary=latest_decision.reason_summary if latest_decision else None,
    )


def _top_failure_attributions(
    failure_counts: dict[str, int],
    current_failure_attributions: list[str],
) -> list[str]:
    if failure_counts:
        return [
            attribution
            for attribution, _count in sorted(
                failure_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]
    return list(dict.fromkeys(current_failure_attributions))


def _next_research_action(chain, lineage) -> str | None:
    if chain.research_autopilot_run is not None:
        return chain.research_autopilot_run.next_research_action
    if chain.leaderboard_entry is not None and chain.paper_shadow_outcome is None:
        return "WAIT_FOR_PAPER_SHADOW_OUTCOME"
    if lineage is not None and lineage.latest_recommended_strategy_action is not None:
        return lineage.latest_recommended_strategy_action
    if chain.paper_shadow_outcome is not None:
        return chain.paper_shadow_outcome.recommended_strategy_action
    return None


def _evidence_artifact_ids(chain, lineage) -> list[str]:
    ids: list[str] = []
    for item in (
        chain.strategy_card,
        chain.experiment_trial,
        chain.locked_evaluation,
        chain.leaderboard_entry,
        chain.paper_shadow_outcome,
        chain.research_agenda,
        chain.research_autopilot_run,
    ):
        _append_artifact_id(ids, item)
    if lineage is not None:
        for outcome in lineage.outcome_nodes:
            _append_id(ids, outcome.outcome_id)
        for card_id in lineage.revision_card_ids:
            _append_id(ids, card_id)
        for card_id in lineage.replacement_card_ids:
            _append_id(ids, card_id)
    return ids


def _append_artifact_id(ids: list[str], item) -> None:
    if item is None:
        return
    for attr in (
        "card_id",
        "outcome_id",
        "entry_id",
        "evaluation_id",
        "trial_id",
        "run_id",
        "agenda_id",
    ):
        value = getattr(item, attr, None)
        if isinstance(value, str):
            _append_id(ids, value)
            return


def _append_id(ids: list[str], artifact_id: str | None) -> None:
    if artifact_id and artifact_id not in ids:
        ids.append(artifact_id)


def _artifacts_as_of(items: list, as_of: datetime) -> list:
    return [
        item
        for item in items
        if getattr(item, "created_at", as_of) <= as_of
    ]


def _latest_strategy_decision(
    decisions: list[StrategyDecision],
    symbol: str,
) -> StrategyDecision | None:
    for decision in reversed(decisions):
        if decision.symbol == symbol:
            return decision
    return None


def _latest_symbol_artifact(items: list, *, symbol: str, as_of: datetime):
    matches = [
        item
        for item in items
        if getattr(item, "symbol", None) == symbol and getattr(item, "created_at", as_of) <= as_of
    ]
    return max(matches, key=lambda item: item.created_at) if matches else None


def _research_evidence_summary(
    *,
    latest_event_edge: EventEdgeEvaluation | None,
    latest_backtest: BacktestResult | None,
    latest_walk_forward: WalkForwardValidation | None,
) -> str:
    parts: list[str] = []
    if latest_event_edge is not None:
        passed = "是" if latest_event_edge.passed else "否"
        flags = _format_flags(latest_event_edge.flags)
        parts.append(
            "Event edge："
            f"樣本 {latest_event_edge.sample_n}，"
            f"after-cost edge {_format_signed_pct(latest_event_edge.average_excess_return_after_costs)}，"
            f"hit-rate {_format_unsigned_pct(latest_event_edge.hit_rate)}，"
            f"pass {passed}，"
            f"flags {flags}"
        )
    if latest_backtest is not None:
        parts.append(
            "Backtest："
            f"策略 {_format_signed_pct(latest_backtest.strategy_return)}，"
            f"benchmark {_format_signed_pct(latest_backtest.benchmark_return)}，"
            f"max DD {_format_unsigned_pct(latest_backtest.max_drawdown)}，"
            f"win-rate {_format_unsigned_pct(latest_backtest.win_rate)}，"
            f"trades {latest_backtest.trade_count}"
        )
    if latest_walk_forward is not None:
        flags = _format_flags(latest_walk_forward.overfit_risk_flags)
        parts.append(
            "Walk-forward："
            f"excess {_format_signed_pct(latest_walk_forward.average_excess_return)}，"
            f"windows {latest_walk_forward.window_count}，"
            f"test win-rate {_format_unsigned_pct(latest_walk_forward.test_win_rate)}，"
            f"overfit windows {latest_walk_forward.overfit_window_count}，"
            f"flags {flags}"
        )
    return "；".join(parts)


def _format_signed_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:+.2f}%"


def _format_unsigned_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{abs(value) * 100:.2f}%"


def _format_flags(flags: list[str]) -> str:
    return ", ".join(flags[:5]) if flags else "none"


def _next_step_rationale(
    *,
    next_research_action: str | None,
    lineage_focus: str | None,
    primary_failure: str | None,
) -> str:
    if next_research_action == "WAIT_FOR_PAPER_SHADOW_OUTCOME":
        return (
            "已有 leaderboard entry，但尚未有 post-entry paper-shadow observation；"
            "等待下一個完整觀察視窗，不捏造未來報酬。"
        )
    if lineage_focus:
        if primary_failure:
            readable_failure = format_failure_attributions([primary_failure])
            return lineage_focus.replace(primary_failure, readable_failure)
        return lineage_focus
    if next_research_action:
        return f"下一步依研究 autopilot 執行 {format_research_action(next_research_action)}。"
    return "目前沒有足夠策略研究證據，先補齊策略卡、回測、paper-shadow 與 lineage 證據。"


def _strategy_rule_summary(card: StrategyCard | None) -> list[str]:
    if card is None:
        return []
    summary: list[str] = []
    _append_summary(summary, "假說", card.hypothesis)
    _append_summary(summary, "訊號", card.signal_description)
    if card.entry_rules:
        _append_summary(summary, "進場", card.entry_rules[0])
    if card.exit_rules:
        _append_summary(summary, "出場", card.exit_rules[0])
    if card.risk_rules:
        _append_summary(summary, "風控", card.risk_rules[0])
    controls = card.parameters.get("source_failure_controls")
    if isinstance(controls, list) and controls:
        _append_summary(summary, "失敗控制", ", ".join(str(item) for item in controls[:5]))
    required_research = card.parameters.get("replacement_required_research")
    if isinstance(required_research, list) and required_research:
        _append_summary(summary, "驗證門檻", ", ".join(str(item) for item in required_research[:5]))
    return summary


def _append_summary(summary: list[str], label: str, value: str | None) -> None:
    if value:
        prefix = f"{label}: "
        summary.append(f"{prefix}{_compact_rule_summary_text(value, max_chars=_MAX_RULE_SUMMARY_CHARS - len(prefix))}")


def _compact_rule_summary_text(value: str, *, max_chars: int = _MAX_RULE_SUMMARY_CHARS) -> str:
    text = " ".join(value.split())
    if len(text) <= max_chars:
        return text

    for marker in (". ", "。", "；", "; "):
        marker_index = text.find(marker)
        if marker_index <= 0:
            continue
        end_index = marker_index + len(marker.rstrip())
        first_sentence = text[:end_index].strip()
        if first_sentence and len(first_sentence) <= max_chars:
            return first_sentence

    ellipsis = "..."
    cutoff = max_chars - len(ellipsis)
    word_cutoff = text.rfind(" ", 0, cutoff)
    if word_cutoff >= 80:
        cutoff = word_cutoff
    return text[:cutoff].rstrip(" ,;:") + ellipsis
