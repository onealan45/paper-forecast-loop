from datetime import UTC, datetime, timedelta

from forecast_loop.models import PaperShadowOutcome, StrategyCard
from forecast_loop.strategy_lineage import build_strategy_lineage_summary


def _card(card_id: str, *, parent_card_id: str | None = None, status: str = "ACTIVE") -> StrategyCard:
    return StrategyCard(
        card_id=card_id,
        created_at=datetime(2026, 4, 29, 9, 0, tzinfo=UTC),
        strategy_name=card_id,
        strategy_family="breakout_reversal",
        version="v1",
        status=status,
        symbols=["BTC-USD"],
        hypothesis="test",
        signal_description="test",
        entry_rules=[],
        exit_rules=[],
        risk_rules=[],
        parameters={},
        data_requirements=[],
        feature_snapshot_ids=[],
        backtest_result_ids=[],
        walk_forward_validation_ids=[],
        event_edge_evaluation_ids=[],
        parent_card_id=parent_card_id,
        author="test",
        decision_basis="test",
    )


def _outcome(
    outcome_id: str,
    *,
    card_id: str,
    created_at: datetime,
    action: str,
    excess: float | None,
    attributions: list[str],
) -> PaperShadowOutcome:
    return PaperShadowOutcome(
        outcome_id=outcome_id,
        created_at=created_at,
        leaderboard_entry_id=f"leaderboard-entry:{outcome_id}",
        evaluation_id=f"locked-evaluation:{outcome_id}",
        strategy_card_id=card_id,
        trial_id=f"experiment-trial:{outcome_id}",
        symbol="BTC-USD",
        window_start=created_at - timedelta(hours=24),
        window_end=created_at,
        observed_return=None,
        benchmark_return=None,
        excess_return_after_costs=excess,
        max_adverse_excursion=None,
        turnover=None,
        outcome_grade="FAIL",
        failure_attributions=attributions,
        recommended_promotion_stage="PAPER_SHADOW_FAILED",
        recommended_strategy_action=action,
        blocked_reasons=[],
        notes=[],
        decision_basis="test",
    )


def test_strategy_lineage_summary_counts_revisions_actions_and_failures():
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    parent = _card("strategy-card:parent")
    revision = _card("strategy-card:revision", parent_card_id=parent.card_id, status="DRAFT")
    sibling = _card("strategy-card:sibling", parent_card_id="strategy-card:other", status="DRAFT")

    summary = build_strategy_lineage_summary(
        root_card=parent,
        strategy_cards=[parent, revision, sibling],
        paper_shadow_outcomes=[
            _outcome(
                "parent-fail",
                card_id=parent.card_id,
                created_at=now,
                action="REVISE_STRATEGY",
                excess=-0.03,
                attributions=["negative_excess_return"],
            ),
            _outcome(
                "revision-fail",
                card_id=revision.card_id,
                created_at=now + timedelta(hours=1),
                action="QUARANTINE_STRATEGY",
                excess=-0.08,
                attributions=["negative_excess_return", "drawdown_breach"],
            ),
        ],
    )

    assert summary.root_card_id == parent.card_id
    assert summary.revision_count == 1
    assert summary.outcome_count == 2
    assert summary.action_counts == {"QUARANTINE_STRATEGY": 1, "REVISE_STRATEGY": 1}
    assert summary.failure_attribution_counts["negative_excess_return"] == 2
    assert summary.best_excess_return_after_costs == -0.03
    assert summary.worst_excess_return_after_costs == -0.08
    assert summary.latest_outcome_id == "revision-fail"


def test_strategy_lineage_summary_resolves_parent_when_current_card_is_revision():
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    parent = _card("strategy-card:parent")
    revision = _card("strategy-card:revision", parent_card_id=parent.card_id, status="DRAFT")

    summary = build_strategy_lineage_summary(
        root_card=revision,
        strategy_cards=[parent, revision],
        paper_shadow_outcomes=[
            _outcome(
                "parent-fail",
                card_id=parent.card_id,
                created_at=now,
                action="REVISE_STRATEGY",
                excess=-0.03,
                attributions=["negative_excess_return"],
            ),
            _outcome(
                "revision-fail",
                card_id=revision.card_id,
                created_at=now + timedelta(hours=1),
                action="QUARANTINE_STRATEGY",
                excess=-0.08,
                attributions=["drawdown_breach"],
            ),
        ],
    )

    assert summary is not None
    assert summary.root_card_id == parent.card_id
    assert summary.revision_card_ids == [revision.card_id]
    assert summary.revision_count == 1
    assert summary.outcome_count == 2
    assert summary.action_counts == {"QUARANTINE_STRATEGY": 1, "REVISE_STRATEGY": 1}
    assert summary.best_excess_return_after_costs == -0.03


def test_strategy_lineage_summary_includes_multi_generation_revisions():
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    parent = _card("strategy-card:parent")
    revision = _card("strategy-card:revision", parent_card_id=parent.card_id, status="DRAFT")
    second_revision = _card("strategy-card:second-revision", parent_card_id=revision.card_id, status="DRAFT")

    summary = build_strategy_lineage_summary(
        root_card=second_revision,
        strategy_cards=[parent, revision, second_revision],
        paper_shadow_outcomes=[
            _outcome(
                "parent-fail",
                card_id=parent.card_id,
                created_at=now,
                action="REVISE_STRATEGY",
                excess=-0.03,
                attributions=["negative_excess_return"],
            ),
            _outcome(
                "revision-fail",
                card_id=revision.card_id,
                created_at=now + timedelta(hours=1),
                action="REVISE_STRATEGY",
                excess=-0.05,
                attributions=["negative_excess_return"],
            ),
            _outcome(
                "second-revision-fail",
                card_id=second_revision.card_id,
                created_at=now + timedelta(hours=2),
                action="QUARANTINE_STRATEGY",
                excess=-0.09,
                attributions=["drawdown_breach"],
            ),
        ],
    )

    assert summary is not None
    assert summary.root_card_id == parent.card_id
    assert summary.revision_card_ids == [revision.card_id, second_revision.card_id]
    assert summary.revision_count == 2
    assert summary.outcome_count == 3
    assert summary.action_counts == {"QUARANTINE_STRATEGY": 1, "REVISE_STRATEGY": 2}
    assert summary.failure_attribution_counts == {"drawdown_breach": 1, "negative_excess_return": 2}
    assert summary.best_excess_return_after_costs == -0.03
    assert summary.worst_excess_return_after_costs == -0.09
    assert summary.latest_outcome_id == "second-revision-fail"
