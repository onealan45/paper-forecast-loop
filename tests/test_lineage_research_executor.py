from datetime import UTC, datetime, timedelta
import json

import pytest

from forecast_loop.cli import main
from forecast_loop.lineage_agenda import create_lineage_research_agenda
from forecast_loop.lineage_research_executor import execute_lineage_research_next_task
from forecast_loop.models import PaperShadowOutcome, ResearchDataset, StrategyCard
from forecast_loop.revision_retest import create_revision_retest_scaffold
from forecast_loop.revision_retest_executor import execute_revision_retest_next_task
from forecast_loop.revision_retest_plan import build_revision_retest_task_plan
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
    excess: float = -0.11,
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
        excess_return_after_costs=excess,
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


def test_execute_lineage_research_next_task_creates_cross_sample_validation_agenda(tmp_path):
    now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_quarantined_lineage(repository, now)
    replacement_result = execute_lineage_research_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=now + timedelta(hours=3),
    )
    replacement_card_id = replacement_result.created_artifact_ids[0]
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:replacement-pass",
            card_id=replacement_card_id,
            created_at=now + timedelta(hours=4),
            action="PROMOTION_READY",
            attributions=[],
            excess=0.04,
        )
    )

    result = execute_lineage_research_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=now + timedelta(hours=5),
    )

    agendas = repository.load_research_agendas()
    cross_sample = next(
        agenda for agenda in agendas if agenda.decision_basis == "lineage_cross_sample_validation_agenda"
    )
    assert result.executed_task_id == "verify_cross_sample_persistence"
    assert result.before_plan.next_task_id == "verify_cross_sample_persistence"
    assert result.after_plan.task_by_id("verify_cross_sample_persistence").status == "completed"
    assert result.after_plan.next_task_id is None
    assert result.created_artifact_ids == [cross_sample.agenda_id]
    assert cross_sample.strategy_card_ids == ["strategy-card:parent", replacement_card_id]
    assert replacement_card_id in cross_sample.hypothesis
    assert "paper-shadow-outcome:replacement-pass" in cross_sample.hypothesis
    assert "latest_lineage_outcome=paper-shadow-outcome:replacement-pass" in cross_sample.acceptance_criteria
    assert cross_sample.expected_artifacts == [
        "locked_evaluation",
        "walk_forward_validation",
        "paper_shadow_outcome",
    ]
    assert any(
        step["name"] == "verify_cross_sample_persistence"
        and step["status"] == "executed"
        and step["artifact_id"] == cross_sample.agenda_id
        for step in result.automation_run.steps
    )


def test_lineage_replacement_strategy_can_start_retest_scaffold(tmp_path):
    now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_quarantined_lineage(repository, now)
    replacement_result = execute_lineage_research_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=now + timedelta(hours=3),
    )
    replacement_card_id = replacement_result.created_artifact_ids[0]

    scaffold = create_revision_retest_scaffold(
        repository=repository,
        created_at=now + timedelta(hours=4),
        revision_card_id=replacement_card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:replacement-retest",
        max_trials=20,
        seed=17,
    )
    plan = build_revision_retest_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        revision_card_id=replacement_card_id,
        symbol="BTC-USD",
    )

    assert scaffold.strategy_card.card_id == replacement_card_id
    assert scaffold.source_outcome.outcome_id == "paper-shadow-outcome:revision-fail"
    assert scaffold.experiment_trial.status == "PENDING"
    assert scaffold.experiment_trial.strategy_card_id == replacement_card_id
    assert scaffold.experiment_trial.parameters["revision_retest_protocol"] == "pr14-v1"
    assert scaffold.experiment_trial.parameters["revision_source_outcome_id"] == "paper-shadow-outcome:revision-fail"
    assert scaffold.experiment_trial.parameters["revision_retest_kind"] == "lineage_replacement"
    assert scaffold.experiment_trial.parameters["replacement_source_lineage_root_card_id"] == "strategy-card:parent"
    assert plan.strategy_card_id == replacement_card_id
    assert plan.source_outcome_id == "paper-shadow-outcome:revision-fail"
    assert plan.pending_trial_id == scaffold.experiment_trial.trial_id
    assert plan.next_task_id == "lock_evaluation_protocol"


def test_replacement_strategy_plan_rejects_non_quarantine_source_outcome(tmp_path):
    now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_quarantined_lineage(repository, now)
    base = _card("strategy-card:replacement", status="DRAFT")
    replacement = StrategyCard(
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
            "replacement_source_lineage_root_card_id": "strategy-card:parent",
            "replacement_source_outcome_id": "paper-shadow-outcome:parent-fail",
        },
        data_requirements=base.data_requirements,
        feature_snapshot_ids=base.feature_snapshot_ids,
        backtest_result_ids=base.backtest_result_ids,
        walk_forward_validation_ids=base.walk_forward_validation_ids,
        event_edge_evaluation_ids=base.event_edge_evaluation_ids,
        parent_card_id=None,
        author=base.author,
        decision_basis="lineage_replacement_strategy_hypothesis",
    )
    repository.save_strategy_card(replacement)

    with pytest.raises(ValueError, match="source paper shadow outcome does not require replacement"):
        build_revision_retest_task_plan(
            repository=repository,
            storage_dir=tmp_path,
            revision_card_id=replacement.card_id,
            symbol="BTC-USD",
        )


def test_cli_create_revision_retest_scaffold_accepts_lineage_replacement_card(tmp_path, capsys):
    now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_quarantined_lineage(repository, now)
    replacement_result = execute_lineage_research_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=now + timedelta(hours=3),
    )

    assert main(
        [
            "create-revision-retest-scaffold",
            "--storage-dir",
            str(tmp_path),
            "--revision-card-id",
            replacement_result.created_artifact_ids[0],
            "--symbol",
            "BTC-USD",
            "--dataset-id",
            "research-dataset:replacement-retest",
            "--max-trials",
            "20",
            "--seed",
            "17",
            "--created-at",
            "2026-04-30T14:00:00+00:00",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["revision_retest_scaffold"]["strategy_card_id"] == replacement_result.created_artifact_ids[0]
    assert payload["revision_retest_scaffold"]["source_outcome_id"] == "paper-shadow-outcome:revision-fail"
    assert JsonFileRepository(tmp_path).load_experiment_trials()[0].parameters["revision_retest_kind"] == "lineage_replacement"


def test_execute_revision_retest_next_task_scaffolds_lineage_replacement_card(tmp_path):
    now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_quarantined_lineage(repository, now)
    replacement_result = execute_lineage_research_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=now + timedelta(hours=3),
    )
    repository.save_research_dataset(
        ResearchDataset(
            dataset_id="research-dataset:replacement-retest",
            created_at=now + timedelta(hours=3, minutes=30),
            symbol="BTC-USD",
            row_count=0,
            leakage_status="passed",
            leakage_findings=[],
            forecast_ids=[],
            score_ids=[],
            rows=[],
            decision_basis="test",
        )
    )

    result = execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=now + timedelta(hours=4),
        revision_card_id=replacement_result.created_artifact_ids[0],
    )

    trial = repository.load_experiment_trials()[0]
    assert result.executed_task_id == "create_revision_retest_scaffold"
    assert result.before_plan.next_task_id == "create_revision_retest_scaffold"
    assert result.after_plan.next_task_id == "lock_evaluation_protocol"
    assert result.created_artifact_ids == [trial.trial_id]
    assert trial.dataset_id == "research-dataset:replacement-retest"
    assert trial.strategy_card_id == replacement_result.created_artifact_ids[0]
    assert trial.parameters["revision_retest_kind"] == "lineage_replacement"
    assert trial.parameters["replacement_source_lineage_root_card_id"] == "strategy-card:parent"


def test_cli_execute_revision_retest_next_task_scaffolds_lineage_replacement_card(tmp_path, capsys):
    now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_quarantined_lineage(repository, now)
    replacement_result = execute_lineage_research_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=now + timedelta(hours=3),
    )
    repository.save_research_dataset(
        ResearchDataset(
            dataset_id="research-dataset:replacement-retest",
            created_at=now + timedelta(hours=3, minutes=30),
            symbol="BTC-USD",
            row_count=0,
            leakage_status="passed",
            leakage_findings=[],
            forecast_ids=[],
            score_ids=[],
            rows=[],
            decision_basis="test",
        )
    )

    assert main(
        [
            "execute-revision-retest-next-task",
            "--storage-dir",
            str(tmp_path),
            "--revision-card-id",
            replacement_result.created_artifact_ids[0],
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-30T14:00:00+00:00",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    trial = JsonFileRepository(tmp_path).load_experiment_trials()[0]

    assert payload["executed_task_id"] == "create_revision_retest_scaffold"
    assert payload["before_plan"]["next_task_id"] == "create_revision_retest_scaffold"
    assert payload["after_plan"]["next_task_id"] == "lock_evaluation_protocol"
    assert payload["created_artifact_ids"] == [trial.trial_id]
    assert trial.parameters["revision_retest_kind"] == "lineage_replacement"
