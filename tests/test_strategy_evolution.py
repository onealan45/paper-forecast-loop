from datetime import UTC, datetime, timedelta
import json

from forecast_loop.cli import main
from forecast_loop.models import PaperShadowOutcome, StrategyCard
from forecast_loop.storage import JsonFileRepository
from forecast_loop.strategy_evolution import refresh_replacement_strategy_hypothesis


def _root_card() -> StrategyCard:
    return StrategyCard(
        card_id="strategy-card:root",
        created_at=datetime(2026, 5, 2, 0, 0, tzinfo=UTC),
        strategy_name="BTC legacy breakout",
        strategy_family="breakout_reversal",
        version="v1",
        status="ACTIVE",
        symbols=["BTC-USD"],
        hypothesis="Legacy breakout card under lineage research.",
        signal_description="Legacy breakout signal.",
        entry_rules=["Enter when breakout confirms."],
        exit_rules=["Exit when breakout fails."],
        risk_rules=["Keep simulated drawdown bounded."],
        parameters={"minimum_after_cost_edge": 0.005},
        data_requirements=["market_candles:BTC-USD:1h"],
        feature_snapshot_ids=[],
        backtest_result_ids=[],
        walk_forward_validation_ids=[],
        event_edge_evaluation_ids=[],
        parent_card_id=None,
        author="test",
        decision_basis="test",
    )


def _source_outcome(root: StrategyCard) -> PaperShadowOutcome:
    created_at = datetime(2026, 5, 2, 1, 0, tzinfo=UTC)
    return PaperShadowOutcome(
        outcome_id="paper-shadow-outcome:root-fail",
        created_at=created_at,
        leaderboard_entry_id="leaderboard-entry:root-fail",
        evaluation_id="locked-evaluation:root-fail",
        strategy_card_id=root.card_id,
        trial_id="experiment-trial:root-fail",
        symbol="BTC-USD",
        window_start=created_at - timedelta(hours=24),
        window_end=created_at,
        observed_return=-0.08,
        benchmark_return=0.02,
        excess_return_after_costs=-0.11,
        max_adverse_excursion=0.18,
        turnover=2.1,
        outcome_grade="FAIL",
        failure_attributions=["drawdown_breach", "weak_baseline_edge"],
        recommended_promotion_stage="QUARANTINED",
        recommended_strategy_action="QUARANTINE_STRATEGY",
        blocked_reasons=["paper_shadow_failed"],
        notes=[],
        decision_basis="test",
    )


def _legacy_replacement(root: StrategyCard, outcome: PaperShadowOutcome) -> StrategyCard:
    return StrategyCard(
        card_id="strategy-card:legacy-replacement",
        created_at=datetime(2026, 5, 2, 2, 0, tzinfo=UTC),
        strategy_name="Replacement for BTC legacy breakout",
        strategy_family=root.strategy_family,
        version="v1.replacement1",
        status="DRAFT",
        symbols=list(root.symbols),
        hypothesis="Legacy replacement template before failure-aware rules existed.",
        signal_description="Legacy replacement signal.",
        entry_rules=["Research a replacement hypothesis."],
        exit_rules=["Exit when invalidated."],
        risk_rules=["Retest before promotion."],
        parameters={
            "replacement_source_lineage_root_card_id": root.card_id,
            "replacement_source_outcome_id": outcome.outcome_id,
            "replacement_failure_attributions": list(outcome.failure_attributions),
            "replacement_required_research": ["locked_backtest", "walk_forward", "paper_shadow"],
            "replacement_not_child_revision": True,
        },
        data_requirements=list(root.data_requirements),
        feature_snapshot_ids=[],
        backtest_result_ids=[],
        walk_forward_validation_ids=[],
        event_edge_evaluation_ids=[],
        parent_card_id=None,
        author="test",
        decision_basis="lineage_replacement_strategy_hypothesis",
    )


def test_refresh_replacement_strategy_hypothesis_creates_failure_aware_successor(tmp_path):
    repository = JsonFileRepository(tmp_path)
    root = _root_card()
    outcome = _source_outcome(root)
    legacy = _legacy_replacement(root, outcome)
    repository.save_strategy_card(root)
    repository.save_strategy_card(legacy)
    repository.save_paper_shadow_outcome(outcome)

    refreshed_at = datetime(2026, 5, 2, 3, 0, tzinfo=UTC)
    result = refresh_replacement_strategy_hypothesis(
        repository=repository,
        created_at=refreshed_at,
        replacement_card_id=legacy.card_id,
        author="codex-test",
    )

    refreshed = result.strategy_card
    assert refreshed.card_id != legacy.card_id
    assert refreshed.created_at == refreshed_at
    assert refreshed.status == "DRAFT"
    assert refreshed.author == "codex-test"
    assert refreshed.decision_basis == "lineage_replacement_strategy_hypothesis"
    assert refreshed.parameters["replacement_refresh_source_card_id"] == legacy.card_id
    assert refreshed.parameters["replacement_source_lineage_root_card_id"] == root.card_id
    assert refreshed.parameters["replacement_source_outcome_id"] == outcome.outcome_id
    assert refreshed.parameters["replacement_strategy_archetype"] == "drawdown_controlled_edge_rebuild"
    assert refreshed.parameters["minimum_after_cost_edge"] == 0.02
    assert refreshed.parameters["max_position_multiplier"] == 0.5
    assert refreshed.parameters["max_adverse_excursion_limit"] == 0.08
    assert any("baseline-edge" in rule for rule in refreshed.entry_rules)
    assert any("max adverse excursion" in rule for rule in refreshed.risk_rules)
    assert [card.card_id for card in repository.load_strategy_cards()] == [
        root.card_id,
        legacy.card_id,
        refreshed.card_id,
    ]


def test_cli_refresh_replacement_strategy_card_outputs_failure_aware_successor(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    root = _root_card()
    outcome = _source_outcome(root)
    legacy = _legacy_replacement(root, outcome)
    repository.save_strategy_card(root)
    repository.save_strategy_card(legacy)
    repository.save_paper_shadow_outcome(outcome)

    assert main(
        [
            "refresh-replacement-strategy-card",
            "--storage-dir",
            str(tmp_path),
            "--replacement-card-id",
            legacy.card_id,
            "--author",
            "codex-test",
            "--created-at",
            "2026-05-02T03:00:00+00:00",
        ]
    ) == 0

    payload = json.loads(capsys.readouterr().out)
    refreshed = payload["replacement_strategy_card"]
    assert refreshed["card_id"] != legacy.card_id
    assert refreshed["author"] == "codex-test"
    assert refreshed["parameters"]["replacement_refresh_source_card_id"] == legacy.card_id
    assert refreshed["parameters"]["replacement_strategy_archetype"] == "drawdown_controlled_edge_rebuild"
