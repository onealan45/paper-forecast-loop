from datetime import UTC, datetime, timedelta
import json

import pytest

from forecast_loop.autopilot import create_research_agenda, record_research_autopilot_run
from forecast_loop.autopilot import record_revision_retest_autopilot_run
from forecast_loop.cli import main
from forecast_loop.experiment_registry import record_experiment_trial
from forecast_loop.health import run_health_check
from forecast_loop.lineage_agenda import create_lineage_research_agenda
from forecast_loop.lineage_research_executor import execute_lineage_research_next_task
from forecast_loop.models import (
    ExperimentTrial,
    LeaderboardEntry,
    LockedEvaluationResult,
    MarketCandleRecord,
    PaperShadowOutcome,
    ResearchAgenda,
    ResearchAutopilotRun,
    BacktestResult,
    SplitManifest,
    StrategyCard,
    StrategyDecision,
    WalkForwardValidation,
)
from forecast_loop.sqlite_repository import SQLiteRepository, export_sqlite_to_jsonl, migrate_jsonl_to_sqlite
from forecast_loop.storage import JsonFileRepository
from forecast_loop.revision_retest import RETEST_PROTOCOL_VERSION, create_revision_retest_scaffold
from forecast_loop.revision_retest_executor import execute_revision_retest_next_task
from forecast_loop.revision_retest_plan import build_revision_retest_task_plan
from forecast_loop.revision_retest_run_log import record_revision_retest_task_run
from forecast_loop.strategy_evolution import propose_strategy_revision
from forecast_loop.strategy_research import resolve_latest_strategy_research_chain


def _now() -> datetime:
    return datetime(2026, 4, 28, 14, 0, tzinfo=UTC)


def _strategy_card(now: datetime) -> StrategyCard:
    return StrategyCard(
        card_id="strategy-card:autopilot",
        created_at=now,
        strategy_name="BTC autopilot candidate",
        strategy_family="trend_following",
        version="v1",
        status="ACTIVE",
        symbols=["BTC-USD"],
        hypothesis="Autopilot should link this candidate through shadow feedback.",
        signal_description="Use locked leaderboard evidence.",
        entry_rules=["Enter when hard gates pass."],
        exit_rules=["Exit when shadow fails."],
        risk_rules=["Quarantine on shadow failure."],
        parameters={"fast_window": 3, "slow_window": 7},
        data_requirements=["market_candles:BTC-USD:1h"],
        feature_snapshot_ids=[],
        backtest_result_ids=[],
        walk_forward_validation_ids=[],
        event_edge_evaluation_ids=[],
        parent_card_id=None,
        author="codex",
        decision_basis="test",
    )


def _trial(now: datetime, card: StrategyCard) -> ExperimentTrial:
    return ExperimentTrial(
        trial_id="experiment-trial:autopilot",
        created_at=now,
        strategy_card_id=card.card_id,
        trial_index=1,
        status="PASSED",
        symbol="BTC-USD",
        seed=42,
        dataset_id="research-dataset:autopilot",
        backtest_result_id="backtest-result:autopilot",
        walk_forward_validation_id="walk-forward:autopilot",
        event_edge_evaluation_id=None,
        prompt_hash="prompt-hash",
        code_hash="code-hash",
        parameters={"fast_window": 3, "slow_window": 7},
        metric_summary={"excess_return": 0.04},
        failure_reason=None,
        started_at=now,
        completed_at=now,
        decision_basis="test",
    )


def _evaluation(now: datetime, card: StrategyCard, trial: ExperimentTrial, *, rankable: bool = True) -> LockedEvaluationResult:
    return LockedEvaluationResult(
        evaluation_id="locked-evaluation:autopilot",
        created_at=now,
        strategy_card_id=card.card_id,
        trial_id=trial.trial_id,
        split_manifest_id="split-manifest:autopilot",
        cost_model_id="cost-model:autopilot",
        baseline_id="baseline:autopilot",
        backtest_result_id="backtest-result:autopilot",
        walk_forward_validation_id="walk-forward:autopilot",
        event_edge_evaluation_id=None,
        passed=rankable,
        rankable=rankable,
        alpha_score=0.21 if rankable else None,
        blocked_reasons=[] if rankable else ["baseline_edge_not_positive"],
        gate_metrics={"model_edge": 0.11, "holdout_excess_return": 0.05},
        decision_basis="test",
    )


def _leaderboard_entry(
    now: datetime,
    card: StrategyCard,
    trial: ExperimentTrial,
    evaluation: LockedEvaluationResult,
    *,
    rankable: bool = True,
) -> LeaderboardEntry:
    return LeaderboardEntry(
        entry_id="leaderboard-entry:autopilot",
        created_at=now,
        strategy_card_id=card.card_id,
        evaluation_id=evaluation.evaluation_id,
        trial_id=trial.trial_id,
        symbol="BTC-USD",
        rankable=rankable,
        alpha_score=0.21 if rankable else None,
        promotion_stage="CANDIDATE" if rankable else "BLOCKED",
        blocked_reasons=[] if rankable else ["baseline_edge_not_positive"],
        leaderboard_rules_version="pr7-v1",
        decision_basis="test",
    )


def _decision(now: datetime) -> StrategyDecision:
    return StrategyDecision(
        decision_id="decision:autopilot",
        created_at=now,
        symbol="BTC-USD",
        horizon_hours=24,
        action="BUY",
        confidence=0.62,
        evidence_grade="B",
        risk_level="MEDIUM",
        tradeable=True,
        blocked_reason=None,
        recommended_position_pct=0.10,
        current_position_pct=0.0,
        max_position_pct=0.15,
        invalidation_conditions=["Shadow outcome fails."],
        reason_summary="Candidate passed locked gates.",
        forecast_ids=[],
        score_ids=[],
        review_ids=[],
        baseline_ids=[],
        decision_basis="test",
    )


def _shadow_outcome(
    now: datetime,
    entry: LeaderboardEntry,
    *,
    action: str = "PROMOTION_READY",
) -> PaperShadowOutcome:
    return PaperShadowOutcome(
        outcome_id=f"paper-shadow-outcome:{action.lower()}",
        created_at=now,
        leaderboard_entry_id=entry.entry_id,
        evaluation_id=entry.evaluation_id,
        strategy_card_id=entry.strategy_card_id,
        trial_id=entry.trial_id,
        symbol=entry.symbol,
        window_start=now,
        window_end=now + timedelta(hours=24),
        observed_return=0.05 if action == "PROMOTION_READY" else -0.02,
        benchmark_return=0.01,
        excess_return_after_costs=0.04 if action == "PROMOTION_READY" else -0.03,
        max_adverse_excursion=0.02,
        turnover=1.0,
        outcome_grade="PASS" if action == "PROMOTION_READY" else "FAIL",
        failure_attributions=[] if action == "PROMOTION_READY" else ["negative_excess_return"],
        recommended_promotion_stage="PAPER_SHADOW_PASSED" if action == "PROMOTION_READY" else "PAPER_SHADOW_FAILED",
        recommended_strategy_action=action,
        blocked_reasons=[],
        notes=[],
        decision_basis="test",
    )


def _seed_repository(tmp_path, *, rankable: bool = True, shadow_action: str = "PROMOTION_READY"):
    now = _now()
    repository = JsonFileRepository(tmp_path)
    card = _strategy_card(now)
    trial = _trial(now, card)
    evaluation = _evaluation(now, card, trial, rankable=rankable)
    entry = _leaderboard_entry(now, card, trial, evaluation, rankable=rankable)
    decision = _decision(now)
    outcome = _shadow_outcome(now, entry, action=shadow_action)
    repository.save_strategy_card(card)
    repository.save_experiment_trial(trial)
    repository.save_locked_evaluation_result(evaluation)
    repository.save_leaderboard_entry(entry)
    repository.save_strategy_decision(decision)
    repository.save_paper_shadow_outcome(outcome)
    return repository, card, trial, evaluation, entry, decision, outcome


def _jsonl_snapshot(tmp_path):
    return {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(tmp_path.glob("*.jsonl"))
    }


def _changed_jsonl_files(before: dict[str, str], after: dict[str, str]) -> set[str]:
    return {
        name
        for name in set(before) | set(after)
        if before.get(name) != after.get(name)
    }


def _retest_candle(index: int, close: float) -> MarketCandleRecord:
    timestamp = datetime(2026, 3, 2, tzinfo=UTC) + timedelta(days=index)
    return MarketCandleRecord(
        candle_id=f"market-candle:retest:{index}",
        symbol="BTC-USD",
        timestamp=timestamp,
        open=close - 1,
        high=close + 1,
        low=close - 2,
        close=close,
        volume=1000 + index,
        source="revision-retest-fixture",
        imported_at=datetime(2026, 4, 29, tzinfo=UTC),
    )


def _seed_retest_candles(repository: JsonFileRepository) -> None:
    for index, close in enumerate([100, 102, 104, 101, 103, 106]):
        repository.save_market_candle(_retest_candle(index, close))


def _retest_full_window_candle(index: int, close: float) -> MarketCandleRecord:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index)
    return MarketCandleRecord(
        candle_id=f"market-candle:retest-full:{index}",
        symbol="BTC-USD",
        timestamp=timestamp,
        open=close - 1,
        high=close + 1,
        low=close - 2,
        close=close,
        volume=2000 + index,
        source="revision-retest-full-window-fixture",
        imported_at=datetime(2026, 4, 29, tzinfo=UTC),
    )


def _seed_retest_full_window_candles(repository: JsonFileRepository) -> None:
    for index, close in enumerate([100, 101, 103, 102, 104, 107, 105, 108, 110, 109]):
        repository.save_market_candle(_retest_full_window_candle(index, close))


def test_json_repository_round_trips_research_autopilot_artifacts(tmp_path):
    repository, card, _trial, _evaluation, _entry, _decision, _outcome = _seed_repository(tmp_path)
    agenda = ResearchAgenda(
        agenda_id="research-agenda:roundtrip",
        created_at=_now(),
        symbol="BTC-USD",
        title="Autopilot trend candidate",
        hypothesis="Trend continuation should survive shadow validation.",
        priority="HIGH",
        status="OPEN",
        target_strategy_family="trend_following",
        strategy_card_ids=[card.card_id],
        expected_artifacts=["strategy_card", "locked_evaluation", "paper_shadow_outcome"],
        acceptance_criteria=["All hard gates pass."],
        blocked_actions=["real_order_submission"],
        decision_basis="test",
    )
    run = ResearchAutopilotRun(
        run_id="research-autopilot-run:roundtrip",
        created_at=_now(),
        symbol="BTC-USD",
        agenda_id=agenda.agenda_id,
        strategy_card_id=card.card_id,
        experiment_trial_id="experiment-trial:autopilot",
        locked_evaluation_id="locked-evaluation:autopilot",
        leaderboard_entry_id="leaderboard-entry:autopilot",
        strategy_decision_id="decision:autopilot",
        paper_shadow_outcome_id="paper-shadow-outcome:promotion_ready",
        steps=[{"name": "agenda", "status": "completed", "artifact_id": agenda.agenda_id}],
        loop_status="READY_FOR_OPERATOR_REVIEW",
        next_research_action="OPERATOR_REVIEW_FOR_PROMOTION",
        blocked_reasons=[],
        decision_basis="test",
    )

    repository.save_research_agenda(agenda)
    repository.save_research_autopilot_run(run)
    repository.save_research_agenda(agenda)
    repository.save_research_autopilot_run(run)

    assert repository.load_research_agendas() == [agenda]
    assert repository.load_research_autopilot_runs() == [run]


def test_research_autopilot_promotion_ready_outcome(tmp_path):
    repository, card, trial, evaluation, entry, decision, outcome = _seed_repository(tmp_path)
    agenda = create_research_agenda(
        repository=repository,
        created_at=_now(),
        symbol="BTC-USD",
        title="Autopilot trend candidate",
        hypothesis="Trend continuation should survive shadow validation.",
        strategy_family="trend_following",
        strategy_card_ids=[card.card_id],
    )

    run = record_research_autopilot_run(
        repository=repository,
        created_at=_now(),
        agenda_id=agenda.agenda_id,
        strategy_card_id=card.card_id,
        experiment_trial_id=trial.trial_id,
        locked_evaluation_id=evaluation.evaluation_id,
        leaderboard_entry_id=entry.entry_id,
        strategy_decision_id=decision.decision_id,
        paper_shadow_outcome_id=outcome.outcome_id,
    )

    assert run.loop_status == "READY_FOR_OPERATOR_REVIEW"
    assert run.next_research_action == "OPERATOR_REVIEW_FOR_PROMOTION"
    assert run.blocked_reasons == []
    assert [step["name"] for step in run.steps] == [
        "agenda",
        "strategy_card",
        "experiment_trial",
        "locked_evaluation",
        "leaderboard",
        "paper_decision",
        "paper_shadow_outcome",
        "next_research_action",
    ]


def test_research_autopilot_blocks_unrankable_chain(tmp_path):
    repository, card, trial, evaluation, entry, decision, outcome = _seed_repository(tmp_path, rankable=False)
    agenda = create_research_agenda(
        repository=repository,
        created_at=_now(),
        symbol="BTC-USD",
        title="Blocked candidate",
        hypothesis="Blocked candidate must not proceed.",
        strategy_family="trend_following",
        strategy_card_ids=[card.card_id],
    )

    run = record_research_autopilot_run(
        repository=repository,
        created_at=_now(),
        agenda_id=agenda.agenda_id,
        strategy_card_id=card.card_id,
        experiment_trial_id=trial.trial_id,
        locked_evaluation_id=evaluation.evaluation_id,
        leaderboard_entry_id=entry.entry_id,
        strategy_decision_id=decision.decision_id,
        paper_shadow_outcome_id=outcome.outcome_id,
    )

    assert run.loop_status == "BLOCKED"
    assert run.next_research_action == "REPAIR_EVIDENCE_CHAIN"
    assert "locked_evaluation_not_rankable" in run.blocked_reasons
    assert "leaderboard_entry_not_rankable" in run.blocked_reasons


def test_research_autopilot_blocks_mismatched_evidence_chain(tmp_path):
    repository, card, trial, evaluation, entry, decision, outcome = _seed_repository(tmp_path)
    other_card = _strategy_card(_now())
    other_card.card_id = "strategy-card:other"
    other_trial = _trial(_now(), other_card)
    other_trial.trial_id = "experiment-trial:other"
    other_trial.strategy_card_id = other_card.card_id
    other_evaluation = _evaluation(_now(), other_card, other_trial)
    other_evaluation.evaluation_id = "locked-evaluation:other"
    other_evaluation.strategy_card_id = other_card.card_id
    other_evaluation.trial_id = other_trial.trial_id
    other_entry = _leaderboard_entry(_now(), other_card, other_trial, other_evaluation)
    other_entry.entry_id = "leaderboard-entry:other"
    other_entry.strategy_card_id = other_card.card_id
    other_entry.trial_id = other_trial.trial_id
    other_entry.evaluation_id = other_evaluation.evaluation_id
    repository.save_strategy_card(other_card)
    repository.save_experiment_trial(other_trial)
    repository.save_locked_evaluation_result(other_evaluation)
    repository.save_leaderboard_entry(other_entry)
    agenda = create_research_agenda(
        repository=repository,
        created_at=_now(),
        symbol="BTC-USD",
        title="Mixed chain candidate",
        hypothesis="Mixed evidence must not pass.",
        strategy_family="trend_following",
        strategy_card_ids=[card.card_id],
    )

    run = record_research_autopilot_run(
        repository=repository,
        created_at=_now(),
        agenda_id=agenda.agenda_id,
        strategy_card_id=card.card_id,
        experiment_trial_id=trial.trial_id,
        locked_evaluation_id=other_evaluation.evaluation_id,
        leaderboard_entry_id=other_entry.entry_id,
        strategy_decision_id=decision.decision_id,
        paper_shadow_outcome_id=outcome.outcome_id,
    )

    assert run.loop_status == "BLOCKED"
    assert run.next_research_action == "REPAIR_EVIDENCE_CHAIN"
    assert "locked_evaluation_strategy_card_mismatch" in run.blocked_reasons
    assert "locked_evaluation_trial_mismatch" in run.blocked_reasons
    assert "leaderboard_entry_strategy_card_mismatch" in run.blocked_reasons
    assert "leaderboard_entry_trial_mismatch" in run.blocked_reasons
    assert "paper_shadow_outcome_leaderboard_mismatch" in run.blocked_reasons


def test_research_autopilot_requires_paper_decision_for_ready_state(tmp_path):
    repository, card, trial, evaluation, entry, _decision, outcome = _seed_repository(tmp_path)
    agenda = create_research_agenda(
        repository=repository,
        created_at=_now(),
        symbol="BTC-USD",
        title="Missing decision candidate",
        hypothesis="Promotion needs paper decision evidence.",
        strategy_family="trend_following",
        strategy_card_ids=[card.card_id],
    )

    run = record_research_autopilot_run(
        repository=repository,
        created_at=_now(),
        agenda_id=agenda.agenda_id,
        strategy_card_id=card.card_id,
        experiment_trial_id=trial.trial_id,
        locked_evaluation_id=evaluation.evaluation_id,
        leaderboard_entry_id=entry.entry_id,
        strategy_decision_id=None,
        paper_shadow_outcome_id=outcome.outcome_id,
    )

    assert run.loop_status == "BLOCKED"
    assert run.next_research_action == "REPAIR_EVIDENCE_CHAIN"
    assert "strategy_decision_missing" in run.blocked_reasons


def test_research_autopilot_blocks_bad_paper_decision_state(tmp_path):
    repository, card, trial, evaluation, entry, decision, outcome = _seed_repository(tmp_path)
    decision.symbol = "ETH-USD"
    decision.action = "STOP_NEW_ENTRIES"
    decision.tradeable = False
    decision.blocked_reason = "health_check_repair_required"
    (tmp_path / "strategy_decisions.jsonl").write_text(
        json.dumps(decision.to_dict()) + "\n",
        encoding="utf-8",
    )
    agenda = create_research_agenda(
        repository=repository,
        created_at=_now(),
        symbol="BTC-USD",
        title="Blocked decision candidate",
        hypothesis="Blocked or wrong-symbol decisions must not promote.",
        strategy_family="trend_following",
        strategy_card_ids=[card.card_id],
    )

    run = record_research_autopilot_run(
        repository=repository,
        created_at=_now(),
        agenda_id=agenda.agenda_id,
        strategy_card_id=card.card_id,
        experiment_trial_id=trial.trial_id,
        locked_evaluation_id=evaluation.evaluation_id,
        leaderboard_entry_id=entry.entry_id,
        strategy_decision_id=decision.decision_id,
        paper_shadow_outcome_id=outcome.outcome_id,
    )

    assert run.loop_status == "BLOCKED"
    assert run.next_research_action == "REPAIR_EVIDENCE_CHAIN"
    assert "strategy_decision_symbol_mismatch" in run.blocked_reasons
    assert "strategy_decision_not_tradeable" in run.blocked_reasons
    assert "strategy_decision_fail_closed_action" in run.blocked_reasons
    assert "strategy_decision_blocked" in run.blocked_reasons


def test_research_autopilot_retire_outcome_requires_revision(tmp_path):
    repository, card, trial, evaluation, entry, decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    agenda = create_research_agenda(
        repository=repository,
        created_at=_now(),
        symbol="BTC-USD",
        title="Retire candidate",
        hypothesis="Retired candidates should create revision work.",
        strategy_family="trend_following",
        strategy_card_ids=[card.card_id],
    )

    run = record_research_autopilot_run(
        repository=repository,
        created_at=_now(),
        agenda_id=agenda.agenda_id,
        strategy_card_id=card.card_id,
        experiment_trial_id=trial.trial_id,
        locked_evaluation_id=evaluation.evaluation_id,
        leaderboard_entry_id=entry.entry_id,
        strategy_decision_id=decision.decision_id,
        paper_shadow_outcome_id=outcome.outcome_id,
    )

    assert run.loop_status == "REVISION_REQUIRED"
    assert run.next_research_action == "CREATE_REVISION_AGENDA"
    assert "negative_excess_return" in run.blocked_reasons


def test_propose_strategy_revision_creates_draft_child_card_and_agenda(tmp_path):
    repository, card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    outcome.failure_attributions = ["negative_excess_return", "turnover_breach"]
    (tmp_path / "paper_shadow_outcomes.jsonl").write_text(
        json.dumps(outcome.to_dict()) + "\n",
        encoding="utf-8",
    )

    result = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    )

    revision = result.strategy_card
    agenda = result.research_agenda
    assert revision.status == "DRAFT"
    assert revision.parent_card_id == card.card_id
    assert revision.author == "codex-strategy-evolution"
    assert revision.decision_basis == "paper_shadow_strategy_revision_candidate"
    assert revision.parameters["revision_source_outcome_id"] == outcome.outcome_id
    assert revision.parameters["revision_failure_attributions"] == [
        "negative_excess_return",
        "turnover_breach",
    ]
    assert revision.backtest_result_ids == []
    assert revision.walk_forward_validation_ids == []
    assert any("positive after-cost edge" in rule for rule in revision.entry_rules)
    assert any("cooldown" in rule for rule in revision.risk_rules)
    assert agenda.strategy_card_ids == [revision.card_id]
    assert "revision" in agenda.title.lower()
    assert "negative_excess_return" in agenda.hypothesis
    assert "paper_shadow_outcome" in agenda.expected_artifacts


def test_propose_strategy_revision_rejects_promotion_ready_outcome(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(tmp_path)

    try:
        propose_strategy_revision(
            repository=repository,
            created_at=_now(),
            paper_shadow_outcome_id=outcome.outcome_id,
        )
    except ValueError as exc:
        assert "does not require revision" in str(exc)
    else:
        raise AssertionError("promotion-ready outcome should not create a revision")


def test_propose_strategy_revision_is_idempotent(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )

    first = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    )
    second = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    )

    assert second.strategy_card.card_id == first.strategy_card.card_id
    assert second.research_agenda.agenda_id == first.research_agenda.agenda_id
    assert len(repository.load_strategy_cards()) == 2
    assert len(repository.load_research_agendas()) == 1


def test_propose_strategy_revision_ignores_later_revision_version_for_same_outcome(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )

    first = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    )
    second = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
        revision_version="manual-v2",
    )

    assert second.strategy_card.card_id == first.strategy_card.card_id
    assert second.strategy_card.version == first.strategy_card.version
    assert second.research_agenda.agenda_id == first.research_agenda.agenda_id
    assert len(repository.load_strategy_cards()) == 2
    assert len(repository.load_research_agendas()) == 1


def test_cli_propose_strategy_revision_outputs_revision_and_persists(tmp_path, capsys):
    _repository, card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )

    assert main(
        [
            "propose-strategy-revision",
            "--storage-dir",
            str(tmp_path),
            "--paper-shadow-outcome-id",
            outcome.outcome_id,
            "--created-at",
            "2026-04-28T14:00:00+00:00",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    revision = payload["revision_strategy_card"]
    agenda = payload["revision_research_agenda"]
    assert revision["card_id"].startswith("strategy-card:")
    assert revision["parent_card_id"] == card.card_id
    assert agenda["agenda_id"].startswith("research-agenda:")
    assert agenda["strategy_card_ids"] == [revision["card_id"]]


def test_create_revision_retest_scaffold_creates_pending_trial(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card

    scaffold = create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
    )

    trial = scaffold.experiment_trial
    assert trial.status == "PENDING"
    assert trial.strategy_card_id == revision.card_id
    assert trial.symbol == "BTC-USD"
    assert trial.dataset_id == "research-dataset:revision-retest"
    assert trial.backtest_result_id is None
    assert trial.walk_forward_validation_id is None
    assert trial.parameters["revision_retest_source_card_id"] == revision.card_id
    assert trial.parameters["revision_source_outcome_id"] == outcome.outcome_id
    assert "backtest_result" in scaffold.next_required_artifacts
    assert not [
        budget
        for budget in repository.load_experiment_budgets()
        if budget.strategy_card_id == revision.card_id
    ]
    assert not [
        result
        for result in repository.load_locked_evaluation_results()
        if result.strategy_card_id == revision.card_id
    ]


def test_create_revision_retest_scaffold_is_idempotent(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card

    first = create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
    )
    second = create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=99,
    )

    assert second.experiment_trial.trial_id == first.experiment_trial.trial_id
    assert len([trial for trial in repository.load_experiment_trials() if trial.strategy_card_id == revision.card_id]) == 1


def test_create_revision_retest_scaffold_returns_persisted_split_and_cost_on_rerun(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card

    first = create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 2, 1, tzinfo=UTC),
        validation_start=datetime(2026, 2, 2, tzinfo=UTC),
        validation_end=datetime(2026, 3, 1, tzinfo=UTC),
        holdout_start=datetime(2026, 3, 2, tzinfo=UTC),
        holdout_end=datetime(2026, 4, 1, tzinfo=UTC),
    )
    second = create_revision_retest_scaffold(
        repository=repository,
        created_at=_now() + timedelta(hours=1),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 2, 1, tzinfo=UTC),
        validation_start=datetime(2026, 2, 2, tzinfo=UTC),
        validation_end=datetime(2026, 3, 1, tzinfo=UTC),
        holdout_start=datetime(2026, 3, 2, tzinfo=UTC),
        holdout_end=datetime(2026, 4, 1, tzinfo=UTC),
    )

    assert first.split_manifest is not None
    assert second.split_manifest is not None
    assert first.cost_model_snapshot is not None
    assert second.cost_model_snapshot is not None
    assert second.split_manifest.manifest_id == first.split_manifest.manifest_id
    assert second.split_manifest.created_at == first.split_manifest.created_at
    assert second.cost_model_snapshot.cost_model_id == first.cost_model_snapshot.cost_model_id
    assert second.cost_model_snapshot.created_at == first.cost_model_snapshot.created_at


def test_create_revision_retest_scaffold_rejects_non_revision_card(tmp_path):
    repository, card, _trial, _evaluation, _entry, _decision, _outcome = _seed_repository(tmp_path)

    try:
        create_revision_retest_scaffold(
            repository=repository,
            created_at=_now(),
            revision_card_id=card.card_id,
            symbol="BTC-USD",
            dataset_id="research-dataset:revision-retest",
            max_trials=20,
        )
    except ValueError as exc:
        assert "not a DRAFT strategy revision card" in str(exc)
    else:
        raise AssertionError("non-revision cards must not create retest scaffolds")


def test_create_revision_retest_scaffold_rejects_revision_without_parent(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    bogus = StrategyCard.from_dict(
        {
            **revision.to_dict(),
            "card_id": "strategy-card:revision-without-parent",
            "parent_card_id": None,
        }
    )
    repository.save_strategy_card(bogus)

    try:
        create_revision_retest_scaffold(
            repository=repository,
            created_at=_now(),
            revision_card_id=bogus.card_id,
            symbol="BTC-USD",
            dataset_id="research-dataset:revision-retest",
            max_trials=20,
        )
    except ValueError as exc:
        assert "not a DRAFT strategy revision card" in str(exc)
    else:
        raise AssertionError("revision-like cards without parent must not create retest scaffolds")


def test_create_revision_retest_scaffold_rejects_parent_source_mismatch(tmp_path):
    repository, card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    bogus = StrategyCard.from_dict(
        {
            **revision.to_dict(),
            "card_id": "strategy-card:revision-parent-mismatch",
            "parent_card_id": "strategy-card:wrong-parent",
        }
    )
    repository.save_strategy_card(bogus)

    try:
        create_revision_retest_scaffold(
            repository=repository,
            created_at=_now(),
            revision_card_id=bogus.card_id,
            symbol="BTC-USD",
            dataset_id="research-dataset:revision-retest",
            max_trials=20,
        )
    except ValueError as exc:
        assert "does not match revision parent" in str(exc)
    else:
        raise AssertionError("revision parent must match the source outcome strategy card")
    assert card.card_id == outcome.strategy_card_id


def test_create_revision_retest_scaffold_locks_protocol_without_evaluation_result(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card

    scaffold = create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 2, 1, tzinfo=UTC),
        validation_start=datetime(2026, 2, 2, tzinfo=UTC),
        validation_end=datetime(2026, 3, 1, tzinfo=UTC),
        holdout_start=datetime(2026, 3, 2, tzinfo=UTC),
        holdout_end=datetime(2026, 4, 1, tzinfo=UTC),
    )

    assert scaffold.split_manifest is not None
    assert scaffold.cost_model_snapshot is not None
    assert scaffold.split_manifest.strategy_card_id == revision.card_id
    assert scaffold.split_manifest.status == "LOCKED"
    assert scaffold.cost_model_snapshot.status == "LOCKED"
    assert not [
        result
        for result in repository.load_locked_evaluation_results()
        if result.strategy_card_id == revision.card_id
    ]


def test_cli_create_revision_retest_scaffold_outputs_json_and_persists(tmp_path, capsys):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card

    assert main(
        [
            "create-revision-retest-scaffold",
            "--storage-dir",
            str(tmp_path),
            "--revision-card-id",
            revision.card_id,
            "--symbol",
            "BTC-USD",
            "--dataset-id",
            "research-dataset:revision-retest",
            "--max-trials",
            "20",
            "--seed",
            "7",
            "--created-at",
            "2026-04-28T14:00:00+00:00",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["revision_retest_scaffold"]["strategy_card_id"] == revision.card_id
    assert payload["revision_retest_scaffold"]["source_outcome_id"] == outcome.outcome_id
    assert payload["revision_retest_scaffold"]["experiment_trial"]["status"] == "PENDING"
    assert payload["revision_retest_scaffold"]["split_manifest"] is None
    assert len([trial for trial in repository.load_experiment_trials() if trial.strategy_card_id == revision.card_id]) == 1


def test_revision_retest_task_plan_is_read_only_and_blocks_missing_split_inputs(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    scaffold = create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
    )
    before_files = _jsonl_snapshot(tmp_path)

    plan = build_revision_retest_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        revision_card_id=revision.card_id,
    )
    after_files = _jsonl_snapshot(tmp_path)

    assert plan.strategy_card_id == revision.card_id
    assert plan.source_outcome_id == outcome.outcome_id
    assert plan.pending_trial_id == scaffold.experiment_trial.trial_id
    assert plan.next_task_id == "lock_evaluation_protocol"
    assert plan.task_by_id("create_revision_retest_scaffold").status == "completed"
    lock_task = plan.task_by_id("lock_evaluation_protocol")
    assert lock_task.status == "blocked"
    assert lock_task.command_args is None
    assert lock_task.blocked_reason == "split_window_inputs_required"
    assert "train_start" in lock_task.missing_inputs
    assert before_files == after_files


def test_revision_retest_task_plan_emits_backtest_and_walk_forward_commands_after_split_lock(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    scaffold = create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 2, 1, tzinfo=UTC),
        validation_start=datetime(2026, 2, 2, tzinfo=UTC),
        validation_end=datetime(2026, 3, 1, tzinfo=UTC),
        holdout_start=datetime(2026, 3, 2, tzinfo=UTC),
        holdout_end=datetime(2026, 4, 1, tzinfo=UTC),
    )

    plan = build_revision_retest_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        revision_card_id=revision.card_id,
    )

    assert scaffold.split_manifest is not None
    assert scaffold.cost_model_snapshot is not None
    assert plan.split_manifest_id == scaffold.split_manifest.manifest_id
    assert plan.cost_model_id == scaffold.cost_model_snapshot.cost_model_id
    assert plan.task_by_id("lock_evaluation_protocol").status == "completed"
    backtest_task = plan.task_by_id("run_backtest")
    assert backtest_task.status == "ready"
    assert "--start" in backtest_task.command_args
    assert "2026-03-02T00:00:00+00:00" in backtest_task.command_args
    assert "--end" in backtest_task.command_args
    assert "2026-04-01T00:00:00+00:00" in backtest_task.command_args
    walk_forward_task = plan.task_by_id("run_walk_forward")
    assert walk_forward_task.status == "ready"
    assert "2026-01-01T00:00:00+00:00" in walk_forward_task.command_args
    assert "2026-04-01T00:00:00+00:00" in walk_forward_task.command_args
    gate_task = plan.task_by_id("evaluate_leaderboard_gate")
    assert gate_task.status == "blocked"
    assert gate_task.blocked_reason == "missing_locked_evaluation_inputs"


def test_cli_revision_retest_plan_outputs_json(tmp_path, capsys):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
    )

    assert main(
        [
            "revision-retest-plan",
            "--storage-dir",
            str(tmp_path),
            "--revision-card-id",
            revision.card_id,
            "--symbol",
            "BTC-USD",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    plan = payload["revision_retest_task_plan"]
    assert plan["strategy_card_id"] == revision.card_id
    assert plan["source_outcome_id"] == outcome.outcome_id
    assert plan["next_task_id"] == "lock_evaluation_protocol"
    assert [task["task_id"] for task in plan["tasks"]][0] == "create_revision_retest_scaffold"


def test_revision_retest_task_plan_does_not_complete_malformed_passed_trial(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    pending = create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
    ).experiment_trial
    malformed_passed = ExperimentTrial.from_dict(
        {
            **pending.to_dict(),
            "trial_id": "experiment-trial:malformed-passed-retest",
            "status": "PASSED",
            "backtest_result_id": None,
            "walk_forward_validation_id": None,
            "completed_at": _now().isoformat(),
        }
    )
    repository.save_experiment_trial(malformed_passed)

    plan = build_revision_retest_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        revision_card_id=revision.card_id,
    )

    assert plan.passed_trial_id is None
    passed_trial_task = plan.task_by_id("record_passed_retest_trial")
    assert passed_trial_task.status == "blocked"
    assert "backtest_result" in passed_trial_task.missing_inputs
    assert "walk_forward_validation" in passed_trial_task.missing_inputs


def test_revision_retest_task_plan_rejects_passed_trial_linked_to_wrong_split(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    pending = create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 1, 4, tzinfo=UTC),
        validation_start=datetime(2026, 1, 5, tzinfo=UTC),
        validation_end=datetime(2026, 1, 7, tzinfo=UTC),
        holdout_start=datetime(2026, 1, 8, tzinfo=UTC),
        holdout_end=datetime(2026, 1, 10, tzinfo=UTC),
    ).experiment_trial
    wrong_backtest = BacktestResult(
        result_id="backtest-result:wrong-window",
        backtest_id="backtest:wrong-window",
        created_at=_now(),
        symbol="BTC-USD",
        start=datetime(2025, 10, 1, tzinfo=UTC),
        end=datetime(2025, 11, 1, tzinfo=UTC),
        initial_cash=10_000.0,
        final_equity=10_500.0,
        strategy_return=0.05,
        benchmark_return=0.01,
        max_drawdown=0.02,
        sharpe=1.2,
        turnover=1.0,
        win_rate=0.6,
        trade_count=3,
        equity_curve=[],
        decision_basis="test-wrong-window",
    )
    wrong_walk_forward = WalkForwardValidation(
        validation_id="walk-forward:wrong-window",
        created_at=_now(),
        symbol="BTC-USD",
        start=datetime(2025, 8, 1, tzinfo=UTC),
        end=datetime(2025, 11, 1, tzinfo=UTC),
        strategy_name="moving_average_trend",
        train_size=4,
        validation_size=3,
        test_size=3,
        step_size=1,
        initial_cash=10_000.0,
        fee_bps=5.0,
        slippage_bps=10.0,
        moving_average_window=3,
        window_count=1,
        average_validation_return=0.03,
        average_test_return=0.04,
        average_benchmark_return=0.01,
        average_excess_return=0.03,
        test_win_rate=1.0,
        overfit_window_count=0,
        overfit_risk_flags=[],
        backtest_result_ids=[wrong_backtest.result_id],
        windows=[],
        decision_basis="test-wrong-window",
    )
    repository.save_backtest_result(wrong_backtest)
    repository.save_walk_forward_validation(wrong_walk_forward)
    malformed_passed = ExperimentTrial.from_dict(
        {
            **pending.to_dict(),
            "trial_id": "experiment-trial:wrong-split-passed-retest",
            "status": "PASSED",
            "backtest_result_id": wrong_backtest.result_id,
            "walk_forward_validation_id": wrong_walk_forward.validation_id,
            "completed_at": _now().isoformat(),
        }
    )
    repository.save_experiment_trial(malformed_passed)

    plan = build_revision_retest_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        revision_card_id=revision.card_id,
    )

    assert plan.passed_trial_id is None
    assert plan.task_by_id("run_backtest").status == "ready"
    assert plan.task_by_id("run_walk_forward").status == "ready"
    assert plan.task_by_id("record_passed_retest_trial").status == "blocked"


def test_revision_retest_task_plan_does_not_record_passed_trial_from_unlinked_evidence(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 1, 4, tzinfo=UTC),
        validation_start=datetime(2026, 1, 5, tzinfo=UTC),
        validation_end=datetime(2026, 1, 7, tzinfo=UTC),
        holdout_start=datetime(2026, 1, 8, tzinfo=UTC),
        holdout_end=datetime(2026, 1, 10, tzinfo=UTC),
    )
    backtest = BacktestResult(
        result_id="backtest-result:split-aligned",
        backtest_id="backtest:split-aligned",
        created_at=_now(),
        symbol="BTC-USD",
        start=datetime(2026, 1, 8, tzinfo=UTC),
        end=datetime(2026, 1, 10, tzinfo=UTC),
        initial_cash=10_000.0,
        final_equity=10_500.0,
        strategy_return=0.05,
        benchmark_return=0.01,
        max_drawdown=0.02,
        sharpe=1.2,
        turnover=1.0,
        win_rate=0.6,
        trade_count=3,
        equity_curve=[],
        decision_basis="test-split-aligned",
    )
    unlinked_walk_forward = WalkForwardValidation(
        validation_id="walk-forward:split-aligned-unlinked",
        created_at=_now(),
        symbol="BTC-USD",
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 1, 10, tzinfo=UTC),
        strategy_name="moving_average_trend",
        train_size=4,
        validation_size=3,
        test_size=3,
        step_size=1,
        initial_cash=10_000.0,
        fee_bps=5.0,
        slippage_bps=10.0,
        moving_average_window=3,
        window_count=1,
        average_validation_return=0.03,
        average_test_return=0.04,
        average_benchmark_return=0.01,
        average_excess_return=0.03,
        test_win_rate=1.0,
        overfit_window_count=0,
        overfit_risk_flags=[],
        backtest_result_ids=["backtest-result:different-holdout"],
        windows=[],
        decision_basis="test-split-aligned-unlinked",
    )
    repository.save_backtest_result(backtest)
    repository.save_walk_forward_validation(unlinked_walk_forward)

    plan = build_revision_retest_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        revision_card_id=revision.card_id,
    )

    passed_trial_task = plan.task_by_id("record_passed_retest_trial")
    assert passed_trial_task.status == "blocked"
    assert passed_trial_task.blocked_reason == "missing_retest_results"
    assert "linked_backtest_walk_forward_pair" in passed_trial_task.missing_inputs


def test_cli_revision_retest_plan_rejects_missing_storage_without_creating_directory(tmp_path, capsys):
    missing_storage = tmp_path / "typo-storage"

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "revision-retest-plan",
                "--storage-dir",
                str(missing_storage),
                "--symbol",
                "BTC-USD",
            ]
        )

    assert exc_info.value.code == 2
    assert not missing_storage.exists()
    assert "storage directory does not exist" in capsys.readouterr().err


def test_record_revision_retest_task_run_logs_blocked_task_plan(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
    )

    result = record_revision_retest_task_run(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 9, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )

    run = result.automation_run
    assert run.status == "RETEST_TASK_BLOCKED"
    assert run.command == "revision-retest-plan"
    assert run.provider == "research"
    assert result.task_plan.next_task_id == "lock_evaluation_protocol"
    assert any(
        step["name"] == "lock_evaluation_protocol" and step["status"] == "blocked"
        for step in run.steps
    )
    assert JsonFileRepository(tmp_path).load_automation_runs() == [run]


def test_record_revision_retest_task_run_writes_only_automation_log_for_ready_plan(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 2, 1, tzinfo=UTC),
        validation_start=datetime(2026, 2, 2, tzinfo=UTC),
        validation_end=datetime(2026, 3, 1, tzinfo=UTC),
        holdout_start=datetime(2026, 3, 2, tzinfo=UTC),
        holdout_end=datetime(2026, 4, 1, tzinfo=UTC),
    )
    before = _jsonl_snapshot(tmp_path)

    result = record_revision_retest_task_run(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 9, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    after = _jsonl_snapshot(tmp_path)

    assert result.automation_run.status == "RETEST_TASK_READY"
    assert result.task_plan.next_task_id == "generate_baseline_evaluation"
    assert _changed_jsonl_files(before, after) == {"automation_runs.jsonl"}


def test_cli_record_revision_retest_task_run_outputs_json_and_persists(tmp_path, capsys):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
    )

    assert main(
        [
            "record-revision-retest-task-run",
            "--storage-dir",
            str(tmp_path),
            "--revision-card-id",
            revision.card_id,
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-29T09:30:00+00:00",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["automation_run"]["status"] == "RETEST_TASK_BLOCKED"
    assert payload["revision_retest_task_plan"]["next_task_id"] == "lock_evaluation_protocol"
    assert len(JsonFileRepository(tmp_path).load_automation_runs()) == 1


def test_execute_revision_retest_next_task_locks_evaluation_protocol(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
    )
    split = SplitManifest(
        manifest_id="split-manifest:executor-retest",
        created_at=_now(),
        symbol="BTC-USD",
        strategy_card_id=revision.card_id,
        dataset_id="research-dataset:revision-retest",
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 2, 1, tzinfo=UTC),
        validation_start=datetime(2026, 2, 2, tzinfo=UTC),
        validation_end=datetime(2026, 3, 1, tzinfo=UTC),
        holdout_start=datetime(2026, 3, 2, tzinfo=UTC),
        holdout_end=datetime(2026, 4, 1, tzinfo=UTC),
        embargo_hours=24,
        status="LOCKED",
        locked_by="codex",
        decision_basis="locked_evaluation_protocol",
    )
    repository.save_split_manifest(split)

    result = execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 10, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )

    assert result.executed_task_id == "lock_evaluation_protocol"
    assert result.before_plan.next_task_id == "lock_evaluation_protocol"
    assert result.after_plan.next_task_id == "generate_baseline_evaluation"
    assert result.automation_run.status == "RETEST_TASK_EXECUTED"
    assert result.after_plan.cost_model_id is not None
    assert result.created_artifact_ids == [result.after_plan.split_manifest_id, result.after_plan.cost_model_id]
    assert result.after_plan.split_manifest_id != split.manifest_id
    assert len(repository.load_cost_model_snapshots()) == 1
    assert repository.load_automation_runs() == [result.automation_run]


def test_execute_revision_retest_next_task_rejects_unsupported_ready_task(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 1, 4, tzinfo=UTC),
        validation_start=datetime(2026, 1, 5, tzinfo=UTC),
        validation_end=datetime(2026, 1, 7, tzinfo=UTC),
        holdout_start=datetime(2026, 1, 8, tzinfo=UTC),
        holdout_end=datetime(2026, 1, 10, tzinfo=UTC),
    )

    baseline_result = execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 10, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )

    assert baseline_result.executed_task_id == "generate_baseline_evaluation"
    assert baseline_result.after_plan.next_task_id == "run_backtest"
    _seed_retest_full_window_candles(repository)
    backtest_result = execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 10, 5, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )

    assert backtest_result.executed_task_id == "run_backtest"
    assert backtest_result.after_plan.next_task_id == "run_walk_forward"
    walk_forward_result = execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 10, 10, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )

    assert walk_forward_result.executed_task_id == "run_walk_forward"
    assert walk_forward_result.after_plan.next_task_id == "record_passed_retest_trial"
    passed_trial_result = execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 10, 15, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )

    assert passed_trial_result.executed_task_id == "record_passed_retest_trial"
    assert passed_trial_result.after_plan.next_task_id == "evaluate_leaderboard_gate"
    leaderboard_result = execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 10, 20, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )

    assert leaderboard_result.executed_task_id == "evaluate_leaderboard_gate"
    assert leaderboard_result.after_plan.next_task_id == "record_paper_shadow_outcome"
    with pytest.raises(ValueError, match="revision_retest_next_task_not_ready:record_paper_shadow_outcome"):
        execute_revision_retest_next_task(
            repository=repository,
            storage_dir=tmp_path,
            symbol="BTC-USD",
            created_at=datetime(2026, 4, 29, 10, 25, tzinfo=UTC),
            revision_card_id=revision.card_id,
        )


def test_cli_execute_revision_retest_next_task_outputs_json_and_persists(tmp_path, capsys):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
    )
    repository.save_split_manifest(
        SplitManifest(
            manifest_id="split-manifest:executor-cli",
            created_at=_now(),
            symbol="BTC-USD",
            strategy_card_id=revision.card_id,
            dataset_id="research-dataset:revision-retest",
            train_start=datetime(2026, 1, 1, tzinfo=UTC),
            train_end=datetime(2026, 2, 1, tzinfo=UTC),
            validation_start=datetime(2026, 2, 2, tzinfo=UTC),
            validation_end=datetime(2026, 3, 1, tzinfo=UTC),
            holdout_start=datetime(2026, 3, 2, tzinfo=UTC),
            holdout_end=datetime(2026, 4, 1, tzinfo=UTC),
            embargo_hours=24,
            status="LOCKED",
            locked_by="codex",
            decision_basis="locked_evaluation_protocol",
        )
    )

    assert main(
        [
            "execute-revision-retest-next-task",
            "--storage-dir",
            str(tmp_path),
            "--revision-card-id",
            revision.card_id,
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-29T10:00:00+00:00",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["executed_task_id"] == "lock_evaluation_protocol"
    assert payload["automation_run"]["status"] == "RETEST_TASK_EXECUTED"
    assert payload["before_plan"]["next_task_id"] == "lock_evaluation_protocol"
    assert payload["after_plan"]["next_task_id"] == "generate_baseline_evaluation"
    assert len(JsonFileRepository(tmp_path).load_automation_runs()) == 1
    assert len(JsonFileRepository(tmp_path).load_cost_model_snapshots()) == 1


def test_execute_revision_retest_baseline_next_task_writes_baseline(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 2, 1, tzinfo=UTC),
        validation_start=datetime(2026, 2, 2, tzinfo=UTC),
        validation_end=datetime(2026, 3, 1, tzinfo=UTC),
        holdout_start=datetime(2026, 3, 2, tzinfo=UTC),
        holdout_end=datetime(2026, 4, 1, tzinfo=UTC),
    )

    result = execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 10, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )

    assert result.executed_task_id == "generate_baseline_evaluation"
    assert result.before_plan.next_task_id == "generate_baseline_evaluation"
    assert result.after_plan.next_task_id == "run_backtest"
    assert result.automation_run.status == "RETEST_TASK_EXECUTED"
    assert len(repository.load_baseline_evaluations()) == 1
    assert result.created_artifact_ids == [repository.load_baseline_evaluations()[0].baseline_id]
    assert repository.load_automation_runs() == [result.automation_run]


def test_cli_execute_revision_retest_baseline_next_task_outputs_json(tmp_path, capsys):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 2, 1, tzinfo=UTC),
        validation_start=datetime(2026, 2, 2, tzinfo=UTC),
        validation_end=datetime(2026, 3, 1, tzinfo=UTC),
        holdout_start=datetime(2026, 3, 2, tzinfo=UTC),
        holdout_end=datetime(2026, 4, 1, tzinfo=UTC),
    )

    assert main(
        [
            "execute-revision-retest-next-task",
            "--storage-dir",
            str(tmp_path),
            "--revision-card-id",
            revision.card_id,
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-29T10:30:00+00:00",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["executed_task_id"] == "generate_baseline_evaluation"
    assert payload["automation_run"]["status"] == "RETEST_TASK_EXECUTED"
    assert payload["before_plan"]["next_task_id"] == "generate_baseline_evaluation"
    assert payload["after_plan"]["next_task_id"] == "run_backtest"
    assert len(JsonFileRepository(tmp_path).load_baseline_evaluations()) == 1


def test_execute_revision_retest_backtest_next_task_writes_backtest(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 2, 1, tzinfo=UTC),
        validation_start=datetime(2026, 2, 2, tzinfo=UTC),
        validation_end=datetime(2026, 3, 1, tzinfo=UTC),
        holdout_start=datetime(2026, 3, 2, tzinfo=UTC),
        holdout_end=datetime(2026, 3, 7, tzinfo=UTC),
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 10, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    _seed_retest_candles(repository)

    result = execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 11, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )

    assert result.executed_task_id == "run_backtest"
    assert result.before_plan.next_task_id == "run_backtest"
    assert result.after_plan.next_task_id == "run_walk_forward"
    assert result.automation_run.status == "RETEST_TASK_EXECUTED"
    assert len(repository.load_backtest_runs()) == 1
    assert len(repository.load_backtest_results()) == 1
    assert result.created_artifact_ids == [repository.load_backtest_results()[0].result_id]
    assert len(repository.load_automation_runs()) == 2


def test_cli_execute_revision_retest_backtest_next_task_outputs_json(tmp_path, capsys):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 2, 1, tzinfo=UTC),
        validation_start=datetime(2026, 2, 2, tzinfo=UTC),
        validation_end=datetime(2026, 3, 1, tzinfo=UTC),
        holdout_start=datetime(2026, 3, 2, tzinfo=UTC),
        holdout_end=datetime(2026, 3, 7, tzinfo=UTC),
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 10, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    _seed_retest_candles(repository)

    assert main(
        [
            "execute-revision-retest-next-task",
            "--storage-dir",
            str(tmp_path),
            "--revision-card-id",
            revision.card_id,
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-29T11:00:00+00:00",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["executed_task_id"] == "run_backtest"
    assert payload["before_plan"]["next_task_id"] == "run_backtest"
    assert payload["after_plan"]["next_task_id"] == "run_walk_forward"
    assert len(JsonFileRepository(tmp_path).load_backtest_results()) == 1


def test_execute_revision_retest_walk_forward_next_task_writes_validation(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 1, 4, tzinfo=UTC),
        validation_start=datetime(2026, 1, 5, tzinfo=UTC),
        validation_end=datetime(2026, 1, 7, tzinfo=UTC),
        holdout_start=datetime(2026, 1, 8, tzinfo=UTC),
        holdout_end=datetime(2026, 1, 10, tzinfo=UTC),
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 10, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    _seed_retest_full_window_candles(repository)
    backtest_result = execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 11, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )

    result = execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 11, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    validations = repository.load_walk_forward_validations()

    assert result.executed_task_id == "run_walk_forward"
    assert result.before_plan.next_task_id == "run_walk_forward"
    assert result.after_plan.next_task_id == "record_passed_retest_trial"
    assert result.automation_run.status == "RETEST_TASK_EXECUTED"
    assert len(validations) == 1
    assert result.created_artifact_ids == [validations[0].validation_id]
    assert backtest_result.created_artifact_ids[0] in validations[0].backtest_result_ids
    assert len(repository.load_automation_runs()) == 3


def test_cli_execute_revision_retest_walk_forward_next_task_outputs_json(tmp_path, capsys):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 1, 4, tzinfo=UTC),
        validation_start=datetime(2026, 1, 5, tzinfo=UTC),
        validation_end=datetime(2026, 1, 7, tzinfo=UTC),
        holdout_start=datetime(2026, 1, 8, tzinfo=UTC),
        holdout_end=datetime(2026, 1, 10, tzinfo=UTC),
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 10, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    _seed_retest_full_window_candles(repository)
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 11, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )

    assert main(
        [
            "execute-revision-retest-next-task",
            "--storage-dir",
            str(tmp_path),
            "--revision-card-id",
            revision.card_id,
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-29T11:30:00+00:00",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["executed_task_id"] == "run_walk_forward"
    assert payload["before_plan"]["next_task_id"] == "run_walk_forward"
    assert payload["after_plan"]["next_task_id"] == "record_passed_retest_trial"
    assert len(JsonFileRepository(tmp_path).load_walk_forward_validations()) == 1


def test_execute_revision_retest_passed_trial_next_task_records_trial(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 1, 4, tzinfo=UTC),
        validation_start=datetime(2026, 1, 5, tzinfo=UTC),
        validation_end=datetime(2026, 1, 7, tzinfo=UTC),
        holdout_start=datetime(2026, 1, 8, tzinfo=UTC),
        holdout_end=datetime(2026, 1, 10, tzinfo=UTC),
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 10, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    _seed_retest_full_window_candles(repository)
    backtest_result = execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 11, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    walk_forward_result = execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 11, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )

    result = execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    revision_trials = [trial for trial in repository.load_experiment_trials() if trial.strategy_card_id == revision.card_id]
    passed_trials = [trial for trial in revision_trials if trial.status == "PASSED"]

    assert result.executed_task_id == "record_passed_retest_trial"
    assert result.before_plan.next_task_id == "record_passed_retest_trial"
    assert result.after_plan.next_task_id == "evaluate_leaderboard_gate"
    assert result.automation_run.status == "RETEST_TASK_EXECUTED"
    assert len(passed_trials) == 1
    assert passed_trials[0].dataset_id == "research-dataset:revision-retest"
    assert passed_trials[0].backtest_result_id == backtest_result.created_artifact_ids[0]
    assert passed_trials[0].walk_forward_validation_id == walk_forward_result.created_artifact_ids[0]
    assert passed_trials[0].parameters["revision_retest_protocol"] == RETEST_PROTOCOL_VERSION
    assert passed_trials[0].parameters["revision_retest_source_card_id"] == revision.card_id
    assert passed_trials[0].parameters["revision_source_outcome_id"] == outcome.outcome_id
    assert result.created_artifact_ids == [passed_trials[0].trial_id]
    assert len(repository.load_automation_runs()) == 4


def test_execute_revision_retest_passed_trial_blocks_budget_exhaustion(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=1,
        seed=7,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 1, 4, tzinfo=UTC),
        validation_start=datetime(2026, 1, 5, tzinfo=UTC),
        validation_end=datetime(2026, 1, 7, tzinfo=UTC),
        holdout_start=datetime(2026, 1, 8, tzinfo=UTC),
        holdout_end=datetime(2026, 1, 10, tzinfo=UTC),
    )
    record_experiment_trial(
        repository=repository,
        created_at=datetime(2026, 4, 29, 10, 0, tzinfo=UTC),
        strategy_card_id=revision.card_id,
        trial_index=99,
        status="FAILED",
        symbol="BTC-USD",
        max_trials=1,
        failure_reason="prior_failed_retest",
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 10, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    _seed_retest_full_window_candles(repository)
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 11, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 11, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    automation_count_before = len(repository.load_automation_runs())

    with pytest.raises(ValueError, match="revision_retest_trial_budget_exhausted"):
        execute_revision_retest_next_task(
            repository=repository,
            storage_dir=tmp_path,
            symbol="BTC-USD",
            created_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
            revision_card_id=revision.card_id,
        )

    revision_trials = [trial for trial in repository.load_experiment_trials() if trial.strategy_card_id == revision.card_id]
    assert [trial.status for trial in revision_trials].count("PASSED") == 0
    assert [trial.status for trial in revision_trials].count("ABORTED") == 0
    assert len(repository.load_automation_runs()) == automation_count_before


def test_execute_revision_retest_leaderboard_gate_next_task_writes_evaluation_and_entry(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 1, 4, tzinfo=UTC),
        validation_start=datetime(2026, 1, 5, tzinfo=UTC),
        validation_end=datetime(2026, 1, 7, tzinfo=UTC),
        holdout_start=datetime(2026, 1, 8, tzinfo=UTC),
        holdout_end=datetime(2026, 1, 10, tzinfo=UTC),
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 10, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    _seed_retest_full_window_candles(repository)
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 11, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 11, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )

    result = execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 12, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    evaluations = [
        item for item in repository.load_locked_evaluation_results() if item.strategy_card_id == revision.card_id
    ]
    entries = [item for item in repository.load_leaderboard_entries() if item.strategy_card_id == revision.card_id]

    assert result.executed_task_id == "evaluate_leaderboard_gate"
    assert result.before_plan.next_task_id == "evaluate_leaderboard_gate"
    assert result.after_plan.next_task_id == "record_paper_shadow_outcome"
    assert len(evaluations) == 1
    assert len(entries) == 1
    evaluation = evaluations[0]
    entry = entries[0]
    assert evaluation.trial_id == result.before_plan.passed_trial_id
    assert evaluation.split_manifest_id == result.before_plan.split_manifest_id
    assert evaluation.cost_model_id == result.before_plan.cost_model_id
    assert evaluation.baseline_id == result.before_plan.baseline_id
    assert evaluation.backtest_result_id == result.before_plan.backtest_result_id
    assert evaluation.walk_forward_validation_id == result.before_plan.walk_forward_validation_id
    assert entry.evaluation_id == evaluation.evaluation_id
    assert entry.trial_id == result.before_plan.passed_trial_id
    assert not evaluation.rankable
    assert not entry.rankable
    assert "baseline_edge_missing" in evaluation.blocked_reasons
    assert "baseline_edge_missing" in entry.blocked_reasons
    assert evaluation.gate_metrics["model_edge"] is None
    assert result.created_artifact_ids == [evaluation.evaluation_id, entry.entry_id]
    assert result.after_plan.locked_evaluation_id == evaluation.evaluation_id
    assert result.after_plan.leaderboard_entry_id == entry.entry_id
    assert len(repository.load_automation_runs()) == 5


def test_cli_execute_revision_retest_passed_trial_next_task_outputs_json(tmp_path, capsys):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 1, 4, tzinfo=UTC),
        validation_start=datetime(2026, 1, 5, tzinfo=UTC),
        validation_end=datetime(2026, 1, 7, tzinfo=UTC),
        holdout_start=datetime(2026, 1, 8, tzinfo=UTC),
        holdout_end=datetime(2026, 1, 10, tzinfo=UTC),
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 10, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    _seed_retest_full_window_candles(repository)
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 11, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 11, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )

    assert main(
        [
            "execute-revision-retest-next-task",
            "--storage-dir",
            str(tmp_path),
            "--revision-card-id",
            revision.card_id,
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-29T12:00:00+00:00",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    revision_trials = [
        trial for trial in JsonFileRepository(tmp_path).load_experiment_trials() if trial.strategy_card_id == revision.card_id
    ]

    assert payload["executed_task_id"] == "record_passed_retest_trial"
    assert payload["before_plan"]["next_task_id"] == "record_passed_retest_trial"
    assert payload["after_plan"]["next_task_id"] == "evaluate_leaderboard_gate"
    assert len([trial for trial in revision_trials if trial.status == "PASSED"]) == 1


def test_cli_execute_revision_retest_leaderboard_gate_next_task_outputs_json(tmp_path, capsys):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 1, 4, tzinfo=UTC),
        validation_start=datetime(2026, 1, 5, tzinfo=UTC),
        validation_end=datetime(2026, 1, 7, tzinfo=UTC),
        holdout_start=datetime(2026, 1, 8, tzinfo=UTC),
        holdout_end=datetime(2026, 1, 10, tzinfo=UTC),
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 10, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    _seed_retest_full_window_candles(repository)
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 11, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 11, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )

    assert main(
        [
            "execute-revision-retest-next-task",
            "--storage-dir",
            str(tmp_path),
            "--revision-card-id",
            revision.card_id,
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-29T12:30:00+00:00",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    saved_repository = JsonFileRepository(tmp_path)

    assert payload["executed_task_id"] == "evaluate_leaderboard_gate"
    assert payload["before_plan"]["next_task_id"] == "evaluate_leaderboard_gate"
    assert payload["after_plan"]["next_task_id"] == "record_paper_shadow_outcome"
    evaluations = [
        item for item in saved_repository.load_locked_evaluation_results() if item.strategy_card_id == revision.card_id
    ]
    entries = [item for item in saved_repository.load_leaderboard_entries() if item.strategy_card_id == revision.card_id]
    assert len(evaluations) == 1
    assert len(entries) == 1
    assert payload["created_artifact_ids"] == [
        evaluations[0].evaluation_id,
        entries[0].entry_id,
    ]


def _seed_revision_retest_through_leaderboard(tmp_path):
    repository, _card, _trial, _evaluation, _entry, _decision, outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=outcome.outcome_id,
    ).strategy_card
    create_revision_retest_scaffold(
        repository=repository,
        created_at=_now(),
        revision_card_id=revision.card_id,
        symbol="BTC-USD",
        dataset_id="research-dataset:revision-retest",
        max_trials=20,
        seed=7,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 1, 4, tzinfo=UTC),
        validation_start=datetime(2026, 1, 5, tzinfo=UTC),
        validation_end=datetime(2026, 1, 7, tzinfo=UTC),
        holdout_start=datetime(2026, 1, 8, tzinfo=UTC),
        holdout_end=datetime(2026, 1, 10, tzinfo=UTC),
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 10, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    _seed_retest_full_window_candles(repository)
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 11, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 11, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    leaderboard_result = execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 12, 30, tzinfo=UTC),
        revision_card_id=revision.card_id,
    )
    assert leaderboard_result.after_plan.next_task_id == "record_paper_shadow_outcome"
    return repository, revision, leaderboard_result


def _seed_lineage_replacement_retest_through_shadow(tmp_path):
    repository, _card, _trial, _evaluation, entry, _decision, source_outcome = _seed_repository(
        tmp_path,
        shadow_action="RETIRE",
    )
    revision = propose_strategy_revision(
        repository=repository,
        created_at=_now(),
        paper_shadow_outcome_id=source_outcome.outcome_id,
    ).strategy_card
    repository.save_paper_shadow_outcome(
        PaperShadowOutcome(
            outcome_id="paper-shadow-outcome:revision-quarantine",
            created_at=datetime(2026, 4, 29, 9, 30, tzinfo=UTC),
            leaderboard_entry_id=entry.entry_id,
            evaluation_id=entry.evaluation_id,
            strategy_card_id=revision.card_id,
            trial_id=entry.trial_id,
            symbol="BTC-USD",
            window_start=datetime(2026, 4, 28, 9, 30, tzinfo=UTC),
            window_end=datetime(2026, 4, 29, 9, 30, tzinfo=UTC),
            observed_return=-0.06,
            benchmark_return=0.01,
            excess_return_after_costs=-0.08,
            max_adverse_excursion=0.16,
            turnover=2.4,
            outcome_grade="FAIL",
            failure_attributions=["drawdown_breach", "weak_baseline_edge"],
            recommended_promotion_stage="PAPER_SHADOW_FAILED",
            recommended_strategy_action="QUARANTINE_STRATEGY",
            blocked_reasons=["paper_shadow_failed"],
            notes=[],
            decision_basis="test",
        )
    )
    create_lineage_research_agenda(
        repository=repository,
        created_at=datetime(2026, 4, 29, 10, 0, tzinfo=UTC),
        symbol="BTC-USD",
    )
    replacement = execute_lineage_research_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 10, 30, tzinfo=UTC),
    ).created_artifact_ids[0]
    create_revision_retest_scaffold(
        repository=repository,
        created_at=datetime(2026, 4, 29, 11, 0, tzinfo=UTC),
        revision_card_id=replacement,
        symbol="BTC-USD",
        dataset_id="research-dataset:replacement-retest",
        max_trials=20,
        seed=7,
        train_start=datetime(2026, 1, 1, tzinfo=UTC),
        train_end=datetime(2026, 1, 4, tzinfo=UTC),
        validation_start=datetime(2026, 1, 5, tzinfo=UTC),
        validation_end=datetime(2026, 1, 7, tzinfo=UTC),
        holdout_start=datetime(2026, 1, 8, tzinfo=UTC),
        holdout_end=datetime(2026, 1, 10, tzinfo=UTC),
    )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 29, 11, 30, tzinfo=UTC),
        revision_card_id=replacement,
    )
    _seed_retest_full_window_candles(repository)
    for created_at in (
        datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
        datetime(2026, 4, 29, 12, 30, tzinfo=UTC),
        datetime(2026, 4, 29, 13, 0, tzinfo=UTC),
        datetime(2026, 4, 29, 13, 30, tzinfo=UTC),
    ):
        execute_revision_retest_next_task(
            repository=repository,
            storage_dir=tmp_path,
            symbol="BTC-USD",
            created_at=created_at,
            revision_card_id=replacement,
        )
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 30, 14, 0, tzinfo=UTC),
        revision_card_id=replacement,
        shadow_window_start=datetime(2026, 4, 29, 13, 30, tzinfo=UTC),
        shadow_window_end=datetime(2026, 4, 30, 13, 30, tzinfo=UTC),
        shadow_observed_return=0.03,
        shadow_benchmark_return=0.01,
        shadow_max_adverse_excursion=0.02,
        shadow_turnover=1.2,
    )
    return repository, replacement


def test_execute_revision_retest_shadow_outcome_requires_observation_inputs(tmp_path):
    repository, revision, _leaderboard_result = _seed_revision_retest_through_leaderboard(tmp_path)

    with pytest.raises(ValueError, match="revision_retest_next_task_not_ready:record_paper_shadow_outcome"):
        execute_revision_retest_next_task(
            repository=repository,
            storage_dir=tmp_path,
            symbol="BTC-USD",
            created_at=datetime(2026, 4, 29, 13, 0, tzinfo=UTC),
            revision_card_id=revision.card_id,
        )

    revision_outcomes = [
        outcome for outcome in repository.load_paper_shadow_outcomes() if outcome.strategy_card_id == revision.card_id
    ]
    assert revision_outcomes == []


def test_execute_revision_retest_shadow_outcome_rejects_unfinished_window(tmp_path):
    repository, revision, _leaderboard_result = _seed_revision_retest_through_leaderboard(tmp_path)

    with pytest.raises(ValueError, match="revision_retest_shadow_window_not_complete"):
        execute_revision_retest_next_task(
            repository=repository,
            storage_dir=tmp_path,
            symbol="BTC-USD",
            created_at=datetime(2026, 4, 29, 13, 0, tzinfo=UTC),
            revision_card_id=revision.card_id,
            shadow_window_start=datetime(2026, 4, 29, 12, 30, tzinfo=UTC),
            shadow_window_end=datetime(2026, 4, 30, 12, 30, tzinfo=UTC),
            shadow_observed_return=0.04,
            shadow_benchmark_return=0.01,
        )

    revision_outcomes = [
        outcome for outcome in repository.load_paper_shadow_outcomes() if outcome.strategy_card_id == revision.card_id
    ]
    assert revision_outcomes == []
    plan = build_revision_retest_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        revision_card_id=revision.card_id,
    )
    assert plan.next_task_id == "record_paper_shadow_outcome"
    assert plan.task_by_id("record_paper_shadow_outcome").blocked_reason == "shadow_window_observation_required"


def test_execute_revision_retest_shadow_outcome_next_task_records_observed_window(tmp_path):
    repository, revision, leaderboard_result = _seed_revision_retest_through_leaderboard(tmp_path)

    result = execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 30, 13, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
        shadow_window_start=datetime(2026, 4, 29, 12, 30, tzinfo=UTC),
        shadow_window_end=datetime(2026, 4, 30, 12, 30, tzinfo=UTC),
        shadow_observed_return=0.04,
        shadow_benchmark_return=0.01,
        shadow_max_adverse_excursion=0.02,
        shadow_turnover=1.5,
        shadow_note="explicit PR26 shadow observation",
    )
    revision_outcomes = [
        outcome for outcome in repository.load_paper_shadow_outcomes() if outcome.strategy_card_id == revision.card_id
    ]

    assert result.executed_task_id == "record_paper_shadow_outcome"
    assert result.before_plan.next_task_id == "record_paper_shadow_outcome"
    assert result.after_plan.next_task_id is None
    assert len(revision_outcomes) == 1
    outcome = revision_outcomes[0]
    assert outcome.leaderboard_entry_id == leaderboard_result.after_plan.leaderboard_entry_id
    assert outcome.window_start == datetime(2026, 4, 29, 12, 30, tzinfo=UTC)
    assert outcome.window_end == datetime(2026, 4, 30, 12, 30, tzinfo=UTC)
    assert outcome.observed_return == 0.04
    assert outcome.benchmark_return == 0.01
    assert outcome.excess_return_after_costs == 0.03
    assert outcome.max_adverse_excursion == 0.02
    assert outcome.turnover == 1.5
    assert outcome.notes == ["explicit PR26 shadow observation"]
    assert result.created_artifact_ids == [outcome.outcome_id]
    assert len(repository.load_automation_runs()) == 6


def test_cli_execute_revision_retest_shadow_outcome_next_task_outputs_json(tmp_path, capsys):
    repository, revision, _leaderboard_result = _seed_revision_retest_through_leaderboard(tmp_path)

    assert main(
        [
            "execute-revision-retest-next-task",
            "--storage-dir",
            str(tmp_path),
            "--revision-card-id",
            revision.card_id,
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-30T13:00:00+00:00",
            "--shadow-window-start",
            "2026-04-29T12:30:00+00:00",
            "--shadow-window-end",
            "2026-04-30T12:30:00+00:00",
            "--shadow-observed-return",
            "0.04",
            "--shadow-benchmark-return",
            "0.01",
            "--shadow-max-adverse-excursion",
            "0.02",
            "--shadow-turnover",
            "1.5",
            "--shadow-note",
            "explicit PR26 CLI shadow observation",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    saved_repository = JsonFileRepository(tmp_path)
    revision_outcomes = [
        outcome for outcome in saved_repository.load_paper_shadow_outcomes() if outcome.strategy_card_id == revision.card_id
    ]

    assert payload["executed_task_id"] == "record_paper_shadow_outcome"
    assert payload["before_plan"]["next_task_id"] == "record_paper_shadow_outcome"
    assert payload["after_plan"]["next_task_id"] is None
    assert len(revision_outcomes) == 1
    assert payload["created_artifact_ids"] == [revision_outcomes[0].outcome_id]


def test_completed_revision_retest_chain_is_visible_as_done(tmp_path):
    repository, revision, _leaderboard_result = _seed_revision_retest_through_leaderboard(tmp_path)
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 30, 13, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
        shadow_window_start=datetime(2026, 4, 29, 12, 30, tzinfo=UTC),
        shadow_window_end=datetime(2026, 4, 30, 12, 30, tzinfo=UTC),
        shadow_observed_return=0.04,
        shadow_benchmark_return=0.01,
        shadow_max_adverse_excursion=0.02,
        shadow_turnover=1.5,
    )

    chain = resolve_latest_strategy_research_chain(
        symbol="BTC-USD",
        strategy_cards=repository.load_strategy_cards(),
        experiment_trials=repository.load_experiment_trials(),
        locked_evaluations=repository.load_locked_evaluation_results(),
        split_manifests=repository.load_split_manifests(),
        leaderboard_entries=repository.load_leaderboard_entries(),
        paper_shadow_outcomes=repository.load_paper_shadow_outcomes(),
        research_agendas=repository.load_research_agendas(),
        research_autopilot_runs=repository.load_research_autopilot_runs(),
    )

    assert chain.revision_candidate is not None
    assert chain.revision_candidate.strategy_card.card_id == revision.card_id
    assert chain.revision_candidate.retest_trial is not None
    assert chain.revision_candidate.retest_trial.status == "PASSED"
    assert chain.revision_candidate.retest_next_required_artifacts == []


def test_revision_retest_autopilot_run_allows_missing_strategy_decision(tmp_path):
    repository, revision, _leaderboard_result = _seed_revision_retest_through_leaderboard(tmp_path)
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 30, 13, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
        shadow_window_start=datetime(2026, 4, 29, 12, 30, tzinfo=UTC),
        shadow_window_end=datetime(2026, 4, 30, 12, 30, tzinfo=UTC),
        shadow_observed_return=0.04,
        shadow_benchmark_return=0.01,
        shadow_max_adverse_excursion=0.02,
        shadow_turnover=1.5,
    )
    plan = build_revision_retest_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        revision_card_id=revision.card_id,
    )
    agenda = next(
        item
        for item in repository.load_research_agendas()
        if item.strategy_card_ids == [revision.card_id]
    )

    run = record_research_autopilot_run(
        repository=repository,
        created_at=datetime(2026, 4, 30, 13, 30, tzinfo=UTC),
        agenda_id=agenda.agenda_id,
        strategy_card_id=revision.card_id,
        experiment_trial_id=plan.passed_trial_id,
        locked_evaluation_id=plan.locked_evaluation_id,
        leaderboard_entry_id=plan.leaderboard_entry_id,
        paper_shadow_outcome_id=plan.paper_shadow_outcome_id,
    )

    assert "strategy_decision_missing" not in run.blocked_reasons
    assert "locked_evaluation_not_rankable" in run.blocked_reasons
    assert run.loop_status == "BLOCKED"
    assert run.next_research_action == "REPAIR_EVIDENCE_CHAIN"
    assert run.strategy_decision_id is None
    assert run.paper_shadow_outcome_id == plan.paper_shadow_outcome_id


def test_sqlite_repository_preserves_revision_retest_autopilot_run_without_decision(tmp_path):
    repository, revision, _leaderboard_result = _seed_revision_retest_through_leaderboard(tmp_path)
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 30, 13, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
        shadow_window_start=datetime(2026, 4, 29, 12, 30, tzinfo=UTC),
        shadow_window_end=datetime(2026, 4, 30, 12, 30, tzinfo=UTC),
        shadow_observed_return=0.04,
        shadow_benchmark_return=0.01,
        shadow_max_adverse_excursion=0.02,
        shadow_turnover=1.5,
    )
    plan = build_revision_retest_task_plan(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        revision_card_id=revision.card_id,
    )
    agenda = next(
        item
        for item in repository.load_research_agendas()
        if item.strategy_card_ids == [revision.card_id]
    )
    run = record_research_autopilot_run(
        repository=repository,
        created_at=datetime(2026, 4, 30, 13, 30, tzinfo=UTC),
        agenda_id=agenda.agenda_id,
        strategy_card_id=revision.card_id,
        experiment_trial_id=plan.passed_trial_id,
        locked_evaluation_id=plan.locked_evaluation_id,
        leaderboard_entry_id=plan.leaderboard_entry_id,
        paper_shadow_outcome_id=plan.paper_shadow_outcome_id,
    )
    sqlite_repo = SQLiteRepository(tmp_path)

    migrate_jsonl_to_sqlite(storage_dir=tmp_path, db_path=sqlite_repo.db_path)

    loaded_run = next(
        item
        for item in sqlite_repo.load_research_autopilot_runs()
        if item.run_id == run.run_id
    )
    assert loaded_run.strategy_decision_id is None
    assert loaded_run.paper_shadow_outcome_id == plan.paper_shadow_outcome_id
    assert loaded_run.blocked_reasons == run.blocked_reasons


def test_revision_retest_autopilot_helper_records_latest_completed_chain(tmp_path):
    repository, revision, _leaderboard_result = _seed_revision_retest_through_leaderboard(tmp_path)
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 30, 13, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
        shadow_window_start=datetime(2026, 4, 29, 12, 30, tzinfo=UTC),
        shadow_window_end=datetime(2026, 4, 30, 12, 30, tzinfo=UTC),
        shadow_observed_return=0.04,
        shadow_benchmark_return=0.01,
        shadow_max_adverse_excursion=0.02,
        shadow_turnover=1.5,
    )

    result = record_revision_retest_autopilot_run(
        repository=repository,
        storage_dir=tmp_path,
        created_at=datetime(2026, 4, 30, 13, 30, tzinfo=UTC),
        symbol="BTC-USD",
        revision_card_id=revision.card_id,
    )
    saved_runs = [run for run in repository.load_research_autopilot_runs() if run.strategy_card_id == revision.card_id]

    assert result.revision_retest_task_plan.next_task_id is None
    assert result.research_autopilot_run.strategy_card_id == revision.card_id
    assert result.research_autopilot_run.experiment_trial_id == result.revision_retest_task_plan.passed_trial_id
    assert result.research_autopilot_run.locked_evaluation_id == result.revision_retest_task_plan.locked_evaluation_id
    assert result.research_autopilot_run.leaderboard_entry_id == result.revision_retest_task_plan.leaderboard_entry_id
    assert result.research_autopilot_run.paper_shadow_outcome_id == result.revision_retest_task_plan.paper_shadow_outcome_id
    assert result.research_autopilot_run.strategy_decision_id is None
    assert saved_runs[-1] == result.research_autopilot_run


def test_replacement_retest_autopilot_helper_records_latest_completed_chain(tmp_path):
    repository, replacement_card_id = _seed_lineage_replacement_retest_through_shadow(tmp_path)

    result = record_revision_retest_autopilot_run(
        repository=repository,
        storage_dir=tmp_path,
        created_at=datetime(2026, 4, 30, 14, 30, tzinfo=UTC),
        symbol="BTC-USD",
        revision_card_id=replacement_card_id,
    )
    saved_runs = [run for run in repository.load_research_autopilot_runs() if run.strategy_card_id == replacement_card_id]

    assert result.revision_retest_task_plan.next_task_id is None
    assert result.research_autopilot_run.strategy_card_id == replacement_card_id
    assert result.research_autopilot_run.experiment_trial_id == result.revision_retest_task_plan.passed_trial_id
    assert result.research_autopilot_run.locked_evaluation_id == result.revision_retest_task_plan.locked_evaluation_id
    assert result.research_autopilot_run.leaderboard_entry_id == result.revision_retest_task_plan.leaderboard_entry_id
    assert result.research_autopilot_run.paper_shadow_outcome_id == result.revision_retest_task_plan.paper_shadow_outcome_id
    assert "agenda_strategy_card_mismatch" not in result.research_autopilot_run.blocked_reasons
    assert "strategy_decision_missing" not in result.research_autopilot_run.blocked_reasons
    assert saved_runs[-1] == result.research_autopilot_run


def test_cli_record_replacement_retest_autopilot_run_outputs_json(tmp_path, capsys):
    _repository, replacement_card_id = _seed_lineage_replacement_retest_through_shadow(tmp_path)

    assert main(
        [
            "record-revision-retest-autopilot-run",
            "--storage-dir",
            str(tmp_path),
            "--revision-card-id",
            replacement_card_id,
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-30T14:30:00+00:00",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["revision_retest_task_plan"]["next_task_id"] is None
    assert payload["research_autopilot_run"]["strategy_card_id"] == replacement_card_id
    assert payload["research_autopilot_run"]["paper_shadow_outcome_id"] == payload["revision_retest_task_plan"]["paper_shadow_outcome_id"]
    assert "agenda_strategy_card_mismatch" not in payload["research_autopilot_run"]["blocked_reasons"]
    assert "strategy_decision_missing" not in payload["research_autopilot_run"]["blocked_reasons"]


def test_cli_record_revision_retest_autopilot_run_outputs_json(tmp_path, capsys):
    repository, revision, _leaderboard_result = _seed_revision_retest_through_leaderboard(tmp_path)
    execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 30, 13, 0, tzinfo=UTC),
        revision_card_id=revision.card_id,
        shadow_window_start=datetime(2026, 4, 29, 12, 30, tzinfo=UTC),
        shadow_window_end=datetime(2026, 4, 30, 12, 30, tzinfo=UTC),
        shadow_observed_return=0.04,
        shadow_benchmark_return=0.01,
        shadow_max_adverse_excursion=0.02,
        shadow_turnover=1.5,
    )

    assert main(
        [
            "record-revision-retest-autopilot-run",
            "--storage-dir",
            str(tmp_path),
            "--revision-card-id",
            revision.card_id,
            "--symbol",
            "BTC-USD",
            "--now",
            "2026-04-30T13:30:00+00:00",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["revision_retest_task_plan"]["next_task_id"] is None
    assert payload["research_autopilot_run"]["strategy_card_id"] == revision.card_id
    assert payload["research_autopilot_run"]["strategy_decision_id"] is None
    assert payload["research_autopilot_run"]["paper_shadow_outcome_id"] == payload["revision_retest_task_plan"]["paper_shadow_outcome_id"]


def test_revision_retest_autopilot_helper_rejects_incomplete_chain(tmp_path):
    repository, revision, _leaderboard_result = _seed_revision_retest_through_leaderboard(tmp_path)

    with pytest.raises(ValueError, match="revision_retest_autopilot_run_not_ready:next_task:record_paper_shadow_outcome"):
        record_revision_retest_autopilot_run(
            repository=repository,
            storage_dir=tmp_path,
            created_at=datetime(2026, 4, 29, 13, 0, tzinfo=UTC),
            symbol="BTC-USD",
            revision_card_id=revision.card_id,
        )

    saved_runs = [run for run in repository.load_research_autopilot_runs() if run.strategy_card_id == revision.card_id]
    assert saved_runs == []


def test_cli_creates_research_agenda_and_autopilot_run(tmp_path, capsys):
    _repository, card, trial, evaluation, entry, decision, outcome = _seed_repository(tmp_path)

    assert main(
        [
            "create-research-agenda",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--title",
            "Autopilot trend candidate",
            "--hypothesis",
            "Trend continuation should survive shadow validation.",
            "--strategy-family",
            "trend_following",
            "--strategy-card-id",
            card.card_id,
            "--created-at",
            "2026-04-28T14:00:00+00:00",
        ]
    ) == 0
    agenda_payload = json.loads(capsys.readouterr().out)
    agenda_id = agenda_payload["research_agenda"]["agenda_id"]

    assert main(
        [
            "record-research-autopilot-run",
            "--storage-dir",
            str(tmp_path),
            "--agenda-id",
            agenda_id,
            "--strategy-card-id",
            card.card_id,
            "--experiment-trial-id",
            trial.trial_id,
            "--locked-evaluation-id",
            evaluation.evaluation_id,
            "--leaderboard-entry-id",
            entry.entry_id,
            "--strategy-decision-id",
            decision.decision_id,
            "--paper-shadow-outcome-id",
            outcome.outcome_id,
            "--created-at",
            "2026-04-28T14:00:00+00:00",
        ]
    ) == 0
    run_payload = json.loads(capsys.readouterr().out)

    assert run_payload["research_autopilot_run"]["loop_status"] == "READY_FOR_OPERATOR_REVIEW"


def test_health_check_flags_research_autopilot_link_errors(tmp_path):
    repository = JsonFileRepository(tmp_path)
    agenda = ResearchAgenda(
        agenda_id="research-agenda:broken",
        created_at=_now(),
        symbol="BTC-USD",
        title="Broken agenda",
        hypothesis="Broken links should be visible.",
        priority="HIGH",
        status="OPEN",
        target_strategy_family="trend_following",
        strategy_card_ids=["strategy-card:missing"],
        expected_artifacts=["strategy_card"],
        acceptance_criteria=["Links exist."],
        blocked_actions=["real_order_submission"],
        decision_basis="test",
    )
    run = ResearchAutopilotRun(
        run_id="research-autopilot-run:broken",
        created_at=_now(),
        symbol="BTC-USD",
        agenda_id=agenda.agenda_id,
        strategy_card_id="strategy-card:missing",
        experiment_trial_id="experiment-trial:missing",
        locked_evaluation_id="locked-evaluation:missing",
        leaderboard_entry_id="leaderboard-entry:missing",
        strategy_decision_id="decision:missing",
        paper_shadow_outcome_id="paper-shadow-outcome:missing",
        steps=[],
        loop_status="BLOCKED",
        next_research_action="REPAIR_EVIDENCE_CHAIN",
        blocked_reasons=["test"],
        decision_basis="test",
    )
    repository.save_research_agenda(agenda)
    repository.save_research_autopilot_run(run)

    health = run_health_check(storage_dir=tmp_path, symbol="BTC-USD", now=_now(), create_repair_request=False)
    codes = {finding.code for finding in health.findings}

    assert "research_agenda_missing_strategy_card" in codes
    assert "research_autopilot_run_missing_strategy_card" in codes
    assert "research_autopilot_run_missing_experiment_trial" in codes
    assert "research_autopilot_run_missing_locked_evaluation" in codes
    assert "research_autopilot_run_missing_leaderboard_entry" in codes
    assert "research_autopilot_run_missing_strategy_decision" in codes
    assert "research_autopilot_run_missing_paper_shadow_outcome" in codes


def test_health_check_flags_research_autopilot_mismatched_chain(tmp_path):
    repository, card, trial, evaluation, entry, decision, outcome = _seed_repository(tmp_path)
    other_card = _strategy_card(_now())
    other_card.card_id = "strategy-card:other"
    other_trial = _trial(_now(), other_card)
    other_trial.trial_id = "experiment-trial:other"
    other_trial.strategy_card_id = other_card.card_id
    other_evaluation = _evaluation(_now(), other_card, other_trial)
    other_evaluation.evaluation_id = "locked-evaluation:other"
    other_evaluation.strategy_card_id = other_card.card_id
    other_evaluation.trial_id = other_trial.trial_id
    repository.save_strategy_card(other_card)
    repository.save_experiment_trial(other_trial)
    repository.save_locked_evaluation_result(other_evaluation)
    agenda = create_research_agenda(
        repository=repository,
        created_at=_now(),
        symbol="BTC-USD",
        title="Mixed chain health",
        hypothesis="Health must catch mixed chain.",
        strategy_family="trend_following",
        strategy_card_ids=[card.card_id],
    )
    run = ResearchAutopilotRun(
        run_id="research-autopilot-run:mismatch",
        created_at=_now(),
        symbol="BTC-USD",
        agenda_id=agenda.agenda_id,
        strategy_card_id=card.card_id,
        experiment_trial_id=trial.trial_id,
        locked_evaluation_id=other_evaluation.evaluation_id,
        leaderboard_entry_id=entry.entry_id,
        strategy_decision_id=decision.decision_id,
        paper_shadow_outcome_id=outcome.outcome_id,
        steps=[],
        loop_status="READY_FOR_OPERATOR_REVIEW",
        next_research_action="OPERATOR_REVIEW_FOR_PROMOTION",
        blocked_reasons=[],
        decision_basis="test",
    )
    repository.save_research_autopilot_run(run)

    health = run_health_check(storage_dir=tmp_path, symbol="BTC-USD", now=_now(), create_repair_request=False)
    codes = {finding.code for finding in health.findings}

    assert "research_autopilot_run_locked_evaluation_strategy_card_mismatch" in codes
    assert "research_autopilot_run_locked_evaluation_trial_mismatch" in codes
    assert "research_autopilot_run_leaderboard_evaluation_mismatch" in codes


def test_health_check_flags_research_autopilot_bad_decision_state(tmp_path):
    repository, card, trial, evaluation, entry, decision, outcome = _seed_repository(tmp_path)
    decision.symbol = "ETH-USD"
    decision.action = "STOP_NEW_ENTRIES"
    decision.tradeable = False
    decision.blocked_reason = "health_check_repair_required"
    (tmp_path / "strategy_decisions.jsonl").write_text(
        json.dumps(decision.to_dict()) + "\n",
        encoding="utf-8",
    )
    agenda = create_research_agenda(
        repository=repository,
        created_at=_now(),
        symbol="BTC-USD",
        title="Bad decision health",
        hypothesis="Health should catch bad decisions.",
        strategy_family="trend_following",
        strategy_card_ids=[card.card_id],
    )
    run = ResearchAutopilotRun(
        run_id="research-autopilot-run:bad-decision",
        created_at=_now(),
        symbol="BTC-USD",
        agenda_id=agenda.agenda_id,
        strategy_card_id=card.card_id,
        experiment_trial_id=trial.trial_id,
        locked_evaluation_id=evaluation.evaluation_id,
        leaderboard_entry_id=entry.entry_id,
        strategy_decision_id=decision.decision_id,
        paper_shadow_outcome_id=outcome.outcome_id,
        steps=[],
        loop_status="READY_FOR_OPERATOR_REVIEW",
        next_research_action="OPERATOR_REVIEW_FOR_PROMOTION",
        blocked_reasons=[],
        decision_basis="test",
    )
    repository.save_research_autopilot_run(run)

    health = run_health_check(storage_dir=tmp_path, symbol="BTC-USD", now=_now(), create_repair_request=False)
    codes = {finding.code for finding in health.findings}

    assert "research_autopilot_run_strategy_decision_symbol_mismatch" in codes
    assert "research_autopilot_run_strategy_decision_not_tradeable" in codes
    assert "research_autopilot_run_strategy_decision_fail_closed" in codes
    assert "research_autopilot_run_strategy_decision_blocked" in codes


def test_sqlite_repository_preserves_research_autopilot_artifacts(tmp_path):
    repository, card, trial, evaluation, entry, decision, outcome = _seed_repository(tmp_path)
    agenda = create_research_agenda(
        repository=repository,
        created_at=_now(),
        symbol="BTC-USD",
        title="Autopilot trend candidate",
        hypothesis="Trend continuation should survive shadow validation.",
        strategy_family="trend_following",
        strategy_card_ids=[card.card_id],
    )
    run = record_research_autopilot_run(
        repository=repository,
        created_at=_now(),
        agenda_id=agenda.agenda_id,
        strategy_card_id=card.card_id,
        experiment_trial_id=trial.trial_id,
        locked_evaluation_id=evaluation.evaluation_id,
        leaderboard_entry_id=entry.entry_id,
        strategy_decision_id=decision.decision_id,
        paper_shadow_outcome_id=outcome.outcome_id,
    )
    sqlite_repo = SQLiteRepository(tmp_path)

    migrate_jsonl_to_sqlite(storage_dir=tmp_path, db_path=sqlite_repo.db_path)

    assert sqlite_repo.load_research_agendas() == [agenda]
    assert sqlite_repo.load_research_autopilot_runs() == [run]

    export_dir = tmp_path / "exported"
    export_sqlite_to_jsonl(storage_dir=tmp_path, output_dir=export_dir, db_path=sqlite_repo.db_path)
    exported = JsonFileRepository(export_dir)

    assert exported.load_research_agendas() == [agenda]
    assert exported.load_research_autopilot_runs() == [run]
