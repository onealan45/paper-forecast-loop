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
    StrategyDecision,
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
        "revision": revision,
        "revision_outcome": revision_outcome,
        "autopilot": autopilot,
    }


def test_record_strategy_research_digest_persists_current_strategy_and_lineage_context(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    artifacts = _seed_strategy_research_chain(repository, now)
    decision = StrategyDecision(
        decision_id="decision:digest-blocker",
        created_at=now + timedelta(minutes=20),
        symbol="BTC-USD",
        horizon_hours=24,
        action="HOLD",
        confidence=0.51,
        evidence_grade="D",
        risk_level="MEDIUM",
        tradeable=False,
        blocked_reason="model_not_beating_baseline",
        recommended_position_pct=0.0,
        current_position_pct=0.0,
        max_position_pct=0.15,
        invalidation_conditions=["補齊 event edge 與 walk-forward 證據。"],
        reason_summary=(
            "模型證據沒有打贏 naive persistence baseline，因此買進/賣出被擋住。 "
            "主要研究阻擋：event edge 缺失、walk-forward overfit risk。"
        ),
        forecast_ids=["forecast:digest"],
        score_ids=["score:digest"],
        review_ids=["review:digest"],
        baseline_ids=["baseline:digest"],
        decision_basis="test",
    )
    repository.save_strategy_decision(decision)

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=30),
    )

    assert repository.load_strategy_research_digests() == [digest]
    assert digest.symbol == "BTC-USD"
    assert digest.strategy_card_id == artifacts["revision"].card_id
    assert digest.paper_shadow_outcome_id == artifacts["revision_outcome"].outcome_id
    assert digest.autopilot_run_id is None
    assert digest.strategy_status == "DRAFT"
    assert digest.outcome_grade == "FAIL"
    assert digest.recommended_strategy_action == "QUARANTINE_STRATEGY"
    assert digest.lineage_root_card_id == artifacts["card"].card_id
    assert digest.lineage_revision_count == 1
    assert digest.lineage_outcome_count == 2
    assert digest.lineage_primary_failure_attribution == "drawdown_breach"
    assert digest.top_failure_attributions == ["negative_excess_return", "drawdown_breach"]
    assert artifacts["outcome"].outcome_id in digest.evidence_artifact_ids
    assert artifacts["revision_outcome"].outcome_id in digest.evidence_artifact_ids
    assert "BTC breakout research" in digest.research_summary
    assert "paper-shadow" in digest.research_summary
    assert "回撤超標" in digest.next_step_rationale
    assert digest.decision_id == decision.decision_id
    assert digest.decision_action == "HOLD"
    assert digest.decision_blocked_reason == "model_not_beating_baseline"
    assert digest.decision_research_blockers == [
        "event edge 缺失",
        "walk-forward overfit risk",
    ]
    assert digest.decision_reason_summary == decision.reason_summary
    assert decision.decision_id in digest.evidence_artifact_ids
    assert digest.strategy_rule_summary == [
        "假說: Tighten risk controls after drawdown-heavy failed samples.",
        "訊號: Breakout with risk filter.",
        "進場: Require breakout and drawdown filter.",
        "出場: Exit when drawdown filter fails.",
        "風控: Quarantine if drawdown repeats.",
    ]


def test_strategy_research_digest_prefers_newer_retest_leaderboard_over_stale_autopilot_run(
    tmp_path,
):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    _seed_strategy_research_chain(repository, now)
    revision = StrategyCard(
        card_id="strategy-card:digest-active-retest",
        created_at=now + timedelta(minutes=20),
        strategy_name="BTC active retest strategy",
        strategy_family="breakout_reversal",
        version="v2",
        status="DRAFT",
        symbols=["BTC-USD"],
        hypothesis="A newer replacement strategy is in retest and must own the digest.",
        signal_description="Replacement retest signal.",
        entry_rules=["Enter only after retest evidence passes."],
        exit_rules=["Exit when retest invalidates."],
        risk_rules=["Wait for paper-shadow outcome before promotion."],
        parameters={"revision_source_outcome_id": "paper-shadow-outcome:digest-revision"},
        data_requirements=["market_candles:BTC-USD:1h"],
        feature_snapshot_ids=[],
        backtest_result_ids=["backtest-result:active-retest"],
        walk_forward_validation_ids=["walk-forward:active-retest"],
        event_edge_evaluation_ids=[],
        parent_card_id="strategy-card:digest-revision",
        author="codex-runtime",
        decision_basis="paper_shadow_strategy_revision_candidate",
    )
    trial = ExperimentTrial(
        trial_id="experiment-trial:active-retest",
        created_at=now + timedelta(minutes=21),
        strategy_card_id=revision.card_id,
        trial_index=1,
        status="PASSED",
        symbol="BTC-USD",
        seed=11,
        dataset_id="research-dataset:active-retest",
        backtest_result_id="backtest-result:active-retest",
        walk_forward_validation_id="walk-forward:active-retest",
        event_edge_evaluation_id=None,
        prompt_hash="prompt-active-retest",
        code_hash="code-active-retest",
        parameters={"revision_retest_protocol": "pr14-v1"},
        metric_summary={"alpha_score": None},
        failure_reason=None,
        started_at=now + timedelta(minutes=20),
        completed_at=now + timedelta(minutes=21),
        decision_basis="test",
    )
    evaluation = LockedEvaluationResult(
        evaluation_id="locked-evaluation:active-retest",
        created_at=now + timedelta(minutes=22),
        strategy_card_id=revision.card_id,
        trial_id=trial.trial_id,
        split_manifest_id="split-manifest:active-retest",
        cost_model_id="cost-model:active-retest",
        baseline_id="baseline:active-retest",
        backtest_result_id="backtest-result:active-retest",
        walk_forward_validation_id="walk-forward:active-retest",
        event_edge_evaluation_id=None,
        passed=False,
        rankable=False,
        alpha_score=None,
        blocked_reasons=["leaderboard_entry_not_rankable"],
        gate_metrics={"holdout_excess_return": -0.01},
        decision_basis="test",
    )
    leaderboard = LeaderboardEntry(
        entry_id="leaderboard-entry:active-retest",
        created_at=now + timedelta(minutes=22),
        strategy_card_id=revision.card_id,
        evaluation_id=evaluation.evaluation_id,
        trial_id=trial.trial_id,
        symbol="BTC-USD",
        rankable=False,
        alpha_score=None,
        promotion_stage="BLOCKED",
        blocked_reasons=["leaderboard_entry_not_rankable"],
        leaderboard_rules_version="pr7-v1",
        decision_basis="test",
    )
    repository.save_strategy_card(revision)
    repository.save_experiment_trial(trial)
    repository.save_locked_evaluation_result(evaluation)
    repository.save_leaderboard_entry(leaderboard)

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=24),
    )

    assert digest.strategy_card_id == revision.card_id
    assert digest.paper_shadow_outcome_id is None
    assert evaluation.evaluation_id in digest.evidence_artifact_ids
    assert leaderboard.entry_id in digest.evidence_artifact_ids
    assert digest.autopilot_run_id is None
    assert "BTC active retest strategy" in digest.research_summary
    assert digest.next_research_action == "WAIT_FOR_PAPER_SHADOW_OUTCOME"
    assert "等待 paper-shadow 視窗" in digest.research_summary
    assert "尚未有 paper-shadow 結果" in digest.research_summary
    assert digest.next_step_rationale == (
        "已有 leaderboard entry，但尚未有 post-entry paper-shadow observation；"
        "等待下一個完整觀察視窗，不捏造未來報酬。"
    )
    assert digest.strategy_rule_summary == [
        "假說: A newer replacement strategy is in retest and must own the digest.",
        "訊號: Replacement retest signal.",
        "進場: Enter only after retest evidence passes.",
        "出場: Exit when retest invalidates.",
        "風控: Wait for paper-shadow outcome before promotion.",
    ]


def test_strategy_research_digest_compacts_long_rule_summary_text(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 2, 8, 0, tzinfo=UTC)
    repository.save_strategy_card(
        StrategyCard(
            card_id="strategy-card:long-summary",
            created_at=now,
            strategy_name="BTC long summary strategy",
            strategy_family="breakout_reversal",
            version="v1",
            status="DRAFT",
            symbols=["BTC-USD"],
            hypothesis=(
                "First concise research hypothesis should own the digest summary. "
                "Do not force the digest panel to display every failure key such as "
                "leaderboard_entry_not_rankable, baseline_edge_not_positive, "
                "walk_forward_excess_not_positive, locked_evaluation_not_rankable, "
                "and turnover_limit_exceeded."
            ),
            signal_description="Use independent confirmation instead of repeating the failed trigger.",
            entry_rules=["Enter only after independent confirmation and positive baseline edge."],
            exit_rules=["Exit when baseline edge turns negative."],
            risk_rules=["Keep max exposure capped while the replacement stays in DRAFT."],
            parameters={},
            data_requirements=["market_candles:BTC-USD:1h"],
            feature_snapshot_ids=[],
            backtest_result_ids=[],
            walk_forward_validation_ids=[],
            event_edge_evaluation_ids=[],
            parent_card_id=None,
            author="codex",
            decision_basis="test",
        )
    )

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=1),
    )

    assert digest.strategy_rule_summary[0] == (
        "假說: First concise research hypothesis should own the digest summary."
    )
    assert "leaderboard_entry_not_rankable" not in digest.strategy_rule_summary[0]
    assert all(len(item) <= 180 for item in digest.strategy_rule_summary)


def test_strategy_research_digest_truncates_long_rule_text_without_sentence_boundary(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    repository.save_strategy_card(
        StrategyCard(
            card_id="strategy-card:no-boundary-summary",
            created_at=now,
            strategy_name="BTC no boundary summary strategy",
            strategy_family="breakout_reversal",
            version="v1",
            status="DRAFT",
            symbols=["BTC-USD"],
            hypothesis="NoBoundaryHypothesis" * 20,
            signal_description="Use compact deterministic fallback truncation.",
            entry_rules=["Enter only after deterministic fallback stays readable."],
            exit_rules=["Exit when deterministic fallback fails readability."],
            risk_rules=["Keep the rule summary bounded."],
            parameters={},
            data_requirements=["market_candles:BTC-USD:1h"],
            feature_snapshot_ids=[],
            backtest_result_ids=[],
            walk_forward_validation_ids=[],
            event_edge_evaluation_ids=[],
            parent_card_id=None,
            author="codex",
            decision_basis="test",
        )
    )

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=1),
    )

    assert digest.strategy_rule_summary[0].startswith("假說: NoBoundaryHypothesis")
    assert digest.strategy_rule_summary[0].endswith("...")
    assert len(digest.strategy_rule_summary[0]) <= 180


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
    assert result["strategy_research_digest"]["next_research_action"] == "QUARANTINE_STRATEGY"


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
    assert saved[0].strategy_card_id == artifacts["revision"].card_id
    assert saved[0].autopilot_run_id is None


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
