from datetime import UTC, datetime, timedelta
import json

import pytest

from forecast_loop.cli import main
from forecast_loop.health import run_health_check
from forecast_loop.models import (
    ExperimentTrial,
    LeaderboardEntry,
    LockedEvaluationResult,
    PaperShadowOutcome,
    StrategyCard,
)
from forecast_loop.paper_shadow import record_paper_shadow_outcome
from forecast_loop.sqlite_repository import SQLiteRepository, export_sqlite_to_jsonl, migrate_jsonl_to_sqlite
from forecast_loop.storage import JsonFileRepository


def _now() -> datetime:
    return datetime(2026, 4, 28, 13, 0, tzinfo=UTC)


def _strategy_card(now: datetime) -> StrategyCard:
    return StrategyCard(
        card_id="strategy-card:shadow",
        created_at=now,
        strategy_name="BTC shadow candidate",
        strategy_family="trend_following",
        version="v1",
        status="ACTIVE",
        symbols=["BTC-USD"],
        hypothesis="BTC trend candidate should keep edge in paper-shadow.",
        signal_description="Locked leaderboard candidate.",
        entry_rules=["Enter when locked gate passes."],
        exit_rules=["Exit when paper-shadow fails."],
        risk_rules=["Quarantine on adverse excursion."],
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
        trial_id="experiment-trial:shadow",
        created_at=now,
        strategy_card_id=card.card_id,
        trial_index=1,
        status="PASSED",
        symbol="BTC-USD",
        seed=42,
        dataset_id="research-dataset:shadow",
        backtest_result_id="backtest-result:shadow",
        walk_forward_validation_id="walk-forward:shadow",
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


def _evaluation(now: datetime, card: StrategyCard, trial: ExperimentTrial) -> LockedEvaluationResult:
    return LockedEvaluationResult(
        evaluation_id="locked-evaluation:shadow",
        created_at=now,
        strategy_card_id=card.card_id,
        trial_id=trial.trial_id,
        split_manifest_id="split-manifest:shadow",
        cost_model_id="cost-model:shadow",
        baseline_id="baseline:shadow",
        backtest_result_id="backtest-result:shadow",
        walk_forward_validation_id="walk-forward:shadow",
        event_edge_evaluation_id=None,
        passed=True,
        rankable=True,
        alpha_score=0.22,
        blocked_reasons=[],
        gate_metrics={"model_edge": 0.12, "holdout_excess_return": 0.06},
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
        entry_id="leaderboard-entry:shadow",
        created_at=now,
        strategy_card_id=card.card_id,
        evaluation_id=evaluation.evaluation_id,
        trial_id=trial.trial_id,
        symbol="BTC-USD",
        rankable=rankable,
        alpha_score=0.22 if rankable else None,
        promotion_stage="CANDIDATE" if rankable else "BLOCKED",
        blocked_reasons=[] if rankable else ["baseline_edge_not_positive"],
        leaderboard_rules_version="pr7-v1",
        decision_basis="test",
    )


def _seed_repository(tmp_path, *, rankable: bool = True):
    now = _now()
    repository = JsonFileRepository(tmp_path)
    card = _strategy_card(now)
    trial = _trial(now, card)
    evaluation = _evaluation(now, card, trial)
    entry = _leaderboard_entry(now, card, trial, evaluation, rankable=rankable)
    repository.save_strategy_card(card)
    repository.save_experiment_trial(trial)
    repository.save_locked_evaluation_result(evaluation)
    repository.save_leaderboard_entry(entry)
    return repository, card, trial, evaluation, entry


def test_json_repository_round_trips_paper_shadow_outcomes(tmp_path):
    repository, _card, _trial, evaluation, entry = _seed_repository(tmp_path)
    outcome = PaperShadowOutcome(
        outcome_id="paper-shadow-outcome:roundtrip",
        created_at=_now(),
        leaderboard_entry_id=entry.entry_id,
        evaluation_id=evaluation.evaluation_id,
        strategy_card_id=entry.strategy_card_id,
        trial_id=entry.trial_id,
        symbol=entry.symbol,
        window_start=_now(),
        window_end=_now() + timedelta(hours=24),
        observed_return=0.04,
        benchmark_return=0.01,
        excess_return_after_costs=0.03,
        max_adverse_excursion=0.02,
        turnover=1.2,
        outcome_grade="PASS",
        failure_attributions=[],
        recommended_promotion_stage="PAPER_SHADOW_PASSED",
        recommended_strategy_action="PROMOTION_READY",
        blocked_reasons=[],
        notes=["fixture"],
        decision_basis="test",
    )

    repository.save_paper_shadow_outcome(outcome)
    repository.save_paper_shadow_outcome(outcome)

    assert repository.load_paper_shadow_outcomes() == [outcome]


def test_paper_shadow_positive_outcome_becomes_promotion_ready(tmp_path):
    repository, _card, _trial, _evaluation, entry = _seed_repository(tmp_path)

    outcome = record_paper_shadow_outcome(
        repository=repository,
        created_at=_now(),
        leaderboard_entry_id=entry.entry_id,
        window_start=_now(),
        window_end=_now() + timedelta(hours=24),
        observed_return=0.05,
        benchmark_return=0.01,
        max_adverse_excursion=0.02,
        turnover=1.1,
        note="shadow pass",
    )

    assert outcome.outcome_grade == "PASS"
    assert outcome.excess_return_after_costs == 0.04
    assert outcome.recommended_promotion_stage == "PAPER_SHADOW_PASSED"
    assert outcome.recommended_strategy_action == "PROMOTION_READY"
    assert outcome.failure_attributions == []
    assert repository.load_paper_shadow_outcomes() == [outcome]


def test_paper_shadow_negative_outcome_retires_candidate(tmp_path):
    repository, _card, _trial, _evaluation, entry = _seed_repository(tmp_path)

    outcome = record_paper_shadow_outcome(
        repository=repository,
        created_at=_now(),
        leaderboard_entry_id=entry.entry_id,
        window_start=_now(),
        window_end=_now() + timedelta(hours=24),
        observed_return=-0.02,
        benchmark_return=0.01,
        max_adverse_excursion=0.06,
        turnover=1.0,
    )

    assert outcome.outcome_grade == "FAIL"
    assert outcome.recommended_promotion_stage == "PAPER_SHADOW_FAILED"
    assert outcome.recommended_strategy_action == "RETIRE"
    assert "negative_excess_return" in outcome.failure_attributions


def test_paper_shadow_blocked_leaderboard_entry_cannot_pass(tmp_path):
    repository, _card, _trial, _evaluation, entry = _seed_repository(tmp_path, rankable=False)

    outcome = record_paper_shadow_outcome(
        repository=repository,
        created_at=_now(),
        leaderboard_entry_id=entry.entry_id,
        window_start=_now(),
        window_end=_now() + timedelta(hours=24),
        observed_return=0.08,
        benchmark_return=0.01,
    )

    assert outcome.outcome_grade == "BLOCKED"
    assert outcome.recommended_promotion_stage == "PAPER_SHADOW_BLOCKED"
    assert outcome.recommended_strategy_action == "QUARANTINE"
    assert "leaderboard_entry_not_rankable" in outcome.blocked_reasons
    assert "baseline_edge_not_positive" in outcome.blocked_reasons


def test_paper_shadow_deduplicates_overlapping_blockers_before_persisting(tmp_path):
    repository, _card, _trial, evaluation, entry = _seed_repository(tmp_path, rankable=False)
    evaluation.passed = False
    evaluation.rankable = False
    evaluation.alpha_score = None
    evaluation.blocked_reasons = [
        "baseline_edge_not_positive",
        "locked_evaluation_not_rankable",
    ]
    (tmp_path / "locked_evaluation_results.jsonl").write_text(
        json.dumps(evaluation.to_dict()) + "\n",
        encoding="utf-8",
    )

    outcome = record_paper_shadow_outcome(
        repository=repository,
        created_at=_now(),
        leaderboard_entry_id=entry.entry_id,
        window_start=_now(),
        window_end=_now() + timedelta(hours=24),
        observed_return=0.08,
        benchmark_return=0.01,
    )

    assert outcome.outcome_grade == "BLOCKED"
    assert outcome.blocked_reasons.count("baseline_edge_not_positive") == 1
    assert outcome.blocked_reasons.count("locked_evaluation_not_rankable") == 1
    assert repository.load_paper_shadow_outcomes()[0].blocked_reasons == outcome.blocked_reasons


def test_paper_shadow_malformed_blocked_entry_fails_closed(tmp_path):
    repository, _card, _trial, evaluation, entry = _seed_repository(tmp_path)
    entry.rankable = True
    entry.alpha_score = 0.22
    entry.promotion_stage = "BLOCKED"
    entry.blocked_reasons = ["manual_block"]
    (tmp_path / "leaderboard_entries.jsonl").write_text(
        json.dumps(entry.to_dict()) + "\n",
        encoding="utf-8",
    )

    outcome = record_paper_shadow_outcome(
        repository=repository,
        created_at=_now(),
        leaderboard_entry_id=entry.entry_id,
        window_start=_now(),
        window_end=_now() + timedelta(hours=24),
        observed_return=0.08,
        benchmark_return=0.01,
    )

    assert outcome.outcome_grade == "BLOCKED"
    assert outcome.recommended_strategy_action == "QUARANTINE"
    assert "leaderboard_entry_promotion_stage_blocked" in outcome.blocked_reasons
    assert "manual_block" in outcome.blocked_reasons

    evaluation.rankable = True
    evaluation.passed = False
    evaluation.blocked_reasons = ["overfit_risk_flagged"]
    entry.promotion_stage = "CANDIDATE"
    entry.blocked_reasons = []
    (tmp_path / "leaderboard_entries.jsonl").write_text(
        json.dumps(entry.to_dict()) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "locked_evaluation_results.jsonl").write_text(
        json.dumps(evaluation.to_dict()) + "\n",
        encoding="utf-8",
    )
    second = record_paper_shadow_outcome(
        repository=repository,
        created_at=_now(),
        leaderboard_entry_id=entry.entry_id,
        window_start=_now() + timedelta(days=1),
        window_end=_now() + timedelta(days=2),
        observed_return=0.08,
        benchmark_return=0.01,
    )

    assert second.outcome_grade == "BLOCKED"
    assert "locked_evaluation_not_passed" in second.blocked_reasons
    assert "overfit_risk_flagged" in second.blocked_reasons


def test_cli_records_paper_shadow_outcome(tmp_path, capsys):
    _repository, _card, _trial, _evaluation, entry = _seed_repository(tmp_path)

    assert main(
        [
            "record-paper-shadow-outcome",
            "--storage-dir",
            str(tmp_path),
            "--leaderboard-entry-id",
            entry.entry_id,
            "--window-start",
            "2026-04-28T13:00:00+00:00",
            "--window-end",
            "2026-04-29T13:00:00+00:00",
            "--observed-return",
            "0.05",
            "--benchmark-return",
            "0.01",
            "--max-adverse-excursion",
            "0.02",
            "--turnover",
            "1.1",
            "--created-at",
            "2026-04-29T13:00:00+00:00",
            "--note",
            "cli shadow pass",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["paper_shadow_outcome"]["leaderboard_entry_id"] == entry.entry_id
    assert payload["paper_shadow_outcome"]["recommended_strategy_action"] == "PROMOTION_READY"


def test_cli_record_paper_shadow_rejects_missing_storage_without_creating_it(tmp_path, capsys):
    missing_storage = tmp_path / "typo-storage"

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "record-paper-shadow-outcome",
                "--storage-dir",
                str(missing_storage),
                "--leaderboard-entry-id",
                "leaderboard-entry:missing",
                "--window-start",
                "2026-04-28T13:00:00+00:00",
                "--window-end",
                "2026-04-29T13:00:00+00:00",
                "--observed-return",
                "0.05",
                "--benchmark-return",
                "0.01",
            ]
        )

    assert exc_info.value.code == 2
    assert not missing_storage.exists()
    assert "storage directory does not exist" in capsys.readouterr().err


def test_health_check_flags_paper_shadow_link_errors(tmp_path):
    repository = JsonFileRepository(tmp_path)
    outcome = PaperShadowOutcome(
        outcome_id="paper-shadow-outcome:broken",
        created_at=_now(),
        leaderboard_entry_id="leaderboard-entry:missing",
        evaluation_id="locked-evaluation:missing",
        strategy_card_id="strategy-card:missing",
        trial_id="experiment-trial:missing",
        symbol="BTC-USD",
        window_start=_now(),
        window_end=_now() + timedelta(hours=24),
        observed_return=0.01,
        benchmark_return=0.02,
        excess_return_after_costs=-0.01,
        max_adverse_excursion=None,
        turnover=None,
        outcome_grade="FAIL",
        failure_attributions=["negative_excess_return"],
        recommended_promotion_stage="PAPER_SHADOW_FAILED",
        recommended_strategy_action="RETIRE",
        blocked_reasons=[],
        notes=[],
        decision_basis="test",
    )
    repository.save_paper_shadow_outcome(outcome)
    health = run_health_check(storage_dir=tmp_path, symbol="BTC-USD", now=_now(), create_repair_request=False)
    codes = {finding.code for finding in health.findings}

    assert "paper_shadow_outcome_missing_leaderboard_entry" in codes
    assert "paper_shadow_outcome_missing_locked_evaluation" in codes
    assert "paper_shadow_outcome_missing_strategy_card" in codes
    assert "paper_shadow_outcome_missing_experiment_trial" in codes


def test_health_check_flags_paper_shadow_mismatched_existing_links(tmp_path):
    repository, card, trial, evaluation, entry = _seed_repository(tmp_path)
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
    outcome = PaperShadowOutcome(
        outcome_id="paper-shadow-outcome:mismatch",
        created_at=_now(),
        leaderboard_entry_id=entry.entry_id,
        evaluation_id=other_evaluation.evaluation_id,
        strategy_card_id=other_card.card_id,
        trial_id=other_trial.trial_id,
        symbol=entry.symbol,
        window_start=_now(),
        window_end=_now() + timedelta(hours=24),
        observed_return=0.05,
        benchmark_return=0.01,
        excess_return_after_costs=0.04,
        max_adverse_excursion=None,
        turnover=None,
        outcome_grade="PASS",
        failure_attributions=[],
        recommended_promotion_stage="PAPER_SHADOW_PASSED",
        recommended_strategy_action="PROMOTION_READY",
        blocked_reasons=[],
        notes=[],
        decision_basis="test",
    )
    repository.save_paper_shadow_outcome(outcome)
    second_outcome = PaperShadowOutcome(
        outcome_id="paper-shadow-outcome:evaluation-mismatch",
        created_at=_now(),
        leaderboard_entry_id=entry.entry_id,
        evaluation_id=evaluation.evaluation_id,
        strategy_card_id=other_card.card_id,
        trial_id=other_trial.trial_id,
        symbol=entry.symbol,
        window_start=_now(),
        window_end=_now() + timedelta(hours=24),
        observed_return=0.05,
        benchmark_return=0.01,
        excess_return_after_costs=0.04,
        max_adverse_excursion=None,
        turnover=None,
        outcome_grade="PASS",
        failure_attributions=[],
        recommended_promotion_stage="PAPER_SHADOW_PASSED",
        recommended_strategy_action="PROMOTION_READY",
        blocked_reasons=[],
        notes=[],
        decision_basis="test",
    )
    repository.save_paper_shadow_outcome(second_outcome)

    health = run_health_check(storage_dir=tmp_path, symbol="BTC-USD", now=_now(), create_repair_request=False)
    codes = {finding.code for finding in health.findings}

    assert "paper_shadow_outcome_leaderboard_evaluation_mismatch" in codes
    assert "paper_shadow_outcome_leaderboard_strategy_card_mismatch" in codes
    assert "paper_shadow_outcome_leaderboard_trial_mismatch" in codes
    assert "paper_shadow_outcome_evaluation_strategy_card_mismatch" in codes
    assert "paper_shadow_outcome_evaluation_trial_mismatch" in codes


def test_sqlite_repository_preserves_paper_shadow_outcomes(tmp_path):
    repository, _card, _trial, _evaluation, entry = _seed_repository(tmp_path)
    outcome = record_paper_shadow_outcome(
        repository=repository,
        created_at=_now(),
        leaderboard_entry_id=entry.entry_id,
        window_start=_now(),
        window_end=_now() + timedelta(hours=24),
        observed_return=0.05,
        benchmark_return=0.01,
    )
    sqlite_repo = SQLiteRepository(tmp_path)

    migrate_jsonl_to_sqlite(storage_dir=tmp_path, db_path=sqlite_repo.db_path)

    assert sqlite_repo.load_paper_shadow_outcomes() == [outcome]

    export_dir = tmp_path / "exported"
    export_sqlite_to_jsonl(storage_dir=tmp_path, output_dir=export_dir, db_path=sqlite_repo.db_path)

    assert JsonFileRepository(export_dir).load_paper_shadow_outcomes() == [outcome]
