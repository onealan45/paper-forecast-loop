import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from forecast_loop.cli import main
from forecast_loop.evaluation import build_evaluation_summary
from forecast_loop.lineage_agenda import create_lineage_research_agenda
from forecast_loop.lineage_research_run_log import record_lineage_research_task_run
from forecast_loop.models import (
    AutomationRun,
    BaselineEvaluation,
    BrokerOrder,
    BrokerReconciliation,
    SplitManifest,
    ExecutionSafetyGate,
    ExperimentTrial,
    Forecast,
    ForecastScore,
    LeaderboardEntry,
    LockedEvaluationResult,
    PaperFill,
    PaperOrder,
    PaperPortfolioSnapshot,
    PaperPosition,
    PaperShadowOutcome,
    Proposal,
    ResearchAgenda,
    ResearchAutopilotRun,
    Review,
    RiskSnapshot,
    StrategyCard,
    StrategyDecision,
)
from forecast_loop.storage import JsonFileRepository


def _write_meta(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_automation(codex_home: Path, automation_id: str, *, status: str, updated_at: int = 1777030175608) -> None:
    automation_dir = codex_home / "automations" / automation_id
    automation_dir.mkdir(parents=True)
    (automation_dir / "automation.toml").write_text(
        "\n".join(
            [
                "version = 1",
                f'id = "{automation_id}"',
                'kind = "heartbeat"',
                f'name = "{automation_id}"',
                'prompt = "test"',
                f'status = "{status}"',
                'rrule = "FREQ=HOURLY;INTERVAL=1"',
                'target_thread_id = "test-thread"',
                "created_at = 1776961384325",
                f"updated_at = {updated_at}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _seed_dashboard_strategy_research(repository: JsonFileRepository, now: datetime) -> None:
    card = StrategyCard(
        card_id="strategy-card:dashboard-visible",
        created_at=now,
        strategy_name="Dashboard BTC breakout candidate",
        strategy_family="breakout_reversal",
        version="v2",
        status="ACTIVE",
        symbols=["BTC-USD"],
        hypothesis="Dashboard should show concrete strategy logic before raw metadata.",
        signal_description="Breakout with volume confirmation.",
        entry_rules=["突破前高且成交量放大"],
        exit_rules=["跌回突破區間"],
        risk_rules=["paper-shadow fail -> revise"],
        parameters={"lookback_hours": 24, "volume_multiplier": 1.5},
        data_requirements=["market_candles:BTC-USD:1h"],
        feature_snapshot_ids=[],
        backtest_result_ids=["backtest-result:dashboard-visible"],
        walk_forward_validation_ids=["walk-forward:dashboard-visible"],
        event_edge_evaluation_ids=[],
        parent_card_id=None,
        author="codex",
        decision_basis="test",
    )
    trial = ExperimentTrial(
        trial_id="experiment-trial:dashboard-visible",
        created_at=now,
        strategy_card_id=card.card_id,
        trial_index=2,
        status="PASSED",
        symbol="BTC-USD",
        seed=7,
        dataset_id="research-dataset:dashboard-visible",
        backtest_result_id="backtest-result:dashboard-visible",
        walk_forward_validation_id="walk-forward:dashboard-visible",
        event_edge_evaluation_id=None,
        prompt_hash="prompt-dashboard",
        code_hash="code-dashboard",
        parameters={"lookback_hours": 24, "volume_multiplier": 1.5},
        metric_summary={"alpha_score": 0.21},
        failure_reason=None,
        started_at=now,
        completed_at=now,
        decision_basis="test",
    )
    evaluation = LockedEvaluationResult(
        evaluation_id="locked-evaluation:dashboard-visible",
        created_at=now,
        strategy_card_id=card.card_id,
        trial_id=trial.trial_id,
        split_manifest_id="split-manifest:dashboard-visible",
        cost_model_id="cost-model:dashboard-visible",
        baseline_id="baseline:dashboard-visible",
        backtest_result_id="backtest-result:dashboard-visible",
        walk_forward_validation_id="walk-forward:dashboard-visible",
        event_edge_evaluation_id=None,
        passed=True,
        rankable=True,
        alpha_score=0.21,
        blocked_reasons=[],
        gate_metrics={"alpha_score": 0.21, "holdout_excess_return": 0.04},
        decision_basis="test",
    )
    leaderboard = LeaderboardEntry(
        entry_id="leaderboard-entry:dashboard-visible",
        created_at=now,
        strategy_card_id=card.card_id,
        evaluation_id=evaluation.evaluation_id,
        trial_id=trial.trial_id,
        symbol="BTC-USD",
        rankable=True,
        alpha_score=0.21,
        promotion_stage="CANDIDATE",
        blocked_reasons=[],
        leaderboard_rules_version="pr7-v1",
        decision_basis="test",
    )
    outcome = PaperShadowOutcome(
        outcome_id="paper-shadow-outcome:dashboard-visible",
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
        agenda_id="research-agenda:dashboard-visible",
        created_at=now,
        symbol="BTC-USD",
        title="Dashboard strategy visibility",
        hypothesis="Strategy UX should expose the current research hypothesis.",
        priority="HIGH",
        status="OPEN",
        target_strategy_family="breakout_reversal",
        strategy_card_ids=[card.card_id],
        expected_artifacts=["strategy_card", "leaderboard", "paper_shadow_outcome"],
        acceptance_criteria=["Dashboard shows concrete strategy context."],
        blocked_actions=["promote_to_live"],
        decision_basis="test",
    )
    autopilot = ResearchAutopilotRun(
        run_id="research-autopilot-run:dashboard-visible",
        created_at=now,
        symbol="BTC-USD",
        agenda_id=agenda.agenda_id,
        strategy_card_id=card.card_id,
        experiment_trial_id=trial.trial_id,
        locked_evaluation_id=evaluation.evaluation_id,
        leaderboard_entry_id=leaderboard.entry_id,
        strategy_decision_id=None,
        paper_shadow_outcome_id=outcome.outcome_id,
        steps=[{"name": "shadow", "status": "failed", "artifact_id": outcome.outcome_id}],
        loop_status="REVISION_REQUIRED",
        next_research_action="REVISE_STRATEGY",
        blocked_reasons=["paper_shadow_failed"],
        decision_basis="test",
    )
    repository.save_strategy_card(card)
    repository.save_experiment_trial(trial)
    repository.save_locked_evaluation_result(evaluation)
    repository.save_leaderboard_entry(leaderboard)
    repository.save_paper_shadow_outcome(outcome)
    repository.save_research_agenda(agenda)
    repository.save_research_autopilot_run(autopilot)


def _seed_dashboard_revision_candidate(repository: JsonFileRepository, now: datetime) -> None:
    revision = StrategyCard(
        card_id="strategy-card:dashboard-revision",
        created_at=now,
        strategy_name="Dashboard BTC breakout candidate revision",
        strategy_family="breakout_reversal",
        version="v2.rev1",
        status="DRAFT",
        symbols=["BTC-USD"],
        hypothesis="Revision should repair negative_excess_return from the failed paper-shadow window.",
        signal_description="Revision adds baseline-edge confirmation before the breakout entry.",
        entry_rules=[
            "突破前高且成交量放大",
            "Require positive after-cost edge versus the active baseline suite before simulated entry.",
        ],
        exit_rules=["跌回突破區間"],
        risk_rules=["Block promotion until the revised card beats no-trade and persistence baselines."],
        parameters={
            "revision_source_outcome_id": "paper-shadow-outcome:dashboard-visible",
            "revision_failure_attributions": ["negative_excess_return"],
            "minimum_after_cost_edge": 0.01,
        },
        data_requirements=["market_candles:BTC-USD:1h"],
        feature_snapshot_ids=[],
        backtest_result_ids=[],
        walk_forward_validation_ids=[],
        event_edge_evaluation_ids=[],
        parent_card_id="strategy-card:dashboard-visible",
        author="codex-strategy-evolution",
        decision_basis="paper_shadow_strategy_revision_candidate",
    )
    agenda = ResearchAgenda(
        agenda_id="research-agenda:dashboard-revision",
        created_at=now,
        symbol="BTC-USD",
        title="Revision test for Dashboard BTC breakout candidate",
        hypothesis="Retest the DRAFT revision against the negative_excess_return attribution.",
        priority="HIGH",
        status="OPEN",
        target_strategy_family="breakout_reversal",
        strategy_card_ids=[revision.card_id],
        expected_artifacts=["strategy_card", "locked_evaluation", "paper_shadow_outcome"],
        acceptance_criteria=["revision card stays DRAFT until new locked evaluation passes"],
        blocked_actions=["automatic_promotion_without_retest"],
        decision_basis="paper_shadow_strategy_revision_agenda",
    )
    repository.save_strategy_card(revision)
    repository.save_research_agenda(agenda)


def _seed_dashboard_revision_retest_scaffold(repository: JsonFileRepository, now: datetime) -> None:
    trial = ExperimentTrial(
        trial_id="experiment-trial:dashboard-revision-retest",
        created_at=now,
        strategy_card_id="strategy-card:dashboard-revision",
        trial_index=1,
        status="PENDING",
        symbol="BTC-USD",
        seed=7,
        dataset_id="research-dataset:dashboard-revision-retest",
        backtest_result_id=None,
        walk_forward_validation_id=None,
        event_edge_evaluation_id=None,
        prompt_hash=None,
        code_hash=None,
        parameters={
            "revision_retest_protocol": "pr14-v1",
            "revision_retest_source_card_id": "strategy-card:dashboard-revision",
            "revision_source_outcome_id": "paper-shadow-outcome:dashboard-visible",
            "revision_parent_card_id": "strategy-card:dashboard-visible",
        },
        metric_summary={},
        failure_reason=None,
        started_at=now,
        completed_at=None,
        decision_basis="revision_retest_scaffold",
    )
    split = SplitManifest(
        manifest_id="split-manifest:dashboard-revision-retest",
        created_at=now,
        symbol="BTC-USD",
        strategy_card_id="strategy-card:dashboard-revision",
        dataset_id="research-dataset:dashboard-revision-retest",
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
    repository.save_experiment_trial(trial)
    repository.save_split_manifest(split)


def _seed_dashboard_revision_retest_autopilot_run(repository: JsonFileRepository, now: datetime) -> None:
    repository.save_research_autopilot_run(
        ResearchAutopilotRun(
            run_id="research-autopilot-run:dashboard-revision-retest",
            created_at=now,
            symbol="BTC-USD",
            agenda_id="research-agenda:dashboard-revision",
            strategy_card_id="strategy-card:dashboard-revision",
            experiment_trial_id="experiment-trial:dashboard-revision-retest",
            locked_evaluation_id="locked-evaluation:dashboard-revision-retest",
            leaderboard_entry_id="leaderboard-entry:dashboard-revision-retest",
            strategy_decision_id=None,
            paper_shadow_outcome_id="paper-shadow-outcome:dashboard-revision-retest",
            steps=[
                {"name": "revision_card", "status": "completed", "artifact_id": "strategy-card:dashboard-revision"},
                {"name": "paper_shadow_outcome", "status": "completed", "artifact_id": "paper-shadow-outcome:dashboard-revision-retest"},
            ],
            loop_status="BLOCKED",
            next_research_action="REPAIR_EVIDENCE_CHAIN",
            blocked_reasons=["locked_evaluation_not_rankable"],
            decision_basis="research_paper_autopilot_loop",
        )
    )


def _seed_dashboard_strategy_lineage(repository: JsonFileRepository, now: datetime) -> None:
    revision_outcome = PaperShadowOutcome(
        outcome_id="paper-shadow-outcome:dashboard-revision-quarantine",
        created_at=now,
        leaderboard_entry_id="leaderboard-entry:dashboard-revision-retest",
        evaluation_id="locked-evaluation:dashboard-revision-retest",
        strategy_card_id="strategy-card:dashboard-revision",
        trial_id="experiment-trial:dashboard-revision-retest",
        symbol="BTC-USD",
        window_start=now - timedelta(hours=24),
        window_end=now,
        observed_return=-0.05,
        benchmark_return=0.01,
        excess_return_after_costs=-0.08,
        max_adverse_excursion=0.12,
        turnover=1.9,
        outcome_grade="FAIL",
        failure_attributions=["negative_excess_return", "drawdown_breach"],
        recommended_promotion_stage="PAPER_SHADOW_FAILED",
        recommended_strategy_action="QUARANTINE_STRATEGY",
        blocked_reasons=["paper_shadow_failed", "drawdown_breach"],
        notes=["Revision failed the second shadow window."],
        decision_basis="test",
    )
    repository.save_paper_shadow_outcome(revision_outcome)


def _seed_dashboard_second_generation_strategy_lineage(repository: JsonFileRepository, now: datetime) -> None:
    second_revision = StrategyCard(
        card_id="strategy-card:dashboard-second-revision",
        created_at=now,
        strategy_name="Dashboard BTC breakout candidate second revision",
        strategy_family="breakout_reversal",
        version="v2.rev2",
        status="DRAFT",
        symbols=["BTC-USD"],
        hypothesis="Second revision should inherit the original strategy lineage.",
        signal_description="Second revision tightens risk after the first revised shadow failed.",
        entry_rules=["突破前高且成交量放大", "Require second-generation risk confirmation."],
        exit_rules=["跌回突破區間", "Stop when second-generation drawdown guard triggers."],
        risk_rules=["Block promotion until recursive lineage shows repaired failure attributions."],
        parameters={
            "revision_source_outcome_id": "paper-shadow-outcome:dashboard-revision-quarantine",
            "revision_failure_attributions": ["drawdown_breach", "weak_baseline_edge"],
            "minimum_after_cost_edge": 0.015,
        },
        data_requirements=["market_candles:BTC-USD:1h"],
        feature_snapshot_ids=[],
        backtest_result_ids=[],
        walk_forward_validation_ids=[],
        event_edge_evaluation_ids=[],
        parent_card_id="strategy-card:dashboard-revision",
        author="codex-strategy-evolution",
        decision_basis="paper_shadow_strategy_revision_candidate",
    )
    second_outcome = PaperShadowOutcome(
        outcome_id="paper-shadow-outcome:dashboard-second-revision-quarantine",
        created_at=now,
        leaderboard_entry_id="leaderboard-entry:dashboard-second-revision-retest",
        evaluation_id="locked-evaluation:dashboard-second-revision-retest",
        strategy_card_id=second_revision.card_id,
        trial_id="experiment-trial:dashboard-second-revision-retest",
        symbol="BTC-USD",
        window_start=now - timedelta(hours=24),
        window_end=now,
        observed_return=-0.08,
        benchmark_return=0.02,
        excess_return_after_costs=-0.11,
        max_adverse_excursion=0.18,
        turnover=2.1,
        outcome_grade="FAIL",
        failure_attributions=["drawdown_breach", "weak_baseline_edge"],
        recommended_promotion_stage="PAPER_SHADOW_FAILED",
        recommended_strategy_action="QUARANTINE_STRATEGY",
        blocked_reasons=["paper_shadow_failed", "weak_baseline_edge"],
        notes=["Second-generation revision still failed paper shadow."],
        decision_basis="test",
    )
    repository.save_strategy_card(second_revision)
    repository.save_paper_shadow_outcome(second_outcome)


def _seed_dashboard_malicious_strategy_lineage(repository: JsonFileRepository, now: datetime) -> None:
    revision = StrategyCard(
        card_id="strategy-card:dashboard-malicious-revision",
        created_at=now,
        strategy_name='Dashboard <script>alert("name")</script> revision',
        strategy_family="breakout_reversal",
        version="v2.rev-xss",
        status="DRAFT",
        symbols=["BTC-USD"],
        hypothesis='Repair hypothesis <script>alert("hypothesis")</script>',
        signal_description="Malicious display fixture.",
        entry_rules=[],
        exit_rules=[],
        risk_rules=[],
        parameters={
            "revision_source_outcome_id": 'paper-shadow-outcome:<script>alert("source")</script>',
            "revision_failure_attributions": ['drawdown_breach<script>alert("fix")</script>'],
        },
        data_requirements=["market_candles:BTC-USD:1h"],
        feature_snapshot_ids=[],
        backtest_result_ids=[],
        walk_forward_validation_ids=[],
        event_edge_evaluation_ids=[],
        parent_card_id="strategy-card:dashboard-visible",
        author="codex-strategy-evolution",
        decision_basis="paper_shadow_strategy_revision_candidate",
    )
    repository.save_strategy_card(revision)


def _seed_dashboard_distractor_strategy_research_without_run(
    repository: JsonFileRepository,
    now: datetime,
) -> None:
    card = StrategyCard(
        card_id="strategy-card:dashboard-distractor",
        created_at=now,
        strategy_name="Dashboard distractor strategy",
        strategy_family="mean_reversion",
        version="v9",
        status="ACTIVE",
        symbols=["BTC-USD"],
        hypothesis="Dashboard distractor must not be mixed into the visible autopilot chain.",
        signal_description="Distractor signal.",
        entry_rules=["distractor_entry_rule"],
        exit_rules=["distractor_exit_rule"],
        risk_rules=["distractor_risk_rule"],
        parameters={"distractor": True},
        data_requirements=["distractor_source"],
        feature_snapshot_ids=[],
        backtest_result_ids=[],
        walk_forward_validation_ids=[],
        event_edge_evaluation_ids=[],
        parent_card_id=None,
        author="codex",
        decision_basis="test",
    )
    trial = ExperimentTrial(
        trial_id="experiment-trial:dashboard-distractor",
        created_at=now,
        strategy_card_id=card.card_id,
        trial_index=99,
        status="PASSED",
        symbol="BTC-USD",
        seed=999,
        dataset_id="research-dataset:dashboard-distractor",
        backtest_result_id="backtest-result:dashboard-distractor",
        walk_forward_validation_id="walk-forward:dashboard-distractor",
        event_edge_evaluation_id=None,
        prompt_hash="prompt-dashboard-distractor",
        code_hash="code-dashboard-distractor",
        parameters={"distractor": True},
        metric_summary={"alpha_score": 0.99},
        failure_reason=None,
        started_at=now,
        completed_at=now,
        decision_basis="test",
    )
    evaluation = LockedEvaluationResult(
        evaluation_id="locked-evaluation:dashboard-distractor",
        created_at=now,
        strategy_card_id=card.card_id,
        trial_id=trial.trial_id,
        split_manifest_id="split-manifest:dashboard-distractor",
        cost_model_id="cost-model:dashboard-distractor",
        baseline_id="baseline:dashboard-distractor",
        backtest_result_id="backtest-result:dashboard-distractor",
        walk_forward_validation_id="walk-forward:dashboard-distractor",
        event_edge_evaluation_id=None,
        passed=True,
        rankable=True,
        alpha_score=0.99,
        blocked_reasons=[],
        gate_metrics={"alpha_score": 0.99, "distractor_metric": 1},
        decision_basis="test",
    )
    leaderboard = LeaderboardEntry(
        entry_id="leaderboard-entry:dashboard-distractor",
        created_at=now,
        strategy_card_id=card.card_id,
        evaluation_id=evaluation.evaluation_id,
        trial_id=trial.trial_id,
        symbol="BTC-USD",
        rankable=True,
        alpha_score=0.99,
        promotion_stage="CANDIDATE",
        blocked_reasons=[],
        leaderboard_rules_version="pr7-v1",
        decision_basis="test",
    )
    outcome = PaperShadowOutcome(
        outcome_id="paper-shadow-outcome:dashboard-distractor",
        created_at=now,
        leaderboard_entry_id=leaderboard.entry_id,
        evaluation_id=evaluation.evaluation_id,
        strategy_card_id=card.card_id,
        trial_id=trial.trial_id,
        symbol="BTC-USD",
        window_start=now - timedelta(hours=24),
        window_end=now,
        observed_return=0.09,
        benchmark_return=0.01,
        excess_return_after_costs=0.07,
        max_adverse_excursion=0.01,
        turnover=0.4,
        outcome_grade="PASS",
        failure_attributions=["distractor_shadow"],
        recommended_promotion_stage="PROMOTION_READY",
        recommended_strategy_action="PROMOTION_READY",
        blocked_reasons=[],
        notes=[],
        decision_basis="test",
    )
    agenda = ResearchAgenda(
        agenda_id="research-agenda:dashboard-distractor",
        created_at=now,
        symbol="BTC-USD",
        title="Dashboard distractor agenda",
        hypothesis="Dashboard distractor agenda must not be mixed into visible run.",
        priority="LOW",
        status="OPEN",
        target_strategy_family="mean_reversion",
        strategy_card_ids=[card.card_id],
        expected_artifacts=["strategy_card"],
        acceptance_criteria=["distractor should stay hidden"],
        blocked_actions=["promote_to_live"],
        decision_basis="test",
    )
    repository.save_strategy_card(card)
    repository.save_experiment_trial(trial)
    repository.save_locked_evaluation_result(evaluation)
    repository.save_leaderboard_entry(leaderboard)
    repository.save_paper_shadow_outcome(outcome)
    repository.save_research_agenda(agenda)


def test_render_dashboard_handles_empty_storage(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)

    assert snapshot.latest_forecast is None
    assert snapshot.latest_review is None
    assert snapshot.latest_replay_summary is None
    assert 'lang="zh-Hant"' in html
    assert "操作摘要" in html
    assert "等待第一筆預測循環" in html
    assert html.count("等待第一筆預測循環") == 1
    assert "目前預測" in html
    assert "目前還沒有預測資料" in html
    assert "目前還沒有 replay 摘要" in html
    assert "Dashboard 產生時間" in html


def test_render_dashboard_includes_latest_artifacts(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    forecast = Forecast(
        forecast_id="forecast:a",
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        anchor_time=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        target_window_start=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 21, 11, 0, tzinfo=UTC),
        candle_interval_minutes=60,
        expected_candle_count=3,
        status="resolved",
        status_reason="scored",
        predicted_regime="trend_up",
        confidence=0.55,
        provider_data_through=datetime(2026, 4, 21, 11, 0, tzinfo=UTC),
        observed_candle_count=3,
    )
    score = ForecastScore(
        score_id="score:a",
        forecast_id="forecast:a",
        scored_at=datetime(2026, 4, 21, 11, 0, tzinfo=UTC),
        predicted_regime="trend_up",
        actual_regime="trend_up",
        score=1.0,
        target_window_start=forecast.target_window_start,
        target_window_end=forecast.target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=3,
        observed_candle_count=3,
        provider_data_through=datetime(2026, 4, 21, 11, 0, tzinfo=UTC),
        scoring_basis="regime_direction_over_fully_covered_hourly_window",
    )
    review = Review(
        review_id="review:a",
        created_at=datetime(2026, 4, 21, 11, 5, tzinfo=UTC),
        score_ids=[score.score_id],
        forecast_ids=[forecast.forecast_id],
        average_score=1.0,
        threshold_used=0.6,
        decision_basis="average of last 1 valid scores",
        summary="Forecast accuracy acceptable; keep current paper-only settings.",
        proposal_recommended=False,
        proposal_reason="average_score_at_or_above_threshold",
    )
    proposal = Proposal(
        proposal_id="proposal:a",
        created_at=datetime(2026, 4, 21, 11, 6, tzinfo=UTC),
        review_id=review.review_id,
        score_ids=[score.score_id],
        proposal_type="risk_adjustment",
        changes={"max_position_pct": 0.15, "new_entry_enabled": False},
        threshold_used=0.6,
        decision_basis="average of last 1 valid scores",
        rationale="Generated because average_score_below_threshold against threshold 0.60.",
    )
    summary = build_evaluation_summary(
        replay_id="replay:btc",
        generated_at=datetime(2026, 4, 21, 12, 0, tzinfo=UTC),
        forecasts=[forecast],
        scores=[score],
        reviews=[review],
        proposals=[proposal],
    )

    repository.save_forecast(forecast)
    repository.save_score(score)
    repository.save_review(review)
    repository.save_proposal(proposal)
    repository.save_evaluation_summary(summary)

    _write_meta(
        tmp_path / "last_run_meta.json",
        {
            "provider": "sample",
            "symbol": "BTC-USD",
            "new_forecast": forecast.to_dict(),
            "score_count": 1,
            "score_ids": [score.score_id],
            "review_id": review.review_id,
            "proposal_id": proposal.proposal_id,
        },
    )
    _write_meta(
        tmp_path / "last_replay_meta.json",
        {
            "provider": "sample",
            "symbol": "BTC-USD",
            "cycles_run": 3,
            "scores_created": 1,
            "evaluation_summary": summary.to_dict(),
        },
    )

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)

    assert snapshot.latest_forecast is not None
    assert snapshot.latest_review is not None
    assert snapshot.latest_replay_summary is not None
    assert 'grid-template-columns: 190px minmax(0, 1fr);' in html
    assert 'main {\n      padding: 28px 32px 42px;\n      display: grid;\n      grid-template-columns: minmax(0, 1fr);' in html
    assert "操作摘要" in html
    assert "目前預測" in html
    assert 'nav aria-label="儀表板區段"' in html
    assert "本輪判讀與建議" in html
    assert "支撐依據" in html
    assert "歷史脈絡" in html
    assert "BTC-USD" in html
    assert "scored" in html
    assert review.summary in html
    assert proposal.proposal_id in html
    assert summary.summary_id in html
    assert 'id="decision"' in html
    assert 'class="panel half secondary-panel" id="replay"' in html
    assert 'id="evidence"' in html
    assert 'id="system"' not in html
    assert "證據快照" in html
    assert html.index('id="summary"') < html.index('id="forecast"') < html.index('id="decision"') < html.index('id="evidence"') < html.index('id="replay"') < html.index('id="raw"')
    summary_section = html.split('id="summary"', 1)[1].split("</section>", 1)[0]
    assert summary_section.index('class="summary-grid"') < summary_section.index('class="summary-tags"') < summary_section.index('class="summary-note"')
    assert "<details open>" not in html
    forecast_section = html.split('id="forecast"', 1)[1].split("</section>", 1)[0]
    forecast_surface = forecast_section.split("<details>", 1)[0]
    assert "forecast:a" not in forecast_surface
    assert "Provider Through" not in forecast_surface
    assert "Anchor" not in forecast_surface
    assert "<details>" in forecast_section
    decision_section = html.split('id="decision"', 1)[1].split("</section>", 1)[0]
    decision_surface = decision_section.split("<details>", 1)[0]
    assert review.summary in decision_surface
    assert "review:a" not in decision_surface
    assert "proposal:a" not in decision_surface
    assert "Forecast IDs" not in decision_surface
    assert "Score IDs" not in decision_surface
    replay_section = html.split('id="replay"', 1)[1].split("</section>", 1)[0]
    assert "<details>" in replay_section
    assert "Summary ID" in replay_section
    raw_section = html.split('id="raw"', 1)[1].split("</section>", 1)[0]
    assert raw_section.count("<details>") == 2
    assert "<pre>" not in raw_section.split("<details>", 1)[0]
    assert 'grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));' in html


def test_render_dashboard_uses_only_proposal_for_latest_review(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    old_review = Review(
        review_id="review:old",
        created_at=datetime(2026, 4, 21, 10, 0, tzinfo=UTC),
        score_ids=["score:old"],
        forecast_ids=["forecast:old"],
        average_score=0.2,
        threshold_used=0.6,
        decision_basis="old basis",
        summary="Old review requested a proposal.",
        proposal_recommended=True,
        proposal_reason="average_score_below_threshold",
    )
    latest_review = Review(
        review_id="review:latest",
        created_at=datetime(2026, 4, 21, 11, 0, tzinfo=UTC),
        score_ids=["score:latest"],
        forecast_ids=["forecast:latest"],
        average_score=1.0,
        threshold_used=0.6,
        decision_basis="latest basis",
        summary="Latest review keeps current settings.",
        proposal_recommended=False,
        proposal_reason="average_score_at_or_above_threshold",
    )
    old_proposal = Proposal(
        proposal_id="proposal:old",
        created_at=datetime(2026, 4, 21, 10, 5, tzinfo=UTC),
        review_id=old_review.review_id,
        score_ids=["score:old"],
        proposal_type="risk_adjustment",
        changes={"max_position_pct": 0.10},
        threshold_used=0.6,
        decision_basis="old basis",
        rationale="old proposal should not be shown as current",
    )

    repository.save_review(old_review)
    repository.save_review(latest_review)
    repository.save_proposal(old_proposal)

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)
    decision_section = html.split('id="decision"', 1)[1].split("</section>", 1)[0]

    assert snapshot.latest_review == latest_review
    assert snapshot.latest_proposal is None
    assert latest_review.summary in decision_section
    assert "proposal:old" not in decision_section
    assert "old proposal should not be shown as current" not in decision_section


def test_render_dashboard_labels_waiting_for_data_as_coverage_wait(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    repository.save_forecast(
        Forecast(
            forecast_id="forecast:waiting",
            symbol="BTC-USD",
            created_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
            anchor_time=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
            target_window_start=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
            target_window_end=datetime(2026, 4, 21, 11, 0, tzinfo=UTC),
            candle_interval_minutes=60,
            expected_candle_count=3,
            status="waiting_for_data",
            status_reason="awaiting_provider_coverage",
            predicted_regime="trend_up",
            confidence=0.55,
            provider_data_through=datetime(2026, 4, 21, 10, 0, tzinfo=UTC),
            observed_candle_count=2,
        )
    )

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert "等待資料覆蓋" in html
    assert "等待 provider 補齊目標視窗" in html
    assert '<div class="summary-value">已結束</div>' not in html


def test_render_dashboard_reports_automation_freshness(tmp_path, monkeypatch):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    codex_home = tmp_path / ".codex"
    _write_automation(codex_home, "hourly-paper-forecast", status="PAUSED")
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path / "storage"))

    assert "每小時：已暫停（PAUSED）" in html
    assert "Dashboard 產生時間" in html
    assert "Automation 狀態來源" in html
    assert "1970-" not in html


def test_render_dashboard_marks_stale_replay_context(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    latest_forecast = Forecast(
        forecast_id="forecast:live",
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 23, 13, 23, tzinfo=UTC),
        anchor_time=datetime(2026, 4, 23, 13, 0, tzinfo=UTC),
        target_window_start=datetime(2026, 4, 23, 13, 0, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 24, 13, 0, tzinfo=UTC),
        candle_interval_minutes=60,
        expected_candle_count=25,
        status="pending",
        status_reason="awaiting_horizon_end",
        predicted_regime="trend_down",
        confidence=0.55,
        provider_data_through=datetime(2026, 4, 23, 13, 0, tzinfo=UTC),
        observed_candle_count=8,
    )
    replay_forecast = Forecast(
        forecast_id="forecast:replay",
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 22, 8, 0, tzinfo=UTC),
        anchor_time=datetime(2026, 4, 22, 8, 0, tzinfo=UTC),
        target_window_start=datetime(2026, 4, 22, 8, 0, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 22, 9, 0, tzinfo=UTC),
        candle_interval_minutes=60,
        expected_candle_count=2,
        status="resolved",
        status_reason="scored",
        predicted_regime="trend_up",
        confidence=0.55,
        provider_data_through=datetime(2026, 4, 22, 9, 0, tzinfo=UTC),
        observed_candle_count=2,
    )
    repository.save_forecast(latest_forecast)
    summary = build_evaluation_summary(
        replay_id="replay:btc",
        generated_at=datetime(2026, 4, 22, 18, 40, tzinfo=UTC),
        forecasts=[replay_forecast],
        scores=[],
        reviews=[],
        proposals=[],
    )
    repository.save_evaluation_summary(summary)

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)

    assert snapshot.replay_is_stale is True
    assert "historical" in snapshot.replay_freshness_label.lower()
    assert "產生時間" in html
    assert "僅供歷史脈絡參考" in html
    assert "落後最新預測 29 小時" in html
    assert "behind latest forecast" not in html
    assert 'secondary-panel' in html


def test_render_dashboard_translates_failure_status_reasons(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    repository.save_forecast(
        Forecast(
            forecast_id="forecast:missing",
            symbol="BTC-USD",
            created_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
            anchor_time=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
            target_window_start=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
            target_window_end=datetime(2026, 4, 21, 11, 0, tzinfo=UTC),
            candle_interval_minutes=60,
            expected_candle_count=3,
            status="unscorable",
            status_reason="missing_expected_candles",
            predicted_regime="trend_up",
            confidence=0.55,
            provider_data_through=datetime(2026, 4, 21, 11, 0, tzinfo=UTC),
            observed_candle_count=2,
        )
    )

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert "無法評分（unscorable）" in html
    assert "缺少必要 K 線（missing_expected_candles）" in html
    assert '<span class="tag">missing_expected_candles</span>' not in html


def test_cli_render_dashboard_writes_html_file(tmp_path):
    exit_code = main(
        [
            "render-dashboard",
            "--storage-dir",
            str(tmp_path),
        ]
    )

    output_path = tmp_path / "dashboard.html"

    assert exit_code == 0
    assert output_path.exists()
    html = output_path.read_text(encoding="utf-8")
    assert "Paper Forecast Loop" in html
    assert "操作摘要" in html


def test_cli_render_dashboard_rejects_missing_storage_dir_without_creating_it(tmp_path):
    missing_storage = tmp_path / "typo-storage"

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "render-dashboard",
                "--storage-dir",
                str(missing_storage),
            ]
        )

    assert exc_info.value.code == 2
    assert not missing_storage.exists()


def test_dashboard_prioritizes_strategy_decision_and_health_status(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime.now(tz=UTC).replace(microsecond=0)
    forecast = Forecast(
        forecast_id="forecast:decision",
        symbol="BTC-USD",
        created_at=now,
        anchor_time=now,
        target_window_start=now,
        target_window_end=now + timedelta(hours=24),
        candle_interval_minutes=60,
        expected_candle_count=25,
        status="pending",
        status_reason="awaiting_horizon_end",
        predicted_regime="trend_up",
        confidence=0.72,
        provider_data_through=now,
        observed_candle_count=1,
    )
    baseline = BaselineEvaluation(
        baseline_id="baseline:decision",
        created_at=now,
        symbol="BTC-USD",
        sample_size=5,
        directional_accuracy=0.8,
        baseline_accuracy=0.4,
        model_edge=0.4,
        recent_score=0.8,
        evidence_grade="B",
        forecast_ids=[forecast.forecast_id],
        score_ids=["score:a"],
        decision_basis="test baseline",
    )
    decision = StrategyDecision(
        decision_id="decision:buy",
        created_at=now,
        symbol="BTC-USD",
        horizon_hours=24,
        action="BUY",
        confidence=0.72,
        evidence_grade="B",
        risk_level="MEDIUM",
        tradeable=True,
        blocked_reason=None,
        recommended_position_pct=0.15,
        current_position_pct=0.0,
        max_position_pct=0.15,
        invalidation_conditions=["health-check 轉為 blocking"],
        reason_summary="forecast 偏多且模型證據打贏 baseline。",
        forecast_ids=[forecast.forecast_id],
        score_ids=["score:a"],
        review_ids=[],
        baseline_ids=[baseline.baseline_id],
        decision_basis="test decision",
    )
    score = ForecastScore(
        score_id="score:a",
        forecast_id=forecast.forecast_id,
        scored_at=now,
        predicted_regime="trend_up",
        actual_regime="trend_up",
        score=1.0,
        target_window_start=forecast.target_window_start,
        target_window_end=forecast.target_window_end,
        candle_interval_minutes=60,
        expected_candle_count=25,
        observed_candle_count=25,
        provider_data_through=forecast.target_window_end,
        scoring_basis="test",
    )
    repository.save_forecast(forecast)
    repository.save_score(score)
    repository.save_baseline_evaluation(baseline)
    repository.save_strategy_decision(decision)

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert html.index('id="strategy"') < html.index('id="summary"')
    assert "明日策略決策" in html
    assert "買進（BUY）" in html
    assert "證據等級 B" in html
    assert "預測品質 vs 基準線" in html
    assert "forecast 偏多且模型證據打贏 baseline。" in html
    assert "需要修復" not in html.split('id="strategy"', 1)[1].split("</section>", 1)[0]


def test_dashboard_surfaces_strategy_research_context_before_raw_metadata(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    _seed_dashboard_strategy_research(repository, now)

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert 'id="strategy-research"' in html
    assert html.index('id="strategy-research"') < html.index('id="raw"')
    assert "策略研究焦點" in html
    assert "Dashboard BTC breakout candidate" in html
    assert "Dashboard should show concrete strategy logic before raw metadata." in html
    assert "進場規則" in html
    assert "突破前高且成交量放大" in html
    assert "Evidence Gates" in html
    assert "locked-evaluation:dashboard-visible" in html
    assert "alpha_score" in html
    assert "0.2100" in html
    assert "Leaderboard" in html
    assert "leaderboard-entry:dashboard-visible" in html
    assert "Paper-shadow 歸因" in html
    assert "negative_excess_return" in html
    assert "下一步研究動作" in html
    assert "REVISE_STRATEGY" in html
    assert "research-autopilot-run:dashboard-visible" in html


def test_dashboard_uses_autopilot_linked_chain_instead_of_latest_symbol_artifacts(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    _seed_dashboard_strategy_research(repository, now)
    _seed_dashboard_distractor_strategy_research_without_run(repository, now + timedelta(minutes=5))

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert "research-autopilot-run:dashboard-visible" in html
    assert "strategy-card:dashboard-visible" in html
    assert "leaderboard-entry:dashboard-visible" in html
    assert "locked-evaluation:dashboard-visible" in html
    assert "paper-shadow-outcome:dashboard-visible" in html
    assert "Dashboard BTC breakout candidate" in html
    assert "negative_excess_return" in html
    assert "Dashboard distractor strategy" not in html
    assert "leaderboard-entry:dashboard-distractor" not in html
    assert "locked-evaluation:dashboard-distractor" not in html
    assert "distractor_shadow" not in html


def test_dashboard_shows_strategy_revision_candidate_even_when_autopilot_chain_points_to_parent(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    _seed_dashboard_strategy_research(repository, now)
    _seed_dashboard_revision_candidate(repository, now + timedelta(minutes=10))

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert "research-autopilot-run:dashboard-visible" in html
    assert "Dashboard BTC breakout candidate" in html
    assert "策略修正候選" in html
    assert "strategy-card:dashboard-revision" in html
    assert "strategy-card:dashboard-visible" in html
    assert "paper-shadow-outcome:dashboard-visible" in html
    assert "research-agenda:dashboard-revision" in html
    assert "DRAFT" in html
    assert "Require positive after-cost edge" in html
    assert "negative_excess_return" in html


def test_dashboard_shows_strategy_revision_retest_scaffold(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    _seed_dashboard_strategy_research(repository, now)
    _seed_dashboard_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_dashboard_revision_retest_scaffold(repository, now + timedelta(minutes=20))

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert "Revision Retest Scaffold" in html
    assert "experiment-trial:dashboard-revision-retest" in html
    assert "research-dataset:dashboard-revision-retest" in html
    assert "PENDING" in html
    assert "split-manifest:dashboard-revision-retest" in html
    assert "baseline_evaluation" in html
    assert "backtest_result" in html
    assert "locked_evaluation_result" in html


def test_dashboard_shows_revision_retest_task_plan(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    _seed_dashboard_strategy_research(repository, now)
    _seed_dashboard_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_dashboard_revision_retest_scaffold(repository, now + timedelta(minutes=20))

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert "下一個 retest 研究任務" in html
    assert "lock_evaluation_protocol" in html
    assert "ready" in html
    assert "cost_model_snapshot" in html
    assert "lock-evaluation-protocol" in html
    assert "--train-start" in html


def test_dashboard_shows_revision_retest_task_run_log(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    _seed_dashboard_strategy_research(repository, now)
    _seed_dashboard_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_dashboard_revision_retest_scaffold(repository, now + timedelta(minutes=20))
    repository.save_automation_run(
        AutomationRun(
            automation_run_id="automation-run:dashboard-retest-task",
            started_at=now + timedelta(minutes=30),
            completed_at=now + timedelta(minutes=30),
            status="RETEST_TASK_BLOCKED",
            symbol="BTC-USD",
            provider="research",
            command="revision-retest-plan",
            steps=[
                {
                    "name": "revision_card",
                    "status": "completed",
                    "artifact_id": "strategy-card:dashboard-revision",
                },
                {
                    "name": "source_outcome",
                    "status": "completed",
                    "artifact_id": "paper-shadow-outcome:dashboard-visible",
                },
                {
                    "name": "lock_evaluation_protocol",
                    "status": "blocked",
                    "artifact_id": None,
                }
            ],
            health_check_id=None,
            decision_id=None,
            repair_request_id=None,
            decision_basis="revision_retest_task_plan_run_log",
        )
    )
    repository.save_automation_run(
        AutomationRun(
            automation_run_id="automation-run:dashboard-wrong-revision-newer",
            started_at=now + timedelta(minutes=35),
            completed_at=now + timedelta(minutes=35),
            status="RETEST_TASK_READY",
            symbol="BTC-USD",
            provider="research",
            command="revision-retest-plan",
            steps=[
                {
                    "name": "revision_card",
                    "status": "completed",
                    "artifact_id": "strategy-card:other-revision",
                },
                {
                    "name": "source_outcome",
                    "status": "completed",
                    "artifact_id": "paper-shadow-outcome:other",
                },
            ],
            health_check_id=None,
            decision_id=None,
            repair_request_id=None,
            decision_basis="revision_retest_task_plan_run_log",
        )
    )
    repository.save_automation_run(
        AutomationRun(
            automation_run_id="automation-run:dashboard-unrelated-newer",
            started_at=now + timedelta(minutes=40),
            completed_at=now + timedelta(minutes=40),
            status="SUCCESS",
            symbol="BTC-USD",
            provider="coingecko",
            command="run-once",
            steps=[],
            health_check_id=None,
            decision_id=None,
            repair_request_id=None,
            decision_basis="hourly_cycle",
        )
    )

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert "最新 retest task run log" in html
    assert "automation-run:dashboard-retest-task" in html
    assert "RETEST_TASK_BLOCKED" in html
    assert "revision-retest-plan" in html
    assert "lock_evaluation_protocol" in html
    assert "automation-run:dashboard-wrong-revision-newer" not in html
    assert "automation-run:dashboard-unrelated-newer" not in html


def test_dashboard_shows_revision_retest_autopilot_run(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    _seed_dashboard_strategy_research(repository, now)
    _seed_dashboard_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_dashboard_revision_retest_scaffold(repository, now + timedelta(minutes=20))
    _seed_dashboard_revision_retest_autopilot_run(repository, now + timedelta(minutes=30))
    repository.save_research_autopilot_run(
        ResearchAutopilotRun(
            run_id="research-autopilot-run:dashboard-parent-newer",
            created_at=now + timedelta(minutes=40),
            symbol="BTC-USD",
            agenda_id="research-agenda:dashboard-visible",
            strategy_card_id="strategy-card:dashboard-visible",
            experiment_trial_id="experiment-trial:dashboard-visible",
            locked_evaluation_id="locked-evaluation:dashboard-visible",
            leaderboard_entry_id="leaderboard-entry:dashboard-visible",
            strategy_decision_id=None,
            paper_shadow_outcome_id="paper-shadow-outcome:dashboard-visible",
            steps=[{"name": "parent_strategy", "status": "completed", "artifact_id": "strategy-card:dashboard-visible"}],
            loop_status="REVISION_REQUIRED",
            next_research_action="PARENT_SHOULD_NOT_RENDER_AS_REVISION_RETEST",
            blocked_reasons=["parent_strategy_failure"],
            decision_basis="research_paper_autopilot_loop",
        )
    )

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)

    assert snapshot.latest_strategy_revision_retest_autopilot_run is not None
    assert snapshot.latest_strategy_revision_retest_autopilot_run.run_id == "research-autopilot-run:dashboard-revision-retest"
    assert "最新 revision retest autopilot run" in html
    assert "research-autopilot-run:dashboard-revision-retest" in html
    assert "REPAIR_EVIDENCE_CHAIN" in html
    assert "locked_evaluation_not_rankable" in html
    assert "paper-shadow-outcome:dashboard-revision-retest" in html


def test_dashboard_shows_strategy_lineage_summary(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    _seed_dashboard_strategy_research(repository, now)
    _seed_dashboard_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_dashboard_strategy_lineage(repository, now + timedelta(minutes=20))

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)

    assert snapshot.latest_strategy_lineage_summary is not None
    assert snapshot.latest_strategy_lineage_summary.revision_count == 1
    assert "策略 lineage" in html
    assert "REVISE_STRATEGY" in html
    assert "QUARANTINE_STRATEGY" in html
    assert "negative_excess_return" in html
    assert "drawdown_breach" in html
    assert "-0.0250" in html
    assert "-0.0800" in html
    assert "paper-shadow-outcome:dashboard-revision-quarantine" in html


def test_dashboard_lineage_uses_parent_root_when_latest_chain_is_revision(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    _seed_dashboard_strategy_research(repository, now)
    _seed_dashboard_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_dashboard_revision_retest_scaffold(repository, now + timedelta(minutes=20))
    _seed_dashboard_revision_retest_autopilot_run(repository, now + timedelta(minutes=30))
    _seed_dashboard_strategy_lineage(repository, now + timedelta(minutes=40))

    summary = build_dashboard_snapshot(tmp_path).latest_strategy_lineage_summary

    assert summary is not None
    assert summary.root_card_id == "strategy-card:dashboard-visible"
    assert summary.revision_card_ids == ["strategy-card:dashboard-revision"]
    assert summary.outcome_count == 2
    assert summary.action_counts == {"QUARANTINE_STRATEGY": 1, "REVISE_STRATEGY": 1}
    assert summary.best_excess_return_after_costs == -0.025


def test_dashboard_strategy_lineage_includes_multi_generation_revisions(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    _seed_dashboard_strategy_research(repository, now)
    _seed_dashboard_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_dashboard_strategy_lineage(repository, now + timedelta(minutes=20))
    _seed_dashboard_second_generation_strategy_lineage(repository, now + timedelta(minutes=30))

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)

    assert snapshot.latest_strategy_lineage_summary is not None
    assert snapshot.latest_strategy_lineage_summary.root_card_id == "strategy-card:dashboard-visible"
    assert snapshot.latest_strategy_lineage_summary.revision_card_ids == [
        "strategy-card:dashboard-revision",
        "strategy-card:dashboard-second-revision",
    ]
    assert [(node.card_id, node.parent_card_id, node.depth) for node in snapshot.latest_strategy_lineage_summary.revision_nodes] == [
        ("strategy-card:dashboard-revision", "strategy-card:dashboard-visible", 1),
        ("strategy-card:dashboard-second-revision", "strategy-card:dashboard-revision", 2),
    ]
    assert snapshot.latest_strategy_lineage_summary.outcome_count == 3
    assert snapshot.latest_strategy_lineage_summary.action_counts == {
        "QUARANTINE_STRATEGY": 2,
        "REVISE_STRATEGY": 1,
    }
    assert "Revision Tree" in html
    assert "Depth 2" in html
    assert "Parent strategy-card:dashboard-revision" in html
    assert "Name Dashboard BTC breakout candidate second revision" in html
    assert "Hypothesis Second revision should inherit the original strategy lineage." in html
    assert "Source paper-shadow-outcome:dashboard-revision-quarantine" in html
    assert "Fixes drawdown_breach；weak_baseline_edge" in html
    assert "表現結論" in html
    assert "改善 0 / 惡化 2 / 未知 0" in html
    assert "主要失敗 drawdown_breach" in html
    assert "最新動作 QUARANTINE_STRATEGY" in html
    assert "下一步研究焦點" in html
    assert "停止加碼此 lineage，優先研究 drawdown_breach 的修正或新策略。" in html
    assert "表現軌跡" in html
    assert "Outcome paper-shadow-outcome:dashboard-second-revision-quarantine" in html
    assert "Card strategy-card:dashboard-second-revision" in html
    assert "Excess -0.1100" in html
    assert "Delta -0.0300" in html
    assert "惡化" in html
    assert "weak_baseline_edge" in html
    assert "paper-shadow-outcome:dashboard-second-revision-quarantine" in html
    assert "-0.1100" in html


def test_dashboard_lineage_research_agenda_visibility(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    _seed_dashboard_strategy_research(repository, now)
    _seed_dashboard_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_dashboard_strategy_lineage(repository, now + timedelta(minutes=20))
    _seed_dashboard_second_generation_strategy_lineage(repository, now + timedelta(minutes=30))
    create_lineage_research_agenda(
        repository=repository,
        created_at=now + timedelta(minutes=40),
        symbol="BTC-USD",
    )
    recorded = record_lineage_research_task_run(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=50),
    )

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)

    assert snapshot.latest_lineage_research_task_plan is not None
    assert snapshot.latest_lineage_research_task_plan.next_task_id == "draft_replacement_strategy_hypothesis"
    assert snapshot.latest_lineage_research_task_run == recorded.automation_run
    assert "Lineage 研究 agenda" in html
    assert "Lineage 下一個研究任務" in html
    assert "最新 lineage task run log" in html
    assert "LINEAGE_RESEARCH_TASK_READY" in html
    assert recorded.automation_run.automation_run_id in html
    assert "draft_replacement_strategy_hypothesis" in html
    assert "新策略" in html
    assert "strategy_lineage_research_agenda" in html
    assert "停止加碼此 lineage" in html
    assert "drawdown_breach" in html


def test_dashboard_lineage_research_task_run_ignores_stale_run_after_new_outcome(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    _seed_dashboard_strategy_research(repository, now)
    _seed_dashboard_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_dashboard_strategy_lineage(repository, now + timedelta(minutes=20))
    create_lineage_research_agenda(
        repository=repository,
        created_at=now + timedelta(minutes=30),
        symbol="BTC-USD",
    )
    stale_recorded = record_lineage_research_task_run(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=40),
    )
    _seed_dashboard_second_generation_strategy_lineage(repository, now + timedelta(minutes=50))

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)

    assert snapshot.latest_lineage_research_task_plan is not None
    assert (
        snapshot.latest_lineage_research_task_plan.latest_outcome_id
        == "paper-shadow-outcome:dashboard-second-revision-quarantine"
    )
    assert snapshot.latest_lineage_research_task_run is None
    assert "Lineage 下一個研究任務" in html
    assert "最新 lineage task run log" not in html
    assert stale_recorded.automation_run.automation_run_id not in html


def test_dashboard_lineage_research_agenda_ignores_other_lineage(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    _seed_dashboard_strategy_research(repository, now)
    _seed_dashboard_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_dashboard_strategy_lineage(repository, now + timedelta(minutes=20))
    repository.save_research_agenda(
        ResearchAgenda(
            agenda_id="research-agenda:other-lineage",
            created_at=now + timedelta(minutes=30),
            symbol="BTC-USD",
            title="Other lineage agenda",
            hypothesis="This same-symbol agenda belongs to another lineage.",
            priority="HIGH",
            status="OPEN",
            target_strategy_family="breakout_reversal",
            strategy_card_ids=["strategy-card:other-lineage"],
            expected_artifacts=["strategy_revision_or_new_strategy"],
            acceptance_criteria=["must not render beside the current lineage"],
            blocked_actions=["real_order_submission"],
            decision_basis="strategy_lineage_research_agenda",
        )
    )

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert "Lineage 研究 agenda" not in html
    assert "research-agenda:other-lineage" not in html
    assert "This same-symbol agenda belongs to another lineage." not in html


def test_dashboard_strategy_lineage_escapes_revision_change_summary(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    _seed_dashboard_strategy_research(repository, now)
    _seed_dashboard_malicious_strategy_lineage(repository, now + timedelta(minutes=10))

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert '<script>alert("name")</script>' not in html
    assert '<script>alert("hypothesis")</script>' not in html
    assert '<script>alert("source")</script>' not in html
    assert '<script>alert("fix")</script>' not in html
    assert 'Dashboard &lt;script&gt;alert(&quot;name&quot;)&lt;/script&gt; revision' in html
    assert 'Repair hypothesis &lt;script&gt;alert(&quot;hypothesis&quot;)&lt;/script&gt;' in html
    assert 'paper-shadow-outcome:&lt;script&gt;alert(&quot;source&quot;)&lt;/script&gt;' in html
    assert 'drawdown_breach&lt;script&gt;alert(&quot;fix&quot;)&lt;/script&gt;' in html


def test_dashboard_revision_retest_task_plan_falls_back_when_source_missing(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    _seed_dashboard_strategy_research(repository, now)
    _seed_dashboard_revision_candidate(repository, now + timedelta(minutes=10))
    (tmp_path / "paper_shadow_outcomes.jsonl").write_text("", encoding="utf-8")

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert "策略修正候選" in html
    assert "目前沒有可解析的 retest task plan" in html


def test_dashboard_does_not_label_unrelated_agenda_as_revision_retest(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    _seed_dashboard_strategy_research(repository, now)
    _seed_dashboard_revision_candidate(repository, now + timedelta(minutes=10))
    unrelated_agenda = ResearchAgenda(
        agenda_id="research-agenda:dashboard-unrelated",
        created_at=now + timedelta(minutes=20),
        symbol="BTC-USD",
        title="Unrelated planning note",
        hypothesis="This agenda should not be rendered as the revision retest agenda.",
        priority="LOW",
        status="OPEN",
        target_strategy_family="breakout_reversal",
        strategy_card_ids=["strategy-card:dashboard-revision"],
        expected_artifacts=["notes"],
        acceptance_criteria=["not a revision retest"],
        blocked_actions=[],
        decision_basis="test",
    )
    (tmp_path / "research_agendas.jsonl").write_text(
        json.dumps(unrelated_agenda.to_dict()) + "\n",
        encoding="utf-8",
    )

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert "策略修正候選" in html
    assert "strategy-card:dashboard-revision" in html
    assert "research-agenda:dashboard-unrelated" not in html
    assert "Unrelated planning note" not in html


def test_dashboard_strategy_research_panel_shows_agenda_only_state(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    agenda = ResearchAgenda(
        agenda_id="research-agenda:agenda-only",
        created_at=now,
        symbol="BTC-USD",
        title="Agenda-only BTC research",
        hypothesis="研究 agenda 應該在策略卡出現前就可見。",
        priority="HIGH",
        status="OPEN",
        target_strategy_family="breakout_reversal",
        strategy_card_ids=[],
        expected_artifacts=["strategy_card"],
        acceptance_criteria=["create the first strategy card"],
        blocked_actions=["promote_to_live"],
        decision_basis="test",
    )
    repository.save_research_agenda(agenda)

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert 'id="strategy-research"' in html
    assert "Research Agenda" in html
    assert "research-agenda:agenda-only" in html
    assert "Agenda-only BTC research" in html
    assert "研究 agenda 應該在策略卡出現前就可見。" in html
    assert "目前尚無 strategy card" not in html


def test_dashboard_renders_portfolio_nav_pnl_and_risk(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    position = PaperPosition(
        symbol="BTC-USD",
        quantity=10.0,
        avg_price=100.0,
        market_price=105.0,
        market_value=1_050.0,
        unrealized_pnl=50.0,
        position_pct=0.105,
    )
    portfolio = PaperPortfolioSnapshot(
        snapshot_id="portfolio:risk-dashboard",
        created_at=now,
        equity=10_000.0,
        cash=8_950.0,
        gross_exposure_pct=0.105,
        net_exposure_pct=0.105,
        max_drawdown_pct=0.02,
        positions=[position],
        realized_pnl=25.0,
        unrealized_pnl=50.0,
        nav=10_000.0,
    )
    risk = RiskSnapshot(
        risk_id="risk:dashboard",
        created_at=now,
        symbol="BTC-USD",
        status="REDUCE_RISK",
        severity="warning",
        current_drawdown_pct=0.06,
        max_drawdown_pct=0.06,
        gross_exposure_pct=0.105,
        net_exposure_pct=0.105,
        position_pct=0.105,
        max_position_pct=0.15,
        max_gross_exposure_pct=0.20,
        reduce_risk_drawdown_pct=0.05,
        stop_new_entries_drawdown_pct=0.10,
        findings=["current_drawdown 6.00% >= reduce-risk threshold 5.00%"],
        recommended_action="REDUCE_RISK",
        decision_basis="test",
    )
    repository.save_portfolio_snapshot(portfolio)
    repository.save_risk_snapshot(risk)

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert 'id="portfolio"' in html
    assert "Paper NAV / 風險" in html
    assert "NAV / Equity" in html
    assert "已實現 / 未實現 PnL" in html
    assert "降低風險（REDUCE_RISK）" in html
    assert "Gross exposure：10.50%" in html


def test_dashboard_renders_broker_sandbox_state(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    position = PaperPosition(
        symbol="BTC-USD",
        quantity=1.0,
        avg_price=100.0,
        market_price=110.0,
        market_value=110.0,
        unrealized_pnl=10.0,
        position_pct=0.011,
    )
    portfolio = PaperPortfolioSnapshot(
        snapshot_id="portfolio:broker-dashboard",
        created_at=now,
        equity=10_000.0,
        cash=9_890.0,
        gross_exposure_pct=0.011,
        net_exposure_pct=0.011,
        max_drawdown_pct=0.0,
        positions=[position],
        realized_pnl=0.0,
        unrealized_pnl=10.0,
        nav=10_000.0,
    )
    paper_order = PaperOrder(
        order_id="paper-order:broker-dashboard",
        created_at=now,
        decision_id="decision:broker-dashboard",
        symbol="BTC-USD",
        side="BUY",
        order_type="TARGET_PERCENT",
        status="CREATED",
        target_position_pct=0.05,
        current_position_pct=0.0,
        max_position_pct=0.15,
        rationale="dashboard test",
    )
    broker_order = BrokerOrder(
        broker_order_id="broker-order:broker-dashboard",
        created_at=now,
        updated_at=now,
        local_order_id=paper_order.order_id,
        decision_id=paper_order.decision_id,
        symbol="BTC-USD",
        side="BUY",
        quantity=None,
        target_position_pct=0.05,
        broker="binance_testnet",
        broker_mode="SANDBOX",
        status="ACKNOWLEDGED",
        broker_status="ACKNOWLEDGED",
        broker_order_ref="testnet:dashboard",
        client_order_id=paper_order.order_id,
        error_message=None,
        raw_response={"mock": True},
        decision_basis="test",
    )
    fill = PaperFill(
        fill_id="paper-fill:dashboard",
        order_id=paper_order.order_id,
        decision_id=paper_order.decision_id,
        symbol="BTC-USD",
        side="BUY",
        filled_at=now,
        quantity=1.0,
        market_price=110.0,
        fill_price=110.0,
        gross_value=110.0,
        fee=0.1,
        fee_bps=5.0,
        slippage_bps=10.0,
        net_cash_change=-110.1,
    )
    reconciliation = BrokerReconciliation(
        reconciliation_id="broker-reconciliation:dashboard",
        created_at=now,
        broker="binance_testnet",
        broker_mode="SANDBOX",
        status="MISMATCH",
        severity="blocking",
        repair_required=True,
        local_broker_order_ids=[broker_order.broker_order_id],
        external_order_refs=["testnet:unknown"],
        matched_order_refs=[],
        missing_external_order_ids=[broker_order.broker_order_id],
        unknown_external_order_refs=["testnet:unknown"],
        duplicate_broker_order_refs=[],
        status_mismatches=[],
        position_mismatches=[],
        cash_mismatch=None,
        equity_mismatch=None,
        findings=[{"code": "unknown_external_order", "severity": "blocking"}],
        decision_basis="test",
    )
    gate = ExecutionSafetyGate(
        gate_id="execution-gate:dashboard",
        created_at=now,
        symbol="BTC-USD",
        decision_id=paper_order.decision_id,
        order_id=paper_order.order_id,
        broker="binance_testnet",
        broker_mode="SANDBOX",
        status="BLOCKED",
        severity="blocking",
        allowed=False,
        checks=[
            {"code": "broker_health", "status": "pass"},
            {"code": "broker_reconciliation", "status": "fail"},
        ],
        health_check_id="health:dashboard",
        risk_id="risk:dashboard",
        broker_reconciliation_id=reconciliation.reconciliation_id,
        decision_basis="test",
    )
    repository.save_portfolio_snapshot(portfolio)
    repository.save_paper_order(paper_order)
    repository.save_broker_order(broker_order)
    repository.save_paper_fill(fill)
    repository.save_broker_reconciliation(reconciliation)
    repository.save_execution_safety_gate(gate)

    html = render_dashboard_html(build_dashboard_snapshot(tmp_path))

    assert 'id="broker"' in html
    assert "Broker / Sandbox 狀態" in html
    assert "SANDBOX" in html
    assert "BLOCKED" in html
    assert "對帳有阻擋性差異" in html
    assert "unknown_external_order" in html
    assert "Execution Enabled / Disabled" in html
    assert "Open paper orders：1；active broker lifecycle rows：1。" in html
    assert "BTC-USD qty 1 / value 110.00" in html
