from datetime import UTC, datetime, timedelta
import json

from forecast_loop.cli import main
from forecast_loop.models import (
    ExperimentTrial,
    LeaderboardEntry,
    LockedEvaluationResult,
    PaperShadowOutcome,
    ResearchAgenda,
    ResearchAutopilotRun,
    StrategyCard,
    StrategyResearchDigest,
)
from forecast_loop.sqlite_repository import SQLiteRepository
from forecast_loop.storage import JsonFileRepository
from forecast_loop.strategy_research_digest import record_strategy_research_digest


def _seed_strategy_research_chain(repository, now: datetime) -> dict:
    card = StrategyCard(
        card_id="strategy-card:digest-root",
        created_at=now,
        strategy_name="BTC breakout research",
        strategy_family="breakout_reversal",
        version="v1",
        status="ACTIVE",
        symbols=["BTC-USD"],
        hypothesis="Breakout with volume confirmation can beat the BTC persistence baseline.",
        signal_description="Breakout after volume expansion.",
        entry_rules=["Break prior high after volume expansion."],
        exit_rules=["Exit when breakout fails."],
        risk_rules=["Revise after failed paper-shadow result."],
        parameters={"lookback_hours": 24},
        data_requirements=["market_candles:BTC-USD:1h"],
        feature_snapshot_ids=[],
        backtest_result_ids=["backtest-result:digest-root"],
        walk_forward_validation_ids=["walk-forward:digest-root"],
        event_edge_evaluation_ids=[],
        parent_card_id=None,
        author="codex",
        decision_basis="test",
    )
    trial = ExperimentTrial(
        trial_id="experiment-trial:digest-root",
        created_at=now,
        strategy_card_id=card.card_id,
        trial_index=1,
        status="PASSED",
        symbol="BTC-USD",
        seed=7,
        dataset_id="research-dataset:digest-root",
        backtest_result_id="backtest-result:digest-root",
        walk_forward_validation_id="walk-forward:digest-root",
        event_edge_evaluation_id=None,
        prompt_hash="prompt-digest",
        code_hash="code-digest",
        parameters={"lookback_hours": 24},
        metric_summary={"alpha_score": 0.18},
        failure_reason=None,
        started_at=now,
        completed_at=now,
        decision_basis="test",
    )
    evaluation = LockedEvaluationResult(
        evaluation_id="locked-evaluation:digest-root",
        created_at=now,
        strategy_card_id=card.card_id,
        trial_id=trial.trial_id,
        split_manifest_id="split-manifest:digest-root",
        cost_model_id="cost-model:digest-root",
        baseline_id="baseline:digest-root",
        backtest_result_id="backtest-result:digest-root",
        walk_forward_validation_id="walk-forward:digest-root",
        event_edge_evaluation_id=None,
        passed=True,
        rankable=True,
        alpha_score=0.18,
        blocked_reasons=[],
        gate_metrics={"holdout_excess_return": 0.03},
        decision_basis="test",
    )
    leaderboard = LeaderboardEntry(
        entry_id="leaderboard-entry:digest-root",
        created_at=now,
        strategy_card_id=card.card_id,
        evaluation_id=evaluation.evaluation_id,
        trial_id=trial.trial_id,
        symbol="BTC-USD",
        rankable=True,
        alpha_score=0.18,
        promotion_stage="CANDIDATE",
        blocked_reasons=[],
        leaderboard_rules_version="pr7-v1",
        decision_basis="test",
    )
    outcome = PaperShadowOutcome(
        outcome_id="paper-shadow-outcome:digest-root",
        created_at=now,
        leaderboard_entry_id=leaderboard.entry_id,
        evaluation_id=evaluation.evaluation_id,
        strategy_card_id=card.card_id,
        trial_id=trial.trial_id,
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
    agenda = ResearchAgenda(
        agenda_id="research-agenda:digest-root",
        created_at=now,
        symbol="BTC-USD",
        title="Repair BTC breakout edge",
        hypothesis="Revise the breakout hypothesis after the failed shadow sample.",
        priority="HIGH",
        status="OPEN",
        target_strategy_family="breakout_reversal",
        strategy_card_ids=[card.card_id],
        expected_artifacts=["strategy_card", "paper_shadow_outcome"],
        acceptance_criteria=["Next revision must improve after-cost edge."],
        blocked_actions=["promote_without_retest"],
        decision_basis="test",
    )
    autopilot = ResearchAutopilotRun(
        run_id="research-autopilot-run:digest-root",
        created_at=now,
        symbol="BTC-USD",
        agenda_id=agenda.agenda_id,
        strategy_card_id=card.card_id,
        experiment_trial_id=trial.trial_id,
        locked_evaluation_id=evaluation.evaluation_id,
        leaderboard_entry_id=leaderboard.entry_id,
        strategy_decision_id=None,
        paper_shadow_outcome_id=outcome.outcome_id,
        steps=[{"name": "paper_shadow", "status": "failed", "artifact_id": outcome.outcome_id}],
        loop_status="REVISION_REQUIRED",
        next_research_action="REVISE_STRATEGY",
        blocked_reasons=["paper_shadow_failed"],
        decision_basis="test",
    )
    revision = StrategyCard(
        card_id="strategy-card:digest-revision",
        created_at=now + timedelta(minutes=5),
        strategy_name="BTC breakout research revision",
        strategy_family="breakout_reversal",
        version="v1.rev1",
        status="DRAFT",
        symbols=["BTC-USD"],
        hypothesis="Tighten risk controls after drawdown-heavy failed samples.",
        signal_description="Breakout with risk filter.",
        entry_rules=["Require breakout and drawdown filter."],
        exit_rules=["Exit when drawdown filter fails."],
        risk_rules=["Quarantine if drawdown repeats."],
        parameters={
            "revision_source_outcome_id": outcome.outcome_id,
            "revision_failure_attributions": ["negative_excess_return"],
        },
        data_requirements=["market_candles:BTC-USD:1h"],
        feature_snapshot_ids=[],
        backtest_result_ids=[],
        walk_forward_validation_ids=[],
        event_edge_evaluation_ids=[],
        parent_card_id=card.card_id,
        author="codex-strategy-evolution",
        decision_basis="paper_shadow_strategy_revision_candidate",
    )
    revision_outcome = PaperShadowOutcome(
        outcome_id="paper-shadow-outcome:digest-revision",
        created_at=now + timedelta(minutes=10),
        leaderboard_entry_id="leaderboard-entry:digest-revision",
        evaluation_id="locked-evaluation:digest-revision",
        strategy_card_id=revision.card_id,
        trial_id="experiment-trial:digest-revision",
        symbol="BTC-USD",
        window_start=now - timedelta(hours=24),
        window_end=now,
        observed_return=-0.05,
        benchmark_return=0.01,
        excess_return_after_costs=-0.08,
        max_adverse_excursion=0.12,
        turnover=1.9,
        outcome_grade="FAIL",
        failure_attributions=["drawdown_breach", "negative_excess_return"],
        recommended_promotion_stage="PAPER_SHADOW_FAILED",
        recommended_strategy_action="QUARANTINE_STRATEGY",
        blocked_reasons=["paper_shadow_failed", "drawdown_breach"],
        notes=["Revision failed the next shadow window."],
        decision_basis="test",
    )

    repository.save_strategy_card(card)
    repository.save_experiment_trial(trial)
    repository.save_locked_evaluation_result(evaluation)
    repository.save_leaderboard_entry(leaderboard)
    repository.save_paper_shadow_outcome(outcome)
    repository.save_research_agenda(agenda)
    repository.save_research_autopilot_run(autopilot)
    repository.save_strategy_card(revision)
    repository.save_paper_shadow_outcome(revision_outcome)
    return {
        "card": card,
        "outcome": outcome,
        "revision_outcome": revision_outcome,
        "autopilot": autopilot,
    }


def test_record_strategy_research_digest_persists_current_strategy_and_lineage_context(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    artifacts = _seed_strategy_research_chain(repository, now)

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=30),
    )

    assert repository.load_strategy_research_digests() == [digest]
    assert digest.symbol == "BTC-USD"
    assert digest.strategy_card_id == artifacts["card"].card_id
    assert digest.paper_shadow_outcome_id == artifacts["outcome"].outcome_id
    assert digest.autopilot_run_id == artifacts["autopilot"].run_id
    assert digest.strategy_status == "ACTIVE"
    assert digest.outcome_grade == "FAIL"
    assert digest.recommended_strategy_action == "REVISE_STRATEGY"
    assert digest.lineage_root_card_id == artifacts["card"].card_id
    assert digest.lineage_revision_count == 1
    assert digest.lineage_outcome_count == 2
    assert digest.lineage_primary_failure_attribution == "drawdown_breach"
    assert digest.top_failure_attributions == ["negative_excess_return", "drawdown_breach"]
    assert artifacts["revision_outcome"].outcome_id in digest.evidence_artifact_ids
    assert "BTC breakout research" in digest.research_summary
    assert "paper-shadow" in digest.research_summary
    assert "回撤超標" in digest.next_step_rationale


def test_strategy_research_digest_cli_writes_digest_artifact(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    _seed_strategy_research_chain(repository, now)

    assert main(
        [
            "strategy-research-digest",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--created-at",
            "2026-05-01T08:30:00+00:00",
        ]
    ) == 0
    result = json.loads(capsys.readouterr().out)

    saved = repository.load_strategy_research_digests()
    assert len(saved) == 1
    assert result["strategy_research_digest"]["digest_id"] == saved[0].digest_id
    assert result["strategy_research_digest"]["symbol"] == "BTC-USD"
    assert result["strategy_research_digest"]["next_research_action"] == "REVISE_STRATEGY"


def test_run_once_also_decide_refreshes_strategy_research_digest_when_research_artifacts_exist(
    tmp_path, capsys
):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    artifacts = _seed_strategy_research_chain(repository, now)

    assert (
        main(
            [
                "run-once",
                "--provider",
                "sample",
                "--symbol",
                "BTC-USD",
                "--storage-dir",
                str(tmp_path),
                "--now",
                "2026-05-01T08:30:00+00:00",
                "--also-decide",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)

    saved = repository.load_strategy_research_digests()
    assert len(saved) == 1
    assert result["strategy_research_digest_id"] == saved[0].digest_id
    assert saved[0].strategy_card_id == artifacts["card"].card_id
    assert saved[0].autopilot_run_id == artifacts["autopilot"].run_id


def test_run_once_also_decide_skips_strategy_research_digest_without_research_artifacts(
    tmp_path, capsys
):
    repository = JsonFileRepository(tmp_path)

    assert (
        main(
            [
                "run-once",
                "--provider",
                "sample",
                "--symbol",
                "BTC-USD",
                "--storage-dir",
                str(tmp_path),
                "--now",
                "2026-05-01T08:30:00+00:00",
                "--also-decide",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)

    assert result["strategy_research_digest_id"] is None
    assert repository.load_strategy_research_digests() == []


def test_strategy_research_digest_round_trips_through_sqlite_repository(tmp_path):
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    digest = StrategyResearchDigest(
        digest_id="strategy-research-digest:sqlite",
        created_at=now,
        symbol="BTC-USD",
        strategy_card_id="strategy-card:sqlite",
        strategy_name="SQLite digest strategy",
        strategy_status="ACTIVE",
        hypothesis="Persist strategy research digest through SQLite.",
        paper_shadow_outcome_id="paper-shadow-outcome:sqlite",
        outcome_grade="FAIL",
        excess_return_after_costs=-0.02,
        recommended_strategy_action="REVISE_STRATEGY",
        top_failure_attributions=["negative_excess_return"],
        lineage_root_card_id="strategy-card:sqlite",
        lineage_revision_count=1,
        lineage_outcome_count=2,
        lineage_primary_failure_attribution="negative_excess_return",
        lineage_next_research_focus="Revise weak edge.",
        next_research_action="REVISE_STRATEGY",
        autopilot_run_id="research-autopilot-run:sqlite",
        evidence_artifact_ids=["strategy-card:sqlite", "paper-shadow-outcome:sqlite"],
        research_summary="目前策略 SQLite digest strategy：paper-shadow 失敗。",
        next_step_rationale="下一步修訂策略。",
        decision_basis="test",
    )
    repository = SQLiteRepository(tmp_path)

    repository.save_strategy_research_digest(digest)
    repository.save_strategy_research_digest(digest)

    assert repository.load_strategy_research_digests() == [digest]
    assert repository.artifact_counts()["strategy_research_digests"] == 1


def test_strategy_research_digest_migrates_to_sqlite_and_exports_back_to_jsonl(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    _seed_strategy_research_chain(repository, now)
    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=30),
    )
    export_dir = tmp_path / "export"

    assert main(["migrate-jsonl-to-sqlite", "--storage-dir", str(tmp_path)]) == 0
    migrate_result = json.loads(capsys.readouterr().out)
    assert migrate_result["inserted_counts"]["strategy_research_digests"] == 1

    sqlite_repository = SQLiteRepository(tmp_path, initialize=False)
    assert sqlite_repository.load_strategy_research_digests() == [digest]

    assert main(["export-jsonl", "--storage-dir", str(tmp_path), "--output-dir", str(export_dir)]) == 0
    capsys.readouterr()
    exported_repository = JsonFileRepository(export_dir)
    assert exported_repository.load_strategy_research_digests() == [digest]
