from datetime import UTC, datetime, timedelta
import json

import pytest

from forecast_loop.cli import main
from forecast_loop.lineage_agenda import create_lineage_research_agenda
from forecast_loop.lineage_research_executor import execute_lineage_research_next_task
from forecast_loop.models import PaperShadowOutcome, StrategyCard
from forecast_loop.storage import JsonFileRepository


def _card(
    card_id: str,
    *,
    parent_card_id: str | None = None,
    status: str = "ACTIVE",
) -> StrategyCard:
    return StrategyCard(
        card_id=card_id,
        created_at=datetime(2026, 4, 30, 9, 0, tzinfo=UTC),
        strategy_name=card_id,
        strategy_family="breakout_reversal",
        version="v1",
        status=status,
        symbols=["BTC-USD"],
        hypothesis="BTC breakout/reversal research hypothesis.",
        signal_description="Use regime and shadow outcomes to test BTC direction.",
        entry_rules=["Breakout entry after confirmation."],
        exit_rules=["Exit when breakout fails."],
        risk_rules=["Limit drawdown during paper shadow."],
        parameters={"minimum_after_cost_edge": 0.01},
        data_requirements=["market_candles:BTC-USD:1h"],
        feature_snapshot_ids=[],
        backtest_result_ids=[],
        walk_forward_validation_ids=[],
        event_edge_evaluation_ids=[],
        parent_card_id=parent_card_id,
        author="test",
        decision_basis="test",
    )


def _revision_card(card_id: str, *, parent_card_id: str, source_outcome_id: str) -> StrategyCard:
    base = _card(card_id, parent_card_id=parent_card_id, status="DRAFT")
    return StrategyCard(
        card_id=base.card_id,
        created_at=base.created_at,
        strategy_name=base.strategy_name,
        strategy_family=base.strategy_family,
        version=base.version,
        status=base.status,
        symbols=base.symbols,
        hypothesis=base.hypothesis,
        signal_description=base.signal_description,
        entry_rules=base.entry_rules,
        exit_rules=base.exit_rules,
        risk_rules=base.risk_rules,
        parameters={
            "revision_source_outcome_id": source_outcome_id,
            "revision_failure_attributions": ["negative_excess_return"],
        },
        data_requirements=base.data_requirements,
        feature_snapshot_ids=base.feature_snapshot_ids,
        backtest_result_ids=base.backtest_result_ids,
        walk_forward_validation_ids=base.walk_forward_validation_ids,
        event_edge_evaluation_ids=base.event_edge_evaluation_ids,
        parent_card_id=base.parent_card_id,
        author=base.author,
        decision_basis="paper_shadow_strategy_revision_candidate",
    )


def _outcome(
    outcome_id: str,
    *,
    card_id: str,
    created_at: datetime,
    action: str,
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
        observed_return=-0.08,
        benchmark_return=0.02,
        excess_return_after_costs=-0.11,
        max_adverse_excursion=0.18,
        turnover=2.1,
        outcome_grade="FAIL",
        failure_attributions=attributions,
        recommended_promotion_stage="PAPER_SHADOW_FAILED",
        recommended_strategy_action=action,
        blocked_reasons=["paper_shadow_failed"],
        notes=[],
        decision_basis="test",
    )


def _seed_quarantined_lineage(repository: JsonFileRepository, now: datetime) -> None:
    parent = _card("strategy-card:parent")
    revision = _revision_card(
        "strategy-card:revision",
        parent_card_id=parent.card_id,
        source_outcome_id="paper-shadow-outcome:parent-fail",
    )
    repository.save_strategy_card(parent)
    repository.save_strategy_card(revision)
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:parent-fail",
            card_id=parent.card_id,
            created_at=now,
            action="REVISE_STRATEGY",
            attributions=["negative_excess_return"],
        )
    )
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:revision-fail",
            card_id=revision.card_id,
            created_at=now + timedelta(hours=1),
            action="QUARANTINE_STRATEGY",
            attributions=["drawdown_breach", "weak_baseline_edge"],
        )
    )
    create_lineage_research_agenda(repository=repository, created_at=now + timedelta(hours=2), symbol="BTC-USD")


def test_execute_lineage_research_next_task_creates_replacement_strategy_card(tmp_path):
    now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_quarantined_lineage(repository, now)

    result = execute_lineage_research_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=now + timedelta(hours=3),
    )

    cards = repository.load_strategy_cards()
    replacement = next(card for card in cards if card.card_id == result.created_artifact_ids[0])
    assert result.executed_task_id == "draft_replacement_strategy_hypothesis"
    assert result.before_plan.next_task_id == "draft_replacement_strategy_hypothesis"
    assert result.after_plan.next_task_id is None
    assert result.after_plan.task_by_id("draft_replacement_strategy_hypothesis").status == "completed"
    assert result.after_plan.task_by_id("draft_replacement_strategy_hypothesis").artifact_id == replacement.card_id
    assert replacement.status == "DRAFT"
    assert replacement.parent_card_id is None
    assert replacement.decision_basis == "lineage_replacement_strategy_hypothesis"
    assert replacement.parameters["replacement_source_lineage_root_card_id"] == "strategy-card:parent"
    assert replacement.parameters["replacement_source_outcome_id"] == "paper-shadow-outcome:revision-fail"
    assert replacement.parameters["replacement_not_child_revision"] is True
    assert "drawdown_breach" in replacement.hypothesis
    assert result.automation_run.command == "execute-lineage-research-next-task"
    assert result.automation_run.status == "LINEAGE_RESEARCH_TASK_EXECUTED"
    assert any(
        step["name"] == "latest_lineage_outcome"
        and step["artifact_id"] == "paper-shadow-outcome:revision-fail"
        for step in result.automation_run.steps
    )
    assert any(
        step["name"] == "draft_replacement_strategy_hypothesis"
        and step["status"] == "executed"
        and step["artifact_id"] == replacement.card_id
        for step in result.automation_run.steps
    )
    assert repository.load_automation_runs() == [result.automation_run]


def test_execute_lineage_research_next_task_rejects_non_replacement_task(tmp_path):
    now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    parent = _card("strategy-card:parent")
    repository.save_strategy_card(parent)
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:parent-fail",
            card_id=parent.card_id,
            created_at=now,
            action="REVISE_STRATEGY",
            attributions=["negative_excess_return"],
        )
    )
    create_lineage_research_agenda(repository=repository, created_at=now + timedelta(hours=1), symbol="BTC-USD")

    with pytest.raises(ValueError, match="unsupported_lineage_research_task_execution:propose_strategy_revision"):
        execute_lineage_research_next_task(
            repository=repository,
            storage_dir=tmp_path,
            symbol="BTC-USD",
            created_at=now + timedelta(hours=2),
        )


def test_cli_execute_lineage_research_next_task_outputs_json_and_persists(tmp_path, capsys):
    now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_quarantined_lineage(repository, now)

    assert main(
        [
            "execute-lineage-research-next-task",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-30T13:00:00+00:00",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["executed_task_id"] == "draft_replacement_strategy_hypothesis"
    assert payload["before_plan"]["next_task_id"] == "draft_replacement_strategy_hypothesis"
    assert payload["after_plan"]["next_task_id"] is None
    assert payload["automation_run"]["command"] == "execute-lineage-research-next-task"
    assert len(JsonFileRepository(tmp_path).load_strategy_cards()) == 3
    assert len(JsonFileRepository(tmp_path).load_automation_runs()) == 1
