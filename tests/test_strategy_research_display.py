from datetime import UTC, datetime, timedelta

from forecast_loop.models import PaperShadowOutcome, ResearchAutopilotRun, StrategyCard
from forecast_loop.strategy_research_display import build_strategy_research_conclusion


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
        "目前策略 BTC breakout candidate：paper-shadow FAIL，after-cost excess -2.50%，"
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
