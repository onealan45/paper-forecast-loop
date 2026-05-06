from datetime import UTC, datetime, timedelta

from forecast_loop.models import EventEdgeEvaluation, PaperShadowOutcome, ResearchAutopilotRun, StrategyCard
from forecast_loop.strategy_research_display import (
    build_strategy_research_conclusion,
    format_event_edge_input_manifest,
    format_promotion_stage,
    format_strategy_card_status,
)


def _strategy_card(now: datetime) -> StrategyCard:
    return StrategyCard(
        card_id="strategy-card:test",
        created_at=now,
        strategy_name="BTC breakout candidate",
        strategy_family="breakout",
        version="v1",
        status="ACTIVE",
        symbols=["BTC-USD"],
        hypothesis="Breakouts should persist after volume confirmation.",
        signal_description="Breakout with volume.",
        entry_rules=[],
        exit_rules=[],
        risk_rules=[],
        parameters={},
        data_requirements=[],
        feature_snapshot_ids=[],
        backtest_result_ids=[],
        walk_forward_validation_ids=[],
        event_edge_evaluation_ids=[],
        parent_card_id=None,
        author="test",
        decision_basis="test",
    )


def test_build_strategy_research_conclusion_summarizes_shadow_failure():
    now = datetime(2026, 5, 1, tzinfo=UTC)
    card = _strategy_card(now)
    outcome = PaperShadowOutcome(
        outcome_id="paper-shadow-outcome:test",
        created_at=now,
        leaderboard_entry_id="leaderboard-entry:test",
        evaluation_id="locked-evaluation:test",
        strategy_card_id=card.card_id,
        trial_id="experiment-trial:test",
        symbol="BTC-USD",
        window_start=now - timedelta(hours=24),
        window_end=now,
        observed_return=-0.01,
        benchmark_return=0.01,
        excess_return_after_costs=-0.025,
        max_adverse_excursion=0.04,
        turnover=1.2,
        outcome_grade="FAIL",
        failure_attributions=["negative_excess_return"],
        recommended_promotion_stage="PAPER_SHADOW_FAILED",
        recommended_strategy_action="REVISE_STRATEGY",
        blocked_reasons=["paper_shadow_failed"],
        notes=[],
        decision_basis="test",
    )
    autopilot = ResearchAutopilotRun(
        run_id="research-autopilot-run:test",
        created_at=now,
        symbol="BTC-USD",
        agenda_id="research-agenda:test",
        strategy_card_id=card.card_id,
        experiment_trial_id="experiment-trial:test",
        locked_evaluation_id="locked-evaluation:test",
        leaderboard_entry_id="leaderboard-entry:test",
        strategy_decision_id=None,
        paper_shadow_outcome_id=outcome.outcome_id,
        steps=[],
        loop_status="REVISION_REQUIRED",
        next_research_action="REVISE_STRATEGY",
        blocked_reasons=["paper_shadow_failed"],
        decision_basis="test",
    )

    assert build_strategy_research_conclusion(card=card, outcome=outcome, autopilot=autopilot) == (
        "目前策略 BTC breakout candidate：paper-shadow 失敗 (FAIL)，扣成本超額報酬 -2.50%，"
        "失敗歸因 負超額報酬 (negative_excess_return)；下一步 修訂策略 (REVISE_STRATEGY)。"
    )


def test_build_strategy_research_conclusion_formats_next_action_without_outcome():
    now = datetime(2026, 5, 1, tzinfo=UTC)
    card = _strategy_card(now)
    autopilot = ResearchAutopilotRun(
        run_id="research-autopilot-run:test",
        created_at=now,
        symbol="BTC-USD",
        agenda_id="research-agenda:test",
        strategy_card_id=card.card_id,
        experiment_trial_id=None,
        locked_evaluation_id=None,
        leaderboard_entry_id=None,
        strategy_decision_id=None,
        paper_shadow_outcome_id=None,
        steps=[],
        loop_status="REPAIR_REQUIRED",
        next_research_action="REPAIR_EVIDENCE_CHAIN",
        blocked_reasons=["missing_evidence"],
        decision_basis="test",
    )

    assert (
        build_strategy_research_conclusion(card=card, outcome=None, autopilot=autopilot)
        == "目前策略 BTC breakout candidate：尚未有 paper-shadow 結果；下一步 修復證據鏈 (REPAIR_EVIDENCE_CHAIN)。"
    )


def test_build_strategy_research_conclusion_handles_missing_card():
    assert (
        build_strategy_research_conclusion(card=None, outcome=None, autopilot=None)
        == "目前沒有策略卡，無法形成策略研究結論。"
    )


def test_format_promotion_stage_keeps_raw_code_with_readable_label():
    assert format_promotion_stage("CANDIDATE") == "候選策略 (CANDIDATE)"
    assert format_promotion_stage("BLOCKED") == "已阻擋 (BLOCKED)"
    assert format_promotion_stage("UNKNOWN_STAGE") == "UNKNOWN_STAGE"


def test_format_strategy_card_status_keeps_raw_code_with_readable_label():
    assert format_strategy_card_status("ACTIVE") == "啟用 (ACTIVE)"
    assert format_strategy_card_status("DRAFT") == "草稿 (DRAFT)"
    assert format_strategy_card_status("QUARANTINED") == "隔離中 (QUARANTINED)"
    assert format_strategy_card_status("UNKNOWN_STATUS") == "UNKNOWN_STATUS"


def _event_edge_evaluation(now: datetime) -> EventEdgeEvaluation:
    return EventEdgeEvaluation(
        evaluation_id="event-edge:display",
        event_family="crypto_flow",
        event_type="CRYPTO_FLOW",
        symbol="BTC-USD",
        created_at=now,
        split="historical_event_sample",
        horizon_hours=24,
        sample_n=2,
        average_forward_return=-0.02,
        average_benchmark_return=-0.008,
        average_excess_return_after_costs=-0.011366,
        hit_rate=0.0,
        max_adverse_excursion_p50=-0.03,
        max_adverse_excursion_p90=-0.05,
        max_drawdown_if_traded=-0.09,
        turnover=2.0,
        estimated_cost_bps=15.0,
        dsr=None,
        white_rc_p=None,
        stability_score=None,
        passed=False,
        blocked_reason="non_positive_after_cost_edge",
        flags=["insufficient_sample_size", "non_positive_after_cost_edge"],
    )


def test_format_event_edge_input_manifest_summarizes_complete_manifest():
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    edge = _event_edge_evaluation(now)
    edge.input_event_ids = ["canonical-event:a", "canonical-event:b"]
    edge.input_reaction_check_ids = ["market-reaction:a", "market-reaction:b"]
    edge.input_candle_ids = ["market-candle:a", "market-candle:b", "market-candle:c"]
    edge.input_watermark = now - timedelta(hours=1)

    assert (
        format_event_edge_input_manifest(edge)
        == "輸入：事件 2；反應 2；K線 3；watermark 2026-05-01T07:00:00+00:00"
    )


def test_format_event_edge_input_manifest_omits_legacy_or_partial_manifest():
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    legacy_edge = _event_edge_evaluation(now)
    partial_edge = _event_edge_evaluation(now)
    partial_edge.input_watermark = now

    assert format_event_edge_input_manifest(legacy_edge) == ""
    assert format_event_edge_input_manifest(partial_edge) == ""
