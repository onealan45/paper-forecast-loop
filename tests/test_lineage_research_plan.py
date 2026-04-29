from datetime import UTC, datetime, timedelta
import json

import pytest

from forecast_loop.cli import main
from forecast_loop.lineage_agenda import create_lineage_research_agenda
from forecast_loop.lineage_research_plan import build_lineage_research_task_plan
from forecast_loop.models import PaperShadowOutcome, StrategyCard
from forecast_loop.storage import JsonFileRepository


def _card(
    card_id: str,
    *,
    parent_card_id: str | None = None,
    status: str = "ACTIVE",
    symbols: list[str] | None = None,
) -> StrategyCard:
    return StrategyCard(
        card_id=card_id,
        created_at=datetime(2026, 4, 30, 9, 0, tzinfo=UTC),
        strategy_name=card_id,
        strategy_family="breakout_reversal",
        version="v1",
        status=status,
        symbols=symbols or ["BTC-USD"],
        hypothesis="BTC breakout/reversal research hypothesis.",
        signal_description="Use regime and shadow outcomes to test BTC direction.",
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


def _revision_card(
    card_id: str,
    *,
    parent_card_id: str,
    source_outcome_id: str,
    failure_attributions: list[str],
) -> StrategyCard:
    parent = _card(card_id, parent_card_id=parent_card_id, status="DRAFT")
    return StrategyCard(
        card_id=parent.card_id,
        created_at=parent.created_at,
        strategy_name=f"{card_id} revision",
        strategy_family=parent.strategy_family,
        version=parent.version,
        status=parent.status,
        symbols=parent.symbols,
        hypothesis="Revision hypothesis under test.",
        signal_description=parent.signal_description,
        entry_rules=parent.entry_rules,
        exit_rules=parent.exit_rules,
        risk_rules=parent.risk_rules,
        parameters={
            "revision_source_outcome_id": source_outcome_id,
            "revision_failure_attributions": failure_attributions,
        },
        data_requirements=parent.data_requirements,
        feature_snapshot_ids=parent.feature_snapshot_ids,
        backtest_result_ids=parent.backtest_result_ids,
        walk_forward_validation_ids=parent.walk_forward_validation_ids,
        event_edge_evaluation_ids=parent.event_edge_evaluation_ids,
        parent_card_id=parent.parent_card_id,
        author=parent.author,
        decision_basis="paper_shadow_strategy_revision_candidate",
    )


def _outcome(
    outcome_id: str,
    *,
    card_id: str,
    created_at: datetime,
    action: str,
    excess: float | None,
    attributions: list[str],
    symbol: str = "BTC-USD",
) -> PaperShadowOutcome:
    return PaperShadowOutcome(
        outcome_id=outcome_id,
        created_at=created_at,
        leaderboard_entry_id=f"leaderboard-entry:{outcome_id}",
        evaluation_id=f"locked-evaluation:{outcome_id}",
        strategy_card_id=card_id,
        trial_id=f"experiment-trial:{outcome_id}",
        symbol=symbol,
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


def test_lineage_research_task_plan_builds_ready_revision_command_for_revise_action(tmp_path):
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
            excess=-0.03,
            attributions=["negative_excess_return"],
        )
    )
    agenda = create_lineage_research_agenda(repository=repository, created_at=now, symbol="BTC-USD")

    plan = build_lineage_research_task_plan(repository=repository, storage_dir=tmp_path, symbol="BTC-USD")

    assert plan.agenda_id == agenda.research_agenda.agenda_id
    assert plan.root_card_id == parent.card_id
    assert plan.latest_outcome_id == "paper-shadow-outcome:parent-fail"
    assert plan.next_task_id == "propose_strategy_revision"
    next_task = plan.task_by_id("propose_strategy_revision")
    assert next_task.status == "ready"
    assert next_task.command_args is not None
    assert "propose-strategy-revision" in next_task.command_args
    assert "paper-shadow-outcome:parent-fail" in next_task.command_args
    assert next_task.required_artifact == "strategy_card"
    assert "negative_excess_return" in next_task.worker_prompt


def test_lineage_research_task_plan_quarantine_requests_new_strategy_hypothesis(tmp_path):
    now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    parent = _card("strategy-card:parent")
    revision = _revision_card(
        "strategy-card:revision",
        parent_card_id=parent.card_id,
        source_outcome_id="paper-shadow-outcome:parent-fail",
        failure_attributions=["negative_excess_return"],
    )
    repository.save_strategy_card(parent)
    repository.save_strategy_card(revision)
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:parent-fail",
            card_id=parent.card_id,
            created_at=now,
            action="REVISE_STRATEGY",
            excess=-0.03,
            attributions=["negative_excess_return"],
        )
    )
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:revision-fail",
            card_id=revision.card_id,
            created_at=now + timedelta(hours=1),
            action="QUARANTINE_STRATEGY",
            excess=-0.08,
            attributions=["drawdown_breach"],
        )
    )
    create_lineage_research_agenda(repository=repository, created_at=now, symbol="BTC-USD")

    plan = build_lineage_research_task_plan(repository=repository, storage_dir=tmp_path, symbol="BTC-USD")

    assert plan.performance_verdict == "惡化"
    assert plan.latest_recommended_strategy_action == "QUARANTINE_STRATEGY"
    assert plan.next_task_id == "draft_replacement_strategy_hypothesis"
    next_task = plan.task_by_id("draft_replacement_strategy_hypothesis")
    assert next_task.status == "ready"
    assert next_task.command_args is None
    assert next_task.required_artifact == "strategy_card"
    assert "新策略" in next_task.worker_prompt
    assert "drawdown_breach" in next_task.worker_prompt


def test_lineage_research_task_plan_filters_agendas_by_requested_symbol(tmp_path):
    now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    shared = _card("strategy-card:shared", symbols=["BTC-USD", "ETH-USD"])
    repository.save_strategy_card(shared)
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:btc-fail",
            card_id=shared.card_id,
            created_at=now,
            action="REVISE_STRATEGY",
            excess=-0.03,
            attributions=["negative_excess_return"],
            symbol="BTC-USD",
        )
    )
    btc_agenda = create_lineage_research_agenda(
        repository=repository,
        created_at=now + timedelta(minutes=10),
        symbol="BTC-USD",
    )
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:eth-fail",
            card_id=shared.card_id,
            created_at=now + timedelta(hours=1),
            action="REVISE_STRATEGY",
            excess=-0.05,
            attributions=["drawdown_breach"],
            symbol="ETH-USD",
        )
    )
    create_lineage_research_agenda(
        repository=repository,
        created_at=now + timedelta(minutes=20),
        symbol="ETH-USD",
    )

    plan = build_lineage_research_task_plan(repository=repository, storage_dir=tmp_path, symbol="BTC-USD")

    assert plan.agenda_id == btc_agenda.research_agenda.agenda_id
    assert plan.latest_outcome_id == "paper-shadow-outcome:btc-fail"


def test_lineage_research_task_plan_routes_improving_lineage_to_cross_sample_verification(tmp_path):
    now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    parent = _card("strategy-card:parent")
    repository.save_strategy_card(parent)
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:baseline",
            card_id=parent.card_id,
            created_at=now,
            action="CONTINUE_SHADOW",
            excess=0.01,
            attributions=[],
        )
    )
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:improved",
            card_id=parent.card_id,
            created_at=now + timedelta(hours=1),
            action="CONTINUE_SHADOW",
            excess=0.04,
            attributions=[],
        )
    )
    create_lineage_research_agenda(repository=repository, created_at=now, symbol="BTC-USD")

    plan = build_lineage_research_task_plan(repository=repository, storage_dir=tmp_path, symbol="BTC-USD")

    assert plan.performance_verdict == "改善"
    assert plan.next_task_id == "verify_cross_sample_persistence"
    next_task = plan.task_by_id("verify_cross_sample_persistence")
    assert next_task.status == "ready"
    assert next_task.required_artifact == "locked_evaluation"
    assert next_task.blocked_reason is None


def test_lineage_research_task_plan_routes_insufficient_evidence_to_shadow_collection(tmp_path):
    now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_strategy_card(_card("strategy-card:parent"))
    create_lineage_research_agenda(repository=repository, created_at=now, symbol="BTC-USD")

    plan = build_lineage_research_task_plan(repository=repository, storage_dir=tmp_path, symbol="BTC-USD")

    assert plan.performance_verdict == "證據不足"
    assert plan.next_task_id == "collect_lineage_shadow_evidence"
    next_task = plan.task_by_id("collect_lineage_shadow_evidence")
    assert next_task.status == "blocked"
    assert next_task.required_artifact == "paper_shadow_outcome"
    assert next_task.blocked_reason == "paper_shadow_outcome_missing"


def test_lineage_research_plan_cli_prints_machine_readable_next_task(tmp_path, capsys):
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
            excess=-0.03,
            attributions=["negative_excess_return"],
        )
    )
    create_lineage_research_agenda(repository=repository, created_at=now, symbol="BTC-USD")

    assert main(["lineage-research-plan", "--storage-dir", str(tmp_path), "--symbol", "BTC-USD"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["lineage_research_task_plan"]["next_task_id"] == "propose_strategy_revision"
    assert payload["lineage_research_task_plan"]["tasks"][1]["command_args"][2] == "propose-strategy-revision"


def test_propose_strategy_revision_accepts_lineage_revise_strategy_action(tmp_path, capsys):
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
            excess=-0.03,
            attributions=["negative_excess_return"],
        )
    )

    assert main(
        [
            "propose-strategy-revision",
            "--storage-dir",
            str(tmp_path),
            "--paper-shadow-outcome-id",
            "paper-shadow-outcome:parent-fail",
            "--created-at",
            "2026-04-30T11:00:00+00:00",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["revision_strategy_card"]["parent_card_id"] == parent.card_id
    assert payload["revision_strategy_card"]["status"] == "DRAFT"
    assert payload["revision_research_agenda"]["decision_basis"] == "paper_shadow_strategy_revision_agenda"


def test_revision_retest_scaffold_accepts_lineage_revise_strategy_action(tmp_path, capsys):
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
            excess=-0.03,
            attributions=["negative_excess_return"],
        )
    )
    assert main(
        [
            "propose-strategy-revision",
            "--storage-dir",
            str(tmp_path),
            "--paper-shadow-outcome-id",
            "paper-shadow-outcome:parent-fail",
            "--created-at",
            "2026-04-30T11:00:00+00:00",
        ]
    ) == 0
    revision_payload = json.loads(capsys.readouterr().out)

    assert main(
        [
            "create-revision-retest-scaffold",
            "--storage-dir",
            str(tmp_path),
            "--revision-card-id",
            revision_payload["revision_strategy_card"]["card_id"],
            "--symbol",
            "BTC-USD",
            "--dataset-id",
            "research-dataset:lineage-revise-strategy",
            "--created-at",
            "2026-04-30T12:00:00+00:00",
        ]
    ) == 0
    scaffold_payload = json.loads(capsys.readouterr().out)

    assert scaffold_payload["revision_retest_scaffold"]["source_outcome_id"] == "paper-shadow-outcome:parent-fail"
    assert scaffold_payload["revision_retest_scaffold"]["experiment_trial"]["status"] == "PENDING"


def test_lineage_research_plan_cli_rejects_missing_agenda_without_traceback(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    repository.save_strategy_card(_card("strategy-card:parent"))

    with pytest.raises(SystemExit) as exc_info:
        main(["lineage-research-plan", "--storage-dir", str(tmp_path), "--symbol", "BTC-USD"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "lineage research agenda not found for symbol: BTC-USD" in captured.err
    assert "Traceback" not in captured.err
