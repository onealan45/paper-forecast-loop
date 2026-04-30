from datetime import UTC, datetime, timedelta
import json

import pytest

from forecast_loop.cli import main
from forecast_loop.lineage_agenda import create_lineage_research_agenda
from forecast_loop.lineage_research_plan import build_lineage_research_task_plan
from forecast_loop.lineage_research_run_log import (
    automation_run_matches_lineage_research_plan,
    record_lineage_research_task_run,
)
from forecast_loop.models import PaperShadowOutcome, ResearchAgenda, ResearchAutopilotRun, StrategyCard
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


def _replacement_card(
    card_id: str,
    *,
    root_card_id: str,
    source_outcome_id: str,
) -> StrategyCard:
    card = _card(card_id, status="DRAFT")
    return StrategyCard(
        card_id=card.card_id,
        created_at=card.created_at,
        strategy_name=f"{card_id} replacement",
        strategy_family=card.strategy_family,
        version=card.version,
        status=card.status,
        symbols=card.symbols,
        hypothesis="Replacement hypothesis should be validated across fresh samples.",
        signal_description=card.signal_description,
        entry_rules=card.entry_rules,
        exit_rules=card.exit_rules,
        risk_rules=card.risk_rules,
        parameters={
            "replacement_source_lineage_root_card_id": root_card_id,
            "replacement_source_outcome_id": source_outcome_id,
            "replacement_failure_attributions": ["drawdown_breach"],
        },
        data_requirements=card.data_requirements,
        feature_snapshot_ids=card.feature_snapshot_ids,
        backtest_result_ids=card.backtest_result_ids,
        walk_forward_validation_ids=card.walk_forward_validation_ids,
        event_edge_evaluation_ids=card.event_edge_evaluation_ids,
        parent_card_id=None,
        author=card.author,
        decision_basis="lineage_replacement_strategy_hypothesis",
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


def _jsonl_snapshot(storage_dir) -> dict[str, str]:
    return {
        path.name: path.read_text(encoding="utf-8")
        for path in storage_dir.glob("*.jsonl")
        if path.is_file()
    }


def _changed_jsonl_files(before: dict[str, str], after: dict[str, str]) -> set[str]:
    names = set(before) | set(after)
    return {name for name in names if before.get(name) != after.get(name)}


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
    assert next_task.required_artifact == "research_agenda"
    assert next_task.blocked_reason is None


def test_lineage_research_task_plan_marks_cross_sample_task_complete_when_agenda_exists(tmp_path):
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
    title = "Cross-sample validation for lineage strategy-card:parent"
    hypothesis = "Validate latest improving lineage on a fresh sample before raising confidence."
    cross_sample_agenda = ResearchAgenda(
        agenda_id=ResearchAgenda.build_id(
            symbol="BTC-USD",
            title=title,
            hypothesis=hypothesis,
            target_strategy_family="lineage_cross_sample_validation",
            strategy_card_ids=[parent.card_id],
        ),
        created_at=now + timedelta(hours=2),
        symbol="BTC-USD",
        title=title,
        hypothesis=hypothesis,
        priority="MEDIUM",
        status="OPEN",
        target_strategy_family="lineage_cross_sample_validation",
        strategy_card_ids=[parent.card_id],
        expected_artifacts=["locked_evaluation", "walk_forward_validation", "paper_shadow_outcome"],
        acceptance_criteria=[
            "latest_lineage_outcome=paper-shadow-outcome:improved",
            "fresh-sample evidence is linked before confidence increases",
        ],
        blocked_actions=["real_order_submission", "automatic_live_execution"],
        decision_basis="lineage_cross_sample_validation_agenda",
    )
    repository.save_research_agenda(cross_sample_agenda)
    repository.save_research_autopilot_run(
        ResearchAutopilotRun(
            run_id="research-autopilot-run:cross-sample-blocked",
            created_at=now + timedelta(hours=3),
            symbol="BTC-USD",
            agenda_id=cross_sample_agenda.agenda_id,
            strategy_card_id=parent.card_id,
            experiment_trial_id="experiment-trial:cross-sample-blocked",
            locked_evaluation_id="locked-evaluation:cross-sample-blocked",
            leaderboard_entry_id="leaderboard-entry:cross-sample-blocked",
            strategy_decision_id=None,
            paper_shadow_outcome_id="paper-shadow-outcome:missing-cross-sample",
            steps=[],
            loop_status="BLOCKED",
            next_research_action="REPAIR_EVIDENCE_CHAIN",
            blocked_reasons=["missing_paper_shadow_outcome"],
            decision_basis="research_paper_autopilot_loop",
        )
    )

    plan = build_lineage_research_task_plan(repository=repository, storage_dir=tmp_path, symbol="BTC-USD")

    task = plan.task_by_id("verify_cross_sample_persistence")
    run_task = plan.task_by_id("record_cross_sample_autopilot_run")
    assert plan.next_task_id == "record_cross_sample_autopilot_run"
    assert task.status == "completed"
    assert task.required_artifact == "research_agenda"
    assert task.artifact_id == cross_sample_agenda.agenda_id
    assert run_task.status == "blocked"
    assert run_task.required_artifact == "research_autopilot_run"
    assert run_task.artifact_id is None
    assert run_task.blocked_reason == "cross_sample_autopilot_run_missing"
    assert run_task.missing_inputs == [
        "locked_evaluation",
        "walk_forward_validation",
        "paper_shadow_outcome",
        "research_autopilot_run",
    ]
    assert cross_sample_agenda.agenda_id in run_task.worker_prompt
    assert parent.card_id in run_task.worker_prompt
    assert "paper-shadow-outcome:improved" in run_task.worker_prompt
    assert "locked_evaluation, walk_forward_validation, paper_shadow_outcome" in run_task.worker_prompt


def test_lineage_research_task_plan_marks_cross_sample_autopilot_task_complete(tmp_path):
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
    title = "Cross-sample validation for lineage strategy-card:parent"
    hypothesis = "Validate latest improving lineage on a fresh sample before raising confidence."
    cross_sample_agenda = ResearchAgenda(
        agenda_id=ResearchAgenda.build_id(
            symbol="BTC-USD",
            title=title,
            hypothesis=hypothesis,
            target_strategy_family="lineage_cross_sample_validation",
            strategy_card_ids=[parent.card_id],
        ),
        created_at=now + timedelta(hours=2),
        symbol="BTC-USD",
        title=title,
        hypothesis=hypothesis,
        priority="MEDIUM",
        status="OPEN",
        target_strategy_family="lineage_cross_sample_validation",
        strategy_card_ids=[parent.card_id],
        expected_artifacts=["locked_evaluation", "walk_forward_validation", "paper_shadow_outcome"],
        acceptance_criteria=[
            "latest_lineage_outcome=paper-shadow-outcome:improved",
            "fresh-sample evidence is linked before confidence increases",
        ],
        blocked_actions=["real_order_submission", "automatic_live_execution"],
        decision_basis="lineage_cross_sample_validation_agenda",
    )
    repository.save_research_agenda(cross_sample_agenda)
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:fresh-sample-pass",
            card_id=parent.card_id,
            created_at=now + timedelta(hours=3),
            action="PROMOTION_READY",
            excess=0.05,
            attributions=[],
        )
    )
    repository.save_research_autopilot_run(
        ResearchAutopilotRun(
            run_id="research-autopilot-run:cross-sample-complete",
            created_at=now + timedelta(hours=4),
            symbol="BTC-USD",
            agenda_id=cross_sample_agenda.agenda_id,
            strategy_card_id=parent.card_id,
            experiment_trial_id="experiment-trial:cross-sample",
            locked_evaluation_id="locked-evaluation:cross-sample",
            leaderboard_entry_id="leaderboard-entry:cross-sample",
            strategy_decision_id=None,
            paper_shadow_outcome_id="paper-shadow-outcome:fresh-sample-pass",
            steps=[],
            loop_status="CROSS_SAMPLE_VALIDATION_COMPLETE",
            next_research_action="COMPARE_FRESH_SAMPLE_EDGE",
            blocked_reasons=[],
            decision_basis="research_paper_autopilot_loop",
        )
    )

    plan = build_lineage_research_task_plan(repository=repository, storage_dir=tmp_path, symbol="BTC-USD")

    task = plan.task_by_id("record_cross_sample_autopilot_run")
    assert plan.next_task_id is None
    assert task.status == "completed"
    assert task.required_artifact == "research_autopilot_run"
    assert task.artifact_id == "research-autopilot-run:cross-sample-complete"


def test_lineage_research_task_plan_does_not_reuse_stale_cross_sample_run_for_newer_outcome(tmp_path):
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
    title = "Cross-sample validation for lineage strategy-card:parent"
    hypothesis = "Validate latest improving lineage on a fresh sample before raising confidence."
    cross_sample_agenda = ResearchAgenda(
        agenda_id=ResearchAgenda.build_id(
            symbol="BTC-USD",
            title=title,
            hypothesis=hypothesis,
            target_strategy_family="lineage_cross_sample_validation",
            strategy_card_ids=[parent.card_id],
        ),
        created_at=now + timedelta(hours=2),
        symbol="BTC-USD",
        title=title,
        hypothesis=hypothesis,
        priority="MEDIUM",
        status="OPEN",
        target_strategy_family="lineage_cross_sample_validation",
        strategy_card_ids=[parent.card_id],
        expected_artifacts=["locked_evaluation", "walk_forward_validation", "paper_shadow_outcome"],
        acceptance_criteria=[
            "latest_lineage_outcome=paper-shadow-outcome:improved",
            "fresh-sample evidence is linked before confidence increases",
        ],
        blocked_actions=["real_order_submission", "automatic_live_execution"],
        decision_basis="lineage_cross_sample_validation_agenda",
    )
    repository.save_research_agenda(cross_sample_agenda)
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:fresh-sample-pass",
            card_id=parent.card_id,
            created_at=now + timedelta(hours=3),
            action="PROMOTION_READY",
            excess=0.05,
            attributions=[],
        )
    )
    repository.save_research_autopilot_run(
        ResearchAutopilotRun(
            run_id="research-autopilot-run:old-cross-sample-complete",
            created_at=now + timedelta(hours=4),
            symbol="BTC-USD",
            agenda_id=cross_sample_agenda.agenda_id,
            strategy_card_id=parent.card_id,
            experiment_trial_id="experiment-trial:old-cross-sample",
            locked_evaluation_id="locked-evaluation:old-cross-sample",
            leaderboard_entry_id="leaderboard-entry:old-cross-sample",
            strategy_decision_id=None,
            paper_shadow_outcome_id="paper-shadow-outcome:fresh-sample-pass",
            steps=[],
            loop_status="CROSS_SAMPLE_VALIDATION_COMPLETE",
            next_research_action="COMPARE_FRESH_SAMPLE_EDGE",
            blocked_reasons=[],
            decision_basis="research_paper_autopilot_loop",
        )
    )
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:newer-improvement",
            card_id=parent.card_id,
            created_at=now + timedelta(hours=5),
            action="CONTINUE_SHADOW",
            excess=0.07,
            attributions=[],
        )
    )

    plan = build_lineage_research_task_plan(repository=repository, storage_dir=tmp_path, symbol="BTC-USD")

    task = plan.task_by_id("verify_cross_sample_persistence")
    assert plan.next_task_id == "verify_cross_sample_persistence"
    assert task.status == "ready"
    assert task.artifact_id is None


def test_lineage_research_task_plan_includes_replacement_context_for_improving_replacement(tmp_path):
    now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    parent = _card("strategy-card:parent")
    revision = _revision_card(
        "strategy-card:revision",
        parent_card_id=parent.card_id,
        source_outcome_id="paper-shadow-outcome:parent-fail",
        failure_attributions=["negative_excess_return"],
    )
    replacement = _replacement_card(
        "strategy-card:replacement",
        root_card_id=parent.card_id,
        source_outcome_id="paper-shadow-outcome:revision-fail",
    )
    repository.save_strategy_card(parent)
    repository.save_strategy_card(revision)
    repository.save_strategy_card(replacement)
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
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:replacement-pass",
            card_id=replacement.card_id,
            created_at=now + timedelta(hours=2),
            action="PROMOTION_READY",
            excess=0.04,
            attributions=[],
        )
    )
    create_lineage_research_agenda(repository=repository, created_at=now, symbol="BTC-USD")

    plan = build_lineage_research_task_plan(repository=repository, storage_dir=tmp_path, symbol="BTC-USD")

    assert plan.latest_outcome_id == "paper-shadow-outcome:replacement-pass"
    assert plan.next_task_id == "verify_cross_sample_persistence"
    next_task = plan.task_by_id("verify_cross_sample_persistence")
    assert "Replacement strategy-card:replacement" in next_task.worker_prompt
    assert "paper-shadow-outcome:replacement-pass" in next_task.worker_prompt
    assert "0.04" in next_task.worker_prompt


def test_lineage_research_task_plan_omits_stale_replacement_context_when_latest_outcome_is_root(tmp_path):
    now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    parent = _card("strategy-card:parent")
    replacement = _replacement_card(
        "strategy-card:replacement",
        root_card_id=parent.card_id,
        source_outcome_id="paper-shadow-outcome:parent-fail",
    )
    repository.save_strategy_card(parent)
    repository.save_strategy_card(replacement)
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:parent-fail",
            card_id=parent.card_id,
            created_at=now,
            action="QUARANTINE_STRATEGY",
            excess=-0.08,
            attributions=["drawdown_breach"],
        )
    )
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:replacement-old-pass",
            card_id=replacement.card_id,
            created_at=now + timedelta(hours=1),
            action="PROMOTION_READY",
            excess=0.01,
            attributions=[],
        )
    )
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:root-latest-pass",
            card_id=parent.card_id,
            created_at=now + timedelta(hours=2),
            action="CONTINUE_SHADOW",
            excess=0.04,
            attributions=[],
        )
    )
    create_lineage_research_agenda(repository=repository, created_at=now, symbol="BTC-USD")

    plan = build_lineage_research_task_plan(repository=repository, storage_dir=tmp_path, symbol="BTC-USD")

    assert plan.latest_outcome_id == "paper-shadow-outcome:root-latest-pass"
    assert plan.next_task_id == "verify_cross_sample_persistence"
    next_task = plan.task_by_id("verify_cross_sample_persistence")
    assert "Replacement strategy-card:replacement" not in next_task.worker_prompt
    assert "replacement-old-pass" not in next_task.worker_prompt
    assert "Latest improvement came from replacement" not in next_task.rationale


def test_lineage_research_task_plan_omits_replacement_context_when_latest_replacement_is_unknown(tmp_path):
    now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    parent = _card("strategy-card:parent")
    replacement = _replacement_card(
        "strategy-card:replacement",
        root_card_id=parent.card_id,
        source_outcome_id="paper-shadow-outcome:parent-fail",
    )
    repository.save_strategy_card(parent)
    repository.save_strategy_card(replacement)
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:parent-baseline",
            card_id=parent.card_id,
            created_at=now,
            action="CONTINUE_SHADOW",
            excess=0.01,
            attributions=[],
        )
    )
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:parent-improved",
            card_id=parent.card_id,
            created_at=now + timedelta(hours=1),
            action="CONTINUE_SHADOW",
            excess=0.04,
            attributions=[],
        )
    )
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:replacement-unknown",
            card_id=replacement.card_id,
            created_at=now + timedelta(hours=2),
            action="CONTINUE_SHADOW",
            excess=None,
            attributions=[],
        )
    )
    create_lineage_research_agenda(repository=repository, created_at=now, symbol="BTC-USD")

    plan = build_lineage_research_task_plan(repository=repository, storage_dir=tmp_path, symbol="BTC-USD")

    assert plan.latest_outcome_id == "paper-shadow-outcome:replacement-unknown"
    assert plan.performance_verdict == "偏強"
    assert plan.next_task_id == "verify_cross_sample_persistence"
    next_task = plan.task_by_id("verify_cross_sample_persistence")
    assert "Replacement strategy-card:replacement" not in next_task.worker_prompt
    assert "replacement-unknown" not in next_task.worker_prompt
    assert "Latest improvement came from replacement" not in next_task.rationale


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


def test_record_lineage_research_task_run_logs_ready_task_plan_without_executing(tmp_path):
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
    before = _jsonl_snapshot(tmp_path)

    result = record_lineage_research_task_run(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 30, 11, 0, tzinfo=UTC),
    )
    after = _jsonl_snapshot(tmp_path)

    run = result.automation_run
    assert run.status == "LINEAGE_RESEARCH_TASK_READY"
    assert run.command == "lineage-research-plan"
    assert run.provider == "research"
    assert run.decision_basis == "lineage_research_task_plan_run_log"
    assert result.task_plan.next_task_id == "propose_strategy_revision"
    assert any(
        step["name"] == "latest_lineage_outcome"
        and step["status"] == "completed"
        and step["artifact_id"] == "paper-shadow-outcome:parent-fail"
        for step in run.steps
    )
    assert any(
        step["name"] == "propose_strategy_revision" and step["status"] == "ready" and step["artifact_id"] is None
        for step in run.steps
    )
    assert automation_run_matches_lineage_research_plan(run, result.task_plan)
    assert _changed_jsonl_files(before, after) == {"automation_runs.jsonl"}
    assert JsonFileRepository(tmp_path).load_automation_runs() == [run]


def test_record_lineage_research_task_run_logs_blocked_evidence_plan(tmp_path):
    now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_strategy_card(_card("strategy-card:parent"))
    create_lineage_research_agenda(repository=repository, created_at=now, symbol="BTC-USD")

    result = record_lineage_research_task_run(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 30, 11, 0, tzinfo=UTC),
    )

    assert result.automation_run.status == "LINEAGE_RESEARCH_TASK_BLOCKED"
    assert result.task_plan.next_task_id == "collect_lineage_shadow_evidence"
    assert result.task_plan.latest_outcome_id is None
    assert not any(step["name"] == "latest_lineage_outcome" for step in result.automation_run.steps)
    assert any(
        step["name"] == "collect_lineage_shadow_evidence"
        and step["status"] == "blocked"
        and step["artifact_id"] is None
        for step in result.automation_run.steps
    )
    assert automation_run_matches_lineage_research_plan(result.automation_run, result.task_plan)


def test_record_lineage_research_task_run_logs_replacement_next_task_context(tmp_path):
    now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    parent = _card("strategy-card:parent")
    revision = _revision_card(
        "strategy-card:revision",
        parent_card_id=parent.card_id,
        source_outcome_id="paper-shadow-outcome:parent-fail",
        failure_attributions=["negative_excess_return"],
    )
    replacement = _replacement_card(
        "strategy-card:replacement",
        root_card_id=parent.card_id,
        source_outcome_id="paper-shadow-outcome:revision-fail",
    )
    repository.save_strategy_card(parent)
    repository.save_strategy_card(revision)
    repository.save_strategy_card(replacement)
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
    repository.save_paper_shadow_outcome(
        _outcome(
            "paper-shadow-outcome:replacement-pass",
            card_id=replacement.card_id,
            created_at=now + timedelta(hours=2),
            action="PROMOTION_READY",
            excess=0.04,
            attributions=[],
        )
    )
    create_lineage_research_agenda(repository=repository, created_at=now, symbol="BTC-USD")

    result = record_lineage_research_task_run(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 30, 11, 0, tzinfo=UTC),
    )
    reloaded = JsonFileRepository(tmp_path).load_automation_runs()[0]

    assert result.task_plan.next_task_id == "verify_cross_sample_persistence"
    assert any(
        step["name"] == "next_task_worker_prompt"
        and step["status"] == "ready"
        and "Replacement strategy-card:replacement" in str(step["artifact_id"])
        and "paper-shadow-outcome:replacement-pass" in str(step["artifact_id"])
        for step in reloaded.steps
    )
    assert any(
        step["name"] == "next_task_required_artifact"
        and step["status"] == "ready"
        and step["artifact_id"] == "research_agenda"
        for step in reloaded.steps
    )
    assert any(
        step["name"] == "next_task_rationale"
        and step["status"] == "ready"
        and "Latest improvement came from replacement strategy-card:replacement" in str(step["artifact_id"])
        for step in reloaded.steps
    )


def test_record_lineage_research_task_run_logs_blocked_next_task_context(tmp_path):
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
    title = "Cross-sample validation for lineage strategy-card:parent"
    hypothesis = "Validate latest improving lineage on a fresh sample before raising confidence."
    cross_sample_agenda = ResearchAgenda(
        agenda_id=ResearchAgenda.build_id(
            symbol="BTC-USD",
            title=title,
            hypothesis=hypothesis,
            target_strategy_family="lineage_cross_sample_validation",
            strategy_card_ids=[parent.card_id],
        ),
        created_at=now + timedelta(hours=2),
        symbol="BTC-USD",
        title=title,
        hypothesis=hypothesis,
        priority="MEDIUM",
        status="OPEN",
        target_strategy_family="lineage_cross_sample_validation",
        strategy_card_ids=[parent.card_id],
        expected_artifacts=["locked_evaluation", "walk_forward_validation", "paper_shadow_outcome"],
        acceptance_criteria=[
            "latest_lineage_outcome=paper-shadow-outcome:improved",
            "fresh-sample evidence is linked before confidence increases",
        ],
        blocked_actions=["real_order_submission", "automatic_live_execution"],
        decision_basis="lineage_cross_sample_validation_agenda",
    )
    repository.save_research_agenda(cross_sample_agenda)

    result = record_lineage_research_task_run(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 30, 13, 0, tzinfo=UTC),
    )
    reloaded = JsonFileRepository(tmp_path).load_automation_runs()[0]

    assert result.task_plan.next_task_id == "record_cross_sample_autopilot_run"
    assert result.automation_run.status == "LINEAGE_RESEARCH_TASK_BLOCKED"
    assert any(
        step["name"] == "next_task_required_artifact"
        and step["status"] == "blocked"
        and step["artifact_id"] == "research_autopilot_run"
        for step in reloaded.steps
    )
    assert any(
        step["name"] == "next_task_blocked_reason"
        and step["status"] == "blocked"
        and step["artifact_id"] == "cross_sample_autopilot_run_missing"
        for step in reloaded.steps
    )
    assert any(
        step["name"] == "next_task_missing_inputs"
        and step["status"] == "blocked"
        and step["artifact_id"] == "locked_evaluation, walk_forward_validation, paper_shadow_outcome, research_autopilot_run"
        for step in reloaded.steps
    )


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


def test_cli_record_lineage_research_task_run_outputs_json_and_persists(tmp_path, capsys):
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

    assert main(
        [
            "record-lineage-research-task-run",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-30T11:00:00+00:00",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["automation_run"]["status"] == "LINEAGE_RESEARCH_TASK_READY"
    assert payload["lineage_research_task_plan"]["next_task_id"] == "propose_strategy_revision"
    assert len(JsonFileRepository(tmp_path).load_automation_runs()) == 1


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
