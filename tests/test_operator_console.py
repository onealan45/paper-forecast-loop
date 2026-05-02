from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
import socket

import pytest

from forecast_loop.cli import main
from forecast_loop.lineage_agenda import create_lineage_research_agenda
from forecast_loop.lineage_research_executor import execute_lineage_research_next_task
from forecast_loop.lineage_research_run_log import record_lineage_research_task_run
from forecast_loop.models import (
    AutomationRun,
    BacktestResult,
    EventEdgeEvaluation,
    ExperimentTrial,
    LeaderboardEntry,
    LockedEvaluationResult,
    NotificationArtifact,
    PaperControlEvent,
    PaperPortfolioSnapshot,
    PaperPosition,
    PaperShadowOutcome,
    RepairRequest,
    ResearchAgenda,
    ResearchAutopilotRun,
    ResearchDataset,
    RiskSnapshot,
    SplitManifest,
    StrategyCard,
    StrategyDecision,
    StrategyResearchDigest,
    WalkForwardValidation,
    WalkForwardWindow,
)
from forecast_loop.operator_console import (
    build_operator_console_snapshot,
    local_address_family_for_host,
    render_operator_console_page,
    validate_local_bind_host,
)
from forecast_loop.revision_retest_executor import execute_revision_retest_next_task
from forecast_loop.storage import JsonFileRepository


def _decision(now: datetime) -> StrategyDecision:
    return StrategyDecision(
        decision_id="decision:test",
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
        invalidation_conditions=["health-check blocking"],
        reason_summary="測試用 paper-only BUY 決策。",
        forecast_ids=["forecast:test"],
        score_ids=["score:test"],
        review_ids=[],
        baseline_ids=["baseline:test"],
        decision_basis="test",
    )


def _blocked_decision(now: datetime) -> StrategyDecision:
    return StrategyDecision(
        decision_id="decision:blocked",
        created_at=now,
        symbol="BTC-USD",
        horizon_hours=24,
        action="HOLD",
        confidence=None,
        evidence_grade="INSUFFICIENT",
        risk_level="UNKNOWN",
        tradeable=False,
        blocked_reason="research_backtest_missing",
        recommended_position_pct=0.0,
        current_position_pct=0.0,
        max_position_pct=0.15,
        invalidation_conditions=["backtest artifact arrives"],
        reason_summary="測試用 blocked 決策。",
        forecast_ids=["forecast:blocked"],
        score_ids=["score:blocked"],
        review_ids=["review:blocked"],
        baseline_ids=["baseline:blocked"],
        decision_basis="test",
    )


def _portfolio(now: datetime) -> PaperPortfolioSnapshot:
    position = PaperPosition(
        symbol="BTC-USD",
        quantity=0.1,
        avg_price=90_000.0,
        market_price=100_000.0,
        market_value=10_000.0,
        unrealized_pnl=1_000.0,
        position_pct=0.5,
    )
    return PaperPortfolioSnapshot(
        snapshot_id="portfolio:test",
        created_at=now,
        equity=20_000.0,
        cash=10_000.0,
        gross_exposure_pct=0.5,
        net_exposure_pct=0.5,
        max_drawdown_pct=0.02,
        positions=[position],
        realized_pnl=0.0,
        unrealized_pnl=1_000.0,
        nav=20_000.0,
    )


def _risk(now: datetime) -> RiskSnapshot:
    return RiskSnapshot(
        risk_id="risk:test",
        created_at=now,
        symbol="BTC-USD",
        status="REDUCE_RISK",
        severity="warning",
        current_drawdown_pct=0.06,
        max_drawdown_pct=0.08,
        gross_exposure_pct=0.5,
        net_exposure_pct=0.5,
        position_pct=0.5,
        max_position_pct=0.4,
        max_gross_exposure_pct=0.45,
        reduce_risk_drawdown_pct=0.05,
        stop_new_entries_drawdown_pct=0.10,
        findings=["gross_exposure_above_limit", "drawdown_reduce_risk"],
        recommended_action="REDUCE_RISK",
        decision_basis="test",
    )


def _repair_request(now: datetime) -> RepairRequest:
    return RepairRequest(
        repair_request_id="repair:test",
        created_at=now,
        status="pending",
        severity="blocking",
        observed_failure="No latest forecast exists for BTC-USD.",
        reproduction_command=(
            "python .\\run_forecast_loop.py health-check --storage-dir storage --symbol BTC-USD"
        ),
        expected_behavior="Health check should be non-blocking.",
        affected_artifacts=["forecasts.jsonl", "provider_runs.jsonl"],
        recommended_tests=[
            "python -m pytest -q",
            "python -m compileall -q src tests run_forecast_loop.py sitecustomize.py",
        ],
        safety_boundary="paper-only; no live trading",
        acceptance_criteria=["health-check returns healthy", "dashboard renders repair status"],
        finding_codes=["missing_latest_forecast"],
        prompt_path=".codex/repair_requests/pending/repair_test.md",
    )


def _control_event(now: datetime) -> PaperControlEvent:
    return PaperControlEvent(
        control_id="control:test",
        created_at=now,
        action="STOP_NEW_ENTRIES",
        actor="operator",
        reason="測試用停止新進場控制。",
        status="ACTIVE",
        symbol="BTC-USD",
        requires_confirmation=False,
        confirmed=False,
        decision_basis="test",
    )


def _automation_run(now: datetime) -> AutomationRun:
    return AutomationRun(
        automation_run_id="automation-run:test",
        started_at=now,
        completed_at=now,
        status="completed",
        symbol="BTC-USD",
        provider="sample",
        command="run-once",
        steps=[
            {"name": "forecast", "status": "created", "artifact_id": "forecast:test"},
            {"name": "decide", "status": "completed", "artifact_id": "decision:test"},
        ],
        health_check_id="health:test",
        decision_id="decision:test",
        repair_request_id=None,
        decision_basis="test",
    )


def _notification(now: datetime) -> NotificationArtifact:
    return NotificationArtifact(
        notification_id="notification:test",
        created_at=now,
        symbol="BTC-USD",
        notification_type="BUY_SELL_BLOCKED",
        severity="warning",
        title="買進/賣出訊號被擋",
        message="BTC-USD 不產生 BUY/SELL：research_backtest_missing。",
        status="pending",
        delivery_channel="local_artifact",
        action="HOLD",
        source_artifact_ids=["decision:test"],
        decision_id="decision:test",
        health_check_id=None,
        repair_request_id=None,
        risk_id=None,
        decision_basis="test",
    )


def _visible_strategy_card(now: datetime) -> StrategyCard:
    return StrategyCard(
        card_id="strategy-card:visible",
        created_at=now,
        strategy_name="BTC strategy visibility candidate",
        strategy_family="breakout_reversal",
        version="v2",
        status="ACTIVE",
        symbols=["BTC-USD"],
        hypothesis="Breakout continuation should beat the baseline after costs.",
        signal_description="Detect price breakout with expanding volume and recent momentum confirmation.",
        entry_rules=["突破前高且成交量放大", "recent_momentum_score > 0"],
        exit_rules=["跌回突破區間", "paper-shadow shows negative excess return"],
        risk_rules=["single-trial max position 10%", "quarantine after two failed shadows"],
        parameters={"lookback_hours": 24, "volume_multiplier": 1.5},
        data_requirements=["market_candles:BTC-USD:1h", "volume:BTC-USD"],
        feature_snapshot_ids=["feature-snapshot:visible"],
        backtest_result_ids=["backtest-result:visible"],
        walk_forward_validation_ids=["walk-forward:visible"],
        event_edge_evaluation_ids=[],
        parent_card_id=None,
        author="codex",
        decision_basis="test",
    )


def _visible_trial(now: datetime, card: StrategyCard) -> ExperimentTrial:
    return ExperimentTrial(
        trial_id="experiment-trial:visible",
        created_at=now,
        strategy_card_id=card.card_id,
        trial_index=3,
        status="PASSED",
        symbol="BTC-USD",
        seed=99,
        dataset_id="research-dataset:visible",
        backtest_result_id="backtest-result:visible",
        walk_forward_validation_id="walk-forward:visible",
        event_edge_evaluation_id=None,
        prompt_hash="prompt-visible",
        code_hash="code-visible",
        parameters={"lookback_hours": 24, "volume_multiplier": 1.5},
        metric_summary={"excess_return_after_costs": 0.04, "win_rate": 0.56},
        failure_reason=None,
        started_at=now,
        completed_at=now,
        decision_basis="test",
    )


def _visible_evaluation(now: datetime, card: StrategyCard, trial: ExperimentTrial) -> LockedEvaluationResult:
    return LockedEvaluationResult(
        evaluation_id="locked-evaluation:visible",
        created_at=now,
        strategy_card_id=card.card_id,
        trial_id=trial.trial_id,
        split_manifest_id="split-manifest:visible",
        cost_model_id="cost-model:visible",
        baseline_id="baseline:visible",
        backtest_result_id="backtest-result:visible",
        walk_forward_validation_id="walk-forward:visible",
        event_edge_evaluation_id=None,
        passed=True,
        rankable=True,
        alpha_score=0.21,
        blocked_reasons=[],
        gate_metrics={"alpha_score": 0.21, "holdout_excess_return": 0.04, "max_drawdown": 0.08},
        decision_basis="test",
    )


def _visible_leaderboard(
    now: datetime,
    card: StrategyCard,
    trial: ExperimentTrial,
    evaluation: LockedEvaluationResult,
) -> LeaderboardEntry:
    return LeaderboardEntry(
        entry_id="leaderboard-entry:visible",
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


def _visible_shadow_outcome(
    now: datetime,
    entry: LeaderboardEntry,
) -> PaperShadowOutcome:
    return PaperShadowOutcome(
        outcome_id="paper-shadow-outcome:visible",
        created_at=now,
        leaderboard_entry_id=entry.entry_id,
        evaluation_id=entry.evaluation_id,
        strategy_card_id=entry.strategy_card_id,
        trial_id=entry.trial_id,
        symbol=entry.symbol,
        window_start=now - timedelta(hours=24),
        window_end=now,
        observed_return=-0.01,
        benchmark_return=0.01,
        excess_return_after_costs=-0.025,
        max_adverse_excursion=0.04,
        turnover=1.2,
        outcome_grade="FAIL",
        failure_attributions=["negative_excess_return", "breakout_reversed"],
        recommended_promotion_stage="PAPER_SHADOW_FAILED",
        recommended_strategy_action="REVISE_STRATEGY",
        blocked_reasons=["paper_shadow_failed"],
        notes=["Volume confirmation was not persistent."],
        decision_basis="test",
    )


def _visible_agenda(now: datetime, card: StrategyCard) -> ResearchAgenda:
    return ResearchAgenda(
        agenda_id="research-agenda:visible",
        created_at=now,
        symbol="BTC-USD",
        title="修正 BTC breakout continuation",
        hypothesis="Breakout continuation needs stronger confirmation after failed shadow.",
        priority="HIGH",
        status="OPEN",
        target_strategy_family="breakout_reversal",
        strategy_card_ids=[card.card_id],
        expected_artifacts=["strategy_card", "locked_evaluation", "paper_shadow_outcome"],
        acceptance_criteria=["New revision improves after-cost edge", "Shadow failure attribution is addressed"],
        blocked_actions=["promote_to_live", "increase_position_size"],
        decision_basis="test",
    )


def _visible_autopilot_run(
    now: datetime,
    agenda: ResearchAgenda,
    card: StrategyCard,
    trial: ExperimentTrial,
    evaluation: LockedEvaluationResult,
    entry: LeaderboardEntry,
) -> ResearchAutopilotRun:
    return ResearchAutopilotRun(
        run_id="research-autopilot-run:visible",
        created_at=now,
        symbol="BTC-USD",
        agenda_id=agenda.agenda_id,
        strategy_card_id=card.card_id,
        experiment_trial_id=trial.trial_id,
        locked_evaluation_id=evaluation.evaluation_id,
        leaderboard_entry_id=entry.entry_id,
        strategy_decision_id="decision:test",
        paper_shadow_outcome_id="paper-shadow-outcome:visible",
        steps=[
            {"name": "agenda", "status": "created", "artifact_id": agenda.agenda_id},
            {"name": "strategy", "status": "tested", "artifact_id": card.card_id},
            {"name": "shadow", "status": "failed", "artifact_id": "paper-shadow-outcome:visible"},
        ],
        loop_status="REVISION_REQUIRED",
        next_research_action="REVISE_STRATEGY",
        blocked_reasons=["paper_shadow_failed"],
        decision_basis="test",
    )


def _seed_visible_strategy_research(repository: JsonFileRepository, now: datetime) -> None:
    card = _visible_strategy_card(now)
    trial = _visible_trial(now, card)
    evaluation = _visible_evaluation(now, card, trial)
    entry = _visible_leaderboard(now, card, trial, evaluation)
    outcome = _visible_shadow_outcome(now, entry)
    agenda = _visible_agenda(now, card)
    run = _visible_autopilot_run(now, agenda, card, trial, evaluation, entry)
    repository.save_strategy_card(card)
    repository.save_experiment_trial(trial)
    repository.save_locked_evaluation_result(evaluation)
    repository.save_leaderboard_entry(entry)
    repository.save_paper_shadow_outcome(outcome)
    repository.save_research_agenda(agenda)
    repository.save_research_autopilot_run(run)


def _seed_visible_strategy_research_digest(repository: JsonFileRepository, now: datetime) -> None:
    repository.save_event_edge_evaluation(
        EventEdgeEvaluation(
            evaluation_id="event-edge:visible",
            event_family="crypto_flow",
            event_type="CRYPTO_FLOW",
            symbol="BTC-USD",
            created_at=now,
            split="historical_event_sample",
            horizon_hours=24,
            sample_n=2,
            average_forward_return=-0.02,
            average_benchmark_return=-0.008,
            average_excess_return_after_costs=-0.011366,
            hit_rate=0.0,
            max_adverse_excursion_p50=-0.03,
            max_adverse_excursion_p90=-0.05,
            max_drawdown_if_traded=-0.09,
            turnover=2.0,
            estimated_cost_bps=15.0,
            dsr=None,
            white_rc_p=None,
            stability_score=None,
            passed=False,
            blocked_reason="non_positive_after_cost_edge",
            flags=["insufficient_sample_size", "non_positive_after_cost_edge"],
        )
    )
    repository.save_backtest_result(
        BacktestResult(
            result_id="backtest-result:visible",
            backtest_id="backtest-run:visible",
            created_at=now,
            symbol="BTC-USD",
            start=now - timedelta(days=30),
            end=now,
            initial_cash=10_000,
            final_equity=9_128,
            strategy_return=-0.0872,
            benchmark_return=0.0102,
            max_drawdown=0.0921,
            sharpe=-3.108,
            turnover=0.75,
            win_rate=0.214,
            trade_count=14,
            equity_curve=[],
            decision_basis="test",
        )
    )
    repository.save_walk_forward_validation(
        WalkForwardValidation(
            validation_id="walk-forward:visible",
            created_at=now,
            symbol="BTC-USD",
            start=now - timedelta(days=20),
            end=now,
            strategy_name="moving_average_trend",
            train_size=120,
            validation_size=96,
            test_size=216,
            step_size=24,
            initial_cash=10_000,
            fee_bps=5,
            slippage_bps=10,
            moving_average_window=24,
            window_count=176,
            average_validation_return=-0.001,
            average_test_return=-0.000834,
            average_benchmark_return=0.000096,
            average_excess_return=-0.000930657,
            test_win_rate=0.0,
            overfit_window_count=108,
            overfit_risk_flags=["aggregate_underperforms_benchmark"],
            backtest_result_ids=["backtest-result:visible"],
            windows=[
                WalkForwardWindow(
                    window_id="walk-forward:visible:window",
                    train_start=now - timedelta(days=20),
                    train_end=now - timedelta(days=15),
                    validation_start=now - timedelta(days=14),
                    validation_end=now - timedelta(days=10),
                    test_start=now - timedelta(days=9),
                    test_end=now,
                    train_candle_count=120,
                    validation_candle_count=96,
                    test_candle_count=216,
                    validation_backtest_result_id="backtest-result:visible",
                    test_backtest_result_id="backtest-result:visible",
                    validation_return=-0.001,
                    test_return=-0.000834,
                    benchmark_return=0.000096,
                    excess_return=-0.000930657,
                    overfit_flags=["aggregate_underperforms_benchmark"],
                    decision_basis="test",
                )
            ],
            decision_basis="test",
        )
    )
    repository.save_strategy_research_digest(
        StrategyResearchDigest(
            digest_id="strategy-research-digest:visible",
            created_at=now,
            symbol="BTC-USD",
            strategy_card_id="strategy-card:visible",
            strategy_name="BTC strategy visibility candidate",
            strategy_status="ACTIVE",
            hypothesis="Breakout continuation should beat the baseline after costs.",
            paper_shadow_outcome_id="paper-shadow-outcome:visible",
            outcome_grade="FAIL",
            excess_return_after_costs=-0.025,
            recommended_strategy_action="REVISE_STRATEGY",
            top_failure_attributions=["negative_excess_return", "drawdown_breach"],
            lineage_root_card_id="strategy-card:visible",
            lineage_revision_count=1,
            lineage_outcome_count=2,
            lineage_primary_failure_attribution="drawdown_breach",
            lineage_next_research_focus="優先修正 drawdown_breach，再重跑 locked retest。",
            next_research_action="REVISE_STRATEGY",
            autopilot_run_id="research-autopilot-run:visible",
            evidence_artifact_ids=[
                "strategy-card:visible",
                "paper-shadow-outcome:visible",
                "paper-shadow-outcome:visible-revision-quarantine",
                "event-edge:visible",
                "backtest-result:visible",
                "walk-forward:visible",
            ],
            research_summary=(
                "目前策略 BTC strategy visibility candidate：paper-shadow 失敗；"
                "下一步修訂策略。 研究證據：Event edge：樣本 2，after-cost edge -1.14%；"
                "Backtest：策略 -8.72%，benchmark +1.02%；"
                "Walk-forward：excess -0.09%，windows 176。"
            ),
            next_step_rationale="優先修正 回撤超標 (drawdown_breach)，再重跑 locked retest。",
            decision_basis="test",
            strategy_rule_summary=[
                "假說: Digest-only operator hypothesis should own the strategy summary.",
                "訊號: Digest-only operator signal filter.",
                "進場: Digest-only operator entry rule.",
                "風控: Digest-only operator risk control.",
            ],
            decision_id="decision:visible",
            decision_action="HOLD",
            decision_blocked_reason="model_not_beating_baseline",
            decision_research_blockers=["event edge 缺失", "walk-forward overfit risk"],
            decision_reason_summary=(
                "模型證據沒有打贏 naive persistence baseline，因此買進/賣出被擋住。 "
                "主要研究阻擋：event edge 缺失、walk-forward overfit risk。"
            ),
        )
    )


def _seed_visible_revision_candidate(repository: JsonFileRepository, now: datetime) -> None:
    revision = StrategyCard(
        card_id="strategy-card:visible-revision",
        created_at=now,
        strategy_name="BTC strategy visibility candidate revision",
        strategy_family="breakout_reversal",
        version="v2.rev1",
        status="DRAFT",
        symbols=["BTC-USD"],
        hypothesis="Revision should address negative_excess_return from the failed paper-shadow outcome.",
        signal_description="Revision adds stronger baseline-edge confirmation before breakout entry.",
        entry_rules=[
            "突破前高且成交量放大",
            "Require positive after-cost edge versus the active baseline suite before simulated entry.",
        ],
        exit_rules=["跌回突破區間"],
        risk_rules=["Block promotion until the revised card beats no-trade and persistence baselines."],
        parameters={
            "revision_source_outcome_id": "paper-shadow-outcome:visible",
            "revision_failure_attributions": ["negative_excess_return"],
            "minimum_after_cost_edge": 0.01,
        },
        data_requirements=["market_candles:BTC-USD:1h"],
        feature_snapshot_ids=[],
        backtest_result_ids=[],
        walk_forward_validation_ids=[],
        event_edge_evaluation_ids=[],
        parent_card_id="strategy-card:visible",
        author="codex-strategy-evolution",
        decision_basis="paper_shadow_strategy_revision_candidate",
    )
    agenda = ResearchAgenda(
        agenda_id="research-agenda:visible-revision",
        created_at=now,
        symbol="BTC-USD",
        title="Revision test for BTC strategy visibility candidate",
        hypothesis="Retest the DRAFT revision against paper-shadow failure attribution.",
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


def _seed_visible_revision_retest_scaffold(repository: JsonFileRepository, now: datetime) -> None:
    trial = ExperimentTrial(
        trial_id="experiment-trial:visible-revision-retest",
        created_at=now,
        strategy_card_id="strategy-card:visible-revision",
        trial_index=1,
        status="PENDING",
        symbol="BTC-USD",
        seed=7,
        dataset_id="research-dataset:visible-revision-retest",
        backtest_result_id=None,
        walk_forward_validation_id=None,
        event_edge_evaluation_id=None,
        prompt_hash=None,
        code_hash=None,
        parameters={
            "revision_retest_protocol": "pr14-v1",
            "revision_retest_source_card_id": "strategy-card:visible-revision",
            "revision_source_outcome_id": "paper-shadow-outcome:visible",
            "revision_parent_card_id": "strategy-card:visible",
        },
        metric_summary={},
        failure_reason=None,
        started_at=now,
        completed_at=None,
        decision_basis="revision_retest_scaffold",
    )
    split = SplitManifest(
        manifest_id="split-manifest:visible-revision-retest",
        created_at=now,
        symbol="BTC-USD",
        strategy_card_id="strategy-card:visible-revision",
        dataset_id="research-dataset:visible-revision-retest",
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


def _seed_visible_revision_retest_autopilot_run(repository: JsonFileRepository, now: datetime) -> None:
    repository.save_research_autopilot_run(
        ResearchAutopilotRun(
            run_id="research-autopilot-run:visible-revision-retest",
            created_at=now,
            symbol="BTC-USD",
            agenda_id="research-agenda:visible-revision",
            strategy_card_id="strategy-card:visible-revision",
            experiment_trial_id="experiment-trial:visible-revision-retest",
            locked_evaluation_id="locked-evaluation:visible-revision-retest",
            leaderboard_entry_id="leaderboard-entry:visible-revision-retest",
            strategy_decision_id=None,
            paper_shadow_outcome_id="paper-shadow-outcome:visible-revision-retest",
            steps=[
                {
                    "name": "revision_card",
                    "status": "completed",
                    "artifact_id": "strategy-card:visible-revision",
                },
                {
                    "name": "paper_shadow_outcome",
                    "status": "completed",
                    "artifact_id": "paper-shadow-outcome:visible-revision-retest",
                },
            ],
            loop_status="BLOCKED",
            next_research_action="REPAIR_EVIDENCE_CHAIN",
            blocked_reasons=["locked_evaluation_not_rankable"],
            decision_basis="research_paper_autopilot_loop",
        )
    )


def _seed_visible_strategy_lineage(repository: JsonFileRepository, now: datetime) -> None:
    repository.save_paper_shadow_outcome(
        PaperShadowOutcome(
            outcome_id="paper-shadow-outcome:visible-revision-quarantine",
            created_at=now,
            leaderboard_entry_id="leaderboard-entry:visible-revision-retest",
            evaluation_id="locked-evaluation:visible-revision-retest",
            strategy_card_id="strategy-card:visible-revision",
            trial_id="experiment-trial:visible-revision-retest",
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
    )


def _seed_visible_second_generation_strategy_lineage(repository: JsonFileRepository, now: datetime) -> None:
    second_revision = StrategyCard(
        card_id="strategy-card:visible-second-revision",
        created_at=now,
        strategy_name="BTC strategy visibility second revision",
        strategy_family="breakout_reversal",
        version="v2.rev2",
        status="DRAFT",
        symbols=["BTC-USD"],
        hypothesis="Second revision should inherit the original visible strategy lineage.",
        signal_description="Second revision tightens risk after the first revised shadow failed.",
        entry_rules=["突破前高且成交量放大", "Require second-generation risk confirmation."],
        exit_rules=["跌回突破區間", "Stop when second-generation drawdown guard triggers."],
        risk_rules=["Block promotion until recursive lineage shows repaired failure attributions."],
        parameters={
            "revision_source_outcome_id": "paper-shadow-outcome:visible-revision-quarantine",
            "revision_failure_attributions": ["drawdown_breach", "weak_baseline_edge"],
            "minimum_after_cost_edge": 0.015,
        },
        data_requirements=["market_candles:BTC-USD:1h"],
        feature_snapshot_ids=[],
        backtest_result_ids=[],
        walk_forward_validation_ids=[],
        event_edge_evaluation_ids=[],
        parent_card_id="strategy-card:visible-revision",
        author="codex-strategy-evolution",
        decision_basis="paper_shadow_strategy_revision_candidate",
    )
    repository.save_strategy_card(second_revision)
    repository.save_paper_shadow_outcome(
        PaperShadowOutcome(
            outcome_id="paper-shadow-outcome:visible-second-revision-quarantine",
            created_at=now,
            leaderboard_entry_id="leaderboard-entry:visible-second-revision-retest",
            evaluation_id="locked-evaluation:visible-second-revision-retest",
            strategy_card_id=second_revision.card_id,
            trial_id="experiment-trial:visible-second-revision-retest",
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
    )


def _seed_visible_malicious_strategy_lineage(repository: JsonFileRepository, now: datetime) -> None:
    revision = StrategyCard(
        card_id="strategy-card:visible-malicious-revision",
        created_at=now,
        strategy_name='Visible <script>alert("name")</script> revision',
        strategy_family="breakout_reversal",
        version="v2.rev-xss",
        status="DRAFT",
        symbols=["BTC-USD"],
        hypothesis='Visible repair <script>alert("hypothesis")</script>',
        signal_description="Malicious display fixture.",
        entry_rules=[],
        exit_rules=[],
        risk_rules=[],
        parameters={
            "revision_source_outcome_id": 'paper-shadow-outcome:<script>alert("source")</script>',
            "revision_failure_attributions": ['weak_baseline_edge<script>alert("fix")</script>'],
        },
        data_requirements=["market_candles:BTC-USD:1h"],
        feature_snapshot_ids=[],
        backtest_result_ids=[],
        walk_forward_validation_ids=[],
        event_edge_evaluation_ids=[],
        parent_card_id="strategy-card:visible",
        author="codex-strategy-evolution",
        decision_basis="paper_shadow_strategy_revision_candidate",
    )
    repository.save_strategy_card(revision)


def _seed_distractor_strategy_research_without_run(repository: JsonFileRepository, now: datetime) -> None:
    card = replace(
        _visible_strategy_card(now),
        card_id="strategy-card:distractor",
        created_at=now,
        strategy_name="Distractor BTC strategy",
        hypothesis="Distractor strategy must not be mixed into the visible autopilot chain.",
    )
    trial = replace(
        _visible_trial(now, card),
        trial_id="experiment-trial:distractor",
        created_at=now,
    )
    evaluation = replace(
        _visible_evaluation(now, card, trial),
        evaluation_id="locked-evaluation:distractor",
        created_at=now,
        alpha_score=0.99,
        gate_metrics={"alpha_score": 0.99, "distractor_metric": 1},
    )
    entry = replace(
        _visible_leaderboard(now, card, trial, evaluation),
        entry_id="leaderboard-entry:distractor",
        created_at=now,
        alpha_score=0.99,
    )
    outcome = replace(
        _visible_shadow_outcome(now, entry),
        outcome_id="paper-shadow-outcome:distractor",
        created_at=now,
        failure_attributions=["distractor_shadow"],
        recommended_strategy_action="QUARANTINE_STRATEGY",
    )
    agenda = replace(
        _visible_agenda(now, card),
        agenda_id="research-agenda:distractor",
        created_at=now,
        title="Distractor research agenda",
        hypothesis="Distractor agenda must not be mixed into the visible autopilot chain.",
        strategy_card_ids=[card.card_id],
    )
    repository.save_strategy_card(card)
    repository.save_experiment_trial(trial)
    repository.save_locked_evaluation_result(evaluation)
    repository.save_leaderboard_entry(entry)
    repository.save_paper_shadow_outcome(outcome)
    repository.save_research_agenda(agenda)


def test_operator_console_renders_required_pages_read_only(tmp_path):
    now = datetime(2026, 4, 25, 1, 30, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_strategy_decision(_decision(now))
    repository.save_portfolio_snapshot(_portfolio(now))
    repository.save_risk_snapshot(_risk(now))
    repository.save_control_event(_control_event(now))
    repository.save_automation_run(_automation_run(now))
    repository.save_notification_artifact(_notification(now))

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)

    overview = render_operator_console_page(snapshot, page="overview")
    assert 'lang="zh-Hant"' in overview
    assert "Operator console sections" in overview
    assert "買進" in overview
    assert "Paper-only" in overview
    assert "Automation Run" in overview
    assert "automation-run:test" in overview
    assert "Notifications" in overview
    assert "notification:test" in overview
    assert "買進/賣出訊號被擋" in overview
    assert "forecast" in overview
    assert "decision:test" in overview
    assert "<form" not in overview.lower()

    for page_title, page in [
        ("決策", "decisions"),
        ("投資組合", "portfolio"),
        ("研究", "research"),
        ("健康 / 修復", "health"),
        ("控制", "control"),
    ]:
        html = render_operator_console_page(snapshot, page=page)
        assert page_title in html
        assert "<form" not in html.lower()

    control = render_operator_console_page(snapshot, page="control")
    assert "目前控制狀態" in control
    assert "停止新進場" in control
    assert "Audit Log" in control
    assert "測試用停止新進場控制。" in control
    assert "operator-control" in control
    assert "submit_order" not in control


def test_portfolio_page_shows_nav_pnl_exposure_drawdown_and_risk_gates(tmp_path):
    now = datetime(2026, 4, 25, 1, 30, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_portfolio_snapshot(_portfolio(now))
    repository.save_risk_snapshot(_risk(now))

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    html = render_operator_console_page(snapshot, page="portfolio")

    assert "NAV / Cash / PnL" in html
    assert "$20,000.00" in html
    assert "Realized PnL" in html
    assert "Unrealized PnL" in html
    assert "$1,000.00" in html
    assert "Drawdown" in html
    assert "Current：6.00%" in html
    assert "Max：8.00%" in html
    assert "Max：2.00%" not in html
    assert "Exposure" in html
    assert "Gross：50.00%" in html
    assert "Risk Gates" in html
    assert "Position" in html
    assert "40.00%" in html
    assert "Gross exposure" in html
    assert "45.00%" in html
    assert "Reduce-risk drawdown" in html
    assert "Stop-new-entries drawdown" in html
    assert "gross_exposure_above_limit" in html
    assert "drawdown_reduce_risk" in html
    assert "Avg Price" in html
    assert "Market Price" in html


def test_health_page_shows_blocking_findings_and_repair_request_detail(tmp_path):
    now = datetime(2026, 4, 25, 1, 30, tzinfo=UTC)
    JsonFileRepository(tmp_path).save_repair_request(_repair_request(now))

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    html = render_operator_console_page(snapshot, page="health")

    assert "健康狀態" in html
    assert "阻塞項目" in html
    assert "missing_latest_forecast" in html
    assert "repair_required：true" in html
    assert "修復佇列" in html
    assert "修復請求詳情" in html
    assert "repair:test" in html
    assert "待處理 (pending)" in html
    assert ".codex/repair_requests/pending/repair_test.md" in html
    assert "forecasts.jsonl" in html
    assert "provider_runs.jsonl" in html
    assert "python -m pytest -q" in html
    assert "health-check returns healthy" in html
    assert "<form" not in html.lower()


def test_health_page_shows_repair_request_status_reason(tmp_path):
    now = datetime(2026, 5, 1, 8, 30, tzinfo=UTC)
    resolved = replace(
        _repair_request(now),
        status="resolved",
        status_updated_at=now + timedelta(minutes=5),
        status_reason="health-check returned healthy after runtime refresh",
    )
    JsonFileRepository(tmp_path).save_repair_request(resolved)

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    html = render_operator_console_page(snapshot, page="health")

    assert "已解決 (resolved)" in html
    assert "health-check returned healthy after runtime refresh" in html
    assert "2026-05-01" in html


def test_health_page_renders_when_repair_request_log_is_corrupt(tmp_path):
    now = datetime(2026, 4, 25, 1, 30, tzinfo=UTC)
    (tmp_path / "repair_requests.jsonl").write_text("{bad json\n", encoding="utf-8")

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    html = render_operator_console_page(snapshot, page="health")

    assert "健康狀態" in html
    assert "阻塞項目" in html
    assert "bad_json_row" in html
    assert "repair_requests.jsonl" in html
    assert "repair_required：true" in html
    assert "目前沒有 repair request prompt 可檢查。" in html
    assert "<form" not in html.lower()


def test_decision_timeline_shows_reason_evidence_and_invalidation(tmp_path):
    now = datetime(2026, 4, 25, 1, 30, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_strategy_decision(_decision(now))

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    html = render_operator_console_page(snapshot, page="decisions")

    assert "最新決策" in html
    assert "Decision Timeline" in html
    assert "測試用 paper-only BUY 決策。" in html
    assert "Evidence Links" in html
    assert "Forecast: <code>forecast:test</code>" in html
    assert "Score: <code>score:test</code>" in html
    assert "Baseline: <code>baseline:test</code>" in html
    assert "Invalidation Conditions" in html
    assert "health-check blocking" in html
    assert "Blocked reason" in html


def test_decision_timeline_orders_newest_first_and_shows_review_ids(tmp_path):
    now = datetime(2026, 4, 25, 1, 30, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_strategy_decision(_blocked_decision(now))
    repository.save_strategy_decision(_decision(now.replace(hour=2)))

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    html = render_operator_console_page(snapshot, page="decisions")

    assert html.index("買進 / BTC-USD") < html.index("持有 / BTC-USD")
    assert "Review: <code>review:blocked</code>" in html
    assert "research_backtest_missing" in html


def test_research_page_surfaces_strategy_hypothesis_gates_shadow_and_autopilot(tmp_path):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_strategy_decision(_decision(now))
    _seed_visible_strategy_research(repository, now)

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    html = render_operator_console_page(snapshot, page="research")

    assert "目前策略假設" in html
    assert "策略研究結論" in html
    assert (
        "目前策略 BTC strategy visibility candidate：paper-shadow 失敗 (FAIL)，扣成本超額報酬 -2.50%，"
        "失敗歸因 負超額報酬 (negative_excess_return), 突破後反轉 (breakout_reversed)；下一步 修訂策略 (REVISE_STRATEGY)。"
    ) in html
    assert "BTC strategy visibility candidate" in html
    assert "Breakout continuation should beat the baseline after costs." in html
    assert "Status 啟用 (ACTIVE)" in html
    assert "進場規則" in html
    assert "突破前高且成交量放大" in html
    assert "Evidence Gates" in html
    assert "locked-evaluation:visible" in html
    assert "alpha_score" in html
    assert "0.2100" in html
    assert "Leaderboard" in html
    assert "leaderboard-entry:visible" in html
    leaderboard_section = html[html.index("Leaderboard") : html.index("Paper-shadow 歸因")]
    assert "Promotion：候選策略 (CANDIDATE)" in leaderboard_section
    assert "Paper-shadow 歸因" in html
    paper_shadow_section = html[html.index("Paper-shadow 歸因") : html.index("策略規則")]
    assert "Grade：失敗 (FAIL)" in paper_shadow_section
    assert "Recommended：修訂策略 (REVISE_STRATEGY)" in paper_shadow_section
    assert "負超額報酬 (negative_excess_return)" in paper_shadow_section
    assert "突破後反轉 (breakout_reversed)" in paper_shadow_section
    assert "negative_excess_return" in html
    assert "下一步研究動作" in html
    assert "REVISE_STRATEGY" in html
    assert "research-autopilot-run:visible" in html
    assert "<form" not in html.lower()


def test_operator_console_surfaces_strategy_research_digest_in_research_and_overview(tmp_path):
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_strategy_decision(_decision(now))
    _seed_visible_strategy_research(repository, now)
    _seed_visible_strategy_research_digest(repository, now + timedelta(minutes=15))

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    research_html = render_operator_console_page(snapshot, page="research")
    overview_html = render_operator_console_page(snapshot, page="overview")

    assert snapshot.latest_strategy_research_digest is not None
    assert snapshot.latest_strategy_research_digest.digest_id == "strategy-research-digest:visible"
    for html in (research_html, overview_html):
        assert "策略研究摘要" in html
        assert "strategy-research-digest:visible" in html
        assert "目前策略 BTC strategy visibility candidate：paper-shadow 失敗；下一步修訂策略。" in html
        assert "Event edge：樣本 2，after-cost edge -1.14%" in html
        assert "Backtest：策略 -8.72%，benchmark +1.02%" in html
        assert "Walk-forward：excess -0.09%，windows 176" in html
        assert "優先修正 回撤超標 (drawdown_breach)，再重跑 locked retest。" in html
        assert "負超額報酬 (negative_excess_return), 回撤超標 (drawdown_breach)" in html
        assert "paper-shadow-outcome:visible-revision-quarantine" in html
        assert "event-edge:visible" in html
        assert "backtest-result:visible" in html
        assert "walk-forward:visible" in html
        digest_start = html.index("策略研究摘要")
        digest_section = html[digest_start : html.index("<p>證據", digest_start)]
        assert "摘要 ID" in digest_section
        assert "下一步理由" in digest_section
        assert "失敗集中" in digest_section
        assert "目前決策阻擋" in digest_section
        assert "HOLD" in digest_section
        assert "model_not_beating_baseline" in digest_section
        assert "event edge 缺失" in digest_section
        assert "walk-forward overfit risk" in digest_section
        assert "策略證據指標" in digest_section
        assert "Event edge" in digest_section
        assert "樣本 2" in digest_section
        assert "after-cost edge -1.14%" in digest_section
        assert "Backtest" in digest_section
        assert "策略 -8.72%" in digest_section
        assert "benchmark 1.02%" in digest_section
        assert "Walk-forward" in digest_section
        assert "excess -0.09%" in digest_section
        assert "windows 176" in digest_section
        metric_section = html[html.index("策略證據指標", digest_start) : html.index("<p>證據", digest_start)]
        assert "&lt;code&gt;" not in metric_section
        assert "<code>event-edge:visible</code>" in metric_section
        assert "<code>backtest-result:visible</code>" in metric_section
        assert "<code>walk-forward:visible</code>" in metric_section
        assert "策略規則摘要" in digest_section
        assert "Digest strategy rules" not in digest_section
        assert "Failure concentration" not in digest_section
        rules_start = html.index("策略規則摘要")
        rules_section = html[rules_start : html.index("證據", rules_start)]
        assert "Digest-only operator hypothesis should own the strategy summary." in rules_section
        assert "Digest-only operator signal filter." in rules_section
        assert "Digest-only operator entry rule." in rules_section
        assert "Digest-only operator risk control." in rules_section
        assert "single-trial max position 10%" not in rules_section


def test_research_page_uses_autopilot_linked_chain_instead_of_latest_symbol_artifacts(tmp_path):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_distractor_strategy_research_without_run(repository, now + timedelta(minutes=5))

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    html = render_operator_console_page(snapshot, page="research")

    assert "research-autopilot-run:visible" in html
    assert "strategy-card:visible" in html
    assert "leaderboard-entry:visible" in html
    assert "locked-evaluation:visible" in html
    assert "paper-shadow-outcome:visible" in html
    assert "BTC strategy visibility candidate" in html
    assert "negative_excess_return" in html
    assert "Distractor BTC strategy" not in html
    assert "leaderboard-entry:distractor" not in html
    assert "locked-evaluation:distractor" not in html
    assert "distractor_shadow" not in html


def test_operator_console_shows_strategy_revision_candidate(tmp_path):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_revision_candidate(repository, now + timedelta(minutes=10))

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    research_html = render_operator_console_page(snapshot, page="research")
    overview_html = render_operator_console_page(snapshot, page="overview")

    for html in (research_html, overview_html):
        assert "策略修正候選" in html
        assert "strategy-card:visible-revision" in html
        assert "paper-shadow-outcome:visible" in html
        assert "research-agenda:visible-revision" in html
        assert "Require positive after-cost edge" in html
    assert research_html.count("策略修正候選") == 1
    assert "strategy-card:visible" in research_html
    assert "research-autopilot-run:visible" in research_html


def test_operator_console_shows_strategy_revision_retest_scaffold(tmp_path):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_visible_revision_retest_scaffold(repository, now + timedelta(minutes=20))

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    research_html = render_operator_console_page(snapshot, page="research")
    overview_html = render_operator_console_page(snapshot, page="overview")

    for html in (research_html, overview_html):
        assert "Revision Retest Scaffold" in html
        assert "experiment-trial:visible-revision-retest" in html
        assert "research-dataset:visible-revision-retest" in html
        assert "split-manifest:visible-revision-retest" in html
        assert "baseline 評估 (baseline_evaluation)" in html
        assert "回測結果 (backtest_result)" in html
        assert "鎖定評估結果 (locked_evaluation_result)" in html
        assert "baseline_evaluation" in html
        assert "backtest_result" in html
        assert "locked_evaluation_result" in html


def test_operator_console_shows_revision_retest_task_plan(tmp_path):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_visible_revision_retest_scaffold(repository, now + timedelta(minutes=20))

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    research_html = render_operator_console_page(snapshot, page="research")
    overview_html = render_operator_console_page(snapshot, page="overview")

    for html in (research_html, overview_html):
        assert "下一個 retest 研究任務" in html
        assert "lock_evaluation_protocol" in html
        assert "ready" in html
        assert "<p>Required artifact：<code>成本模型快照 (cost_model_snapshot)</code></p>" in html
        assert "cost_model_snapshot" in html
        assert "lock-evaluation-protocol" in html
        assert "--train-start" in html


def test_operator_console_revision_retest_task_plan_translates_missing_inputs():
    from forecast_loop.operator_console import _revision_retest_task_plan_panel
    from forecast_loop.revision_retest_plan import RevisionRetestTask, RevisionRetestTaskPlan

    plan = RevisionRetestTaskPlan(
        symbol="BTC-USD",
        strategy_card_id="strategy-card:test",
        source_outcome_id="paper-shadow-outcome:test",
        pending_trial_id=None,
        passed_trial_id=None,
        dataset_id=None,
        split_manifest_id=None,
        cost_model_id=None,
        baseline_id=None,
        backtest_result_id=None,
        walk_forward_validation_id=None,
        locked_evaluation_id=None,
        leaderboard_entry_id=None,
        paper_shadow_outcome_id=None,
        next_task_id="lock_evaluation_protocol",
        tasks=[
            RevisionRetestTask(
                task_id="lock_evaluation_protocol",
                title="Lock evaluation protocol",
                status="blocked",
                required_artifact="split_manifest",
                artifact_id=None,
                command_args=None,
                blocked_reason="split_window_inputs_required",
                missing_inputs=["train_start", "validation_end", "storage_dir"],
                rationale="Split windows are required.",
            )
        ],
    )

    html = _revision_retest_task_plan_panel(plan)

    assert "切分清單 (split_manifest)" in html
    assert "訓練開始, 驗證結束, storage 目錄 (train_start, validation_end, storage_dir)" in html


def test_operator_console_revision_retest_task_plan_shows_shadow_readiness_copy():
    from forecast_loop.operator_console import _revision_retest_task_plan_panel
    from forecast_loop.revision_retest_plan import RevisionRetestTask, RevisionRetestTaskPlan

    plan = RevisionRetestTaskPlan(
        symbol="BTC-USD",
        strategy_card_id="strategy-card:test",
        source_outcome_id="paper-shadow-outcome:test",
        pending_trial_id="experiment-trial:test",
        passed_trial_id="experiment-trial:passed",
        dataset_id="market-candles:test",
        split_manifest_id="split-manifest:test",
        cost_model_id="cost-model:test",
        baseline_id="baseline:test",
        backtest_result_id="backtest-result:test",
        walk_forward_validation_id="walk-forward:test",
        locked_evaluation_id="locked-evaluation:test",
        leaderboard_entry_id="leaderboard-entry:test",
        paper_shadow_outcome_id=None,
        next_task_id="record_paper_shadow_outcome",
        tasks=[
            RevisionRetestTask(
                task_id="record_paper_shadow_outcome",
                title="Record paper shadow outcome",
                status="blocked",
                required_artifact="paper_shadow_outcome",
                artifact_id=None,
                command_args=None,
                blocked_reason="shadow_window_observation_required",
                missing_inputs=["window_start", "window_end"],
                rationale=(
                    "The planner does not fabricate future shadow-window returns. "
                    "earliest_window_start=2026-05-01T17:27:48+00:00; "
                    "latest_stored_candle=2026-05-01T18:00:00+00:00; "
                    "first_aligned_window_start=2026-05-01T18:00:00+00:00; "
                    "next_required_window_end=missing; "
                    "candidate_window_ready=false."
                ),
            )
        ],
    )

    html = _revision_retest_task_plan_panel(plan)

    assert "Shadow 觀察 readiness" in html
    assert "最早合法觀察開始" in html
    assert "2026-05-01T17:27:48+00:00" in html
    assert "第一個 K 線對齊開始" in html
    assert "下一個需要的結束 K 線" in html
    assert "候選視窗尚未完整" in html


def test_operator_console_lineage_replacement_retest_panel_shows_shadow_readiness_copy():
    from forecast_loop.operator_console import _lineage_replacement_strategy_panel
    from forecast_loop.revision_retest_plan import RevisionRetestTask, RevisionRetestTaskPlan

    now = datetime(2026, 5, 1, 18, 0, tzinfo=UTC)
    card = StrategyCard(
        card_id="strategy-card:replacement-readiness",
        created_at=now,
        strategy_name="Replacement readiness",
        strategy_family="replacement",
        version="v1",
        status="DRAFT",
        symbols=["BTC-USD"],
        hypothesis="Show replacement retest readiness.",
        signal_description="Replacement signal.",
        entry_rules=["entry"],
        exit_rules=["exit"],
        risk_rules=["risk"],
        parameters={
            "replacement_source_outcome_id": "paper-shadow-outcome:source",
            "replacement_source_lineage_root_card_id": "strategy-card:root",
            "replacement_failure_attributions": ["missing_shadow_window"],
        },
        data_requirements=[],
        feature_snapshot_ids=[],
        backtest_result_ids=[],
        walk_forward_validation_ids=[],
        event_edge_evaluation_ids=[],
        parent_card_id=None,
        author="codex",
        decision_basis="lineage_replacement_strategy_hypothesis",
    )
    plan = RevisionRetestTaskPlan(
        symbol="BTC-USD",
        strategy_card_id=card.card_id,
        source_outcome_id="paper-shadow-outcome:source",
        pending_trial_id="experiment-trial:replacement",
        passed_trial_id="experiment-trial:passed",
        dataset_id="market-candles:replacement",
        split_manifest_id="split-manifest:replacement",
        cost_model_id="cost-model:replacement",
        baseline_id="baseline:replacement",
        backtest_result_id="backtest-result:replacement",
        walk_forward_validation_id="walk-forward:replacement",
        locked_evaluation_id="locked-evaluation:replacement",
        leaderboard_entry_id="leaderboard-entry:replacement",
        paper_shadow_outcome_id=None,
        next_task_id="record_paper_shadow_outcome",
        tasks=[
            RevisionRetestTask(
                task_id="create_revision_retest_scaffold",
                title="Create revision retest scaffold",
                status="completed",
                required_artifact="experiment_trial",
                artifact_id="experiment-trial:replacement",
                command_args=None,
                blocked_reason=None,
                missing_inputs=[],
                rationale="scaffolded",
            ),
            RevisionRetestTask(
                task_id="record_paper_shadow_outcome",
                title="Record paper shadow outcome",
                status="blocked",
                required_artifact="paper_shadow_outcome",
                artifact_id=None,
                command_args=None,
                blocked_reason="shadow_window_observation_required",
                missing_inputs=["window_start", "window_end"],
                rationale=(
                    "The planner does not fabricate future shadow-window returns. "
                    "earliest_window_start=2026-05-01T17:27:48+00:00; "
                    "latest_stored_candle=2026-05-01T18:00:00+00:00; "
                    "first_aligned_window_start=2026-05-01T18:00:00+00:00; "
                    "next_required_window_end=missing; "
                    "candidate_window_ready=false."
                ),
            ),
        ],
    )

    html = _lineage_replacement_strategy_panel(card, plan, None, None)

    assert "Shadow 觀察 readiness" in html
    assert "第一個 K 線對齊開始" in html
    assert "下一個需要的結束 K 線" in html
    assert "候選視窗尚未完整" in html


def test_operator_console_shows_revision_retest_task_run_log(tmp_path):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_visible_revision_retest_scaffold(repository, now + timedelta(minutes=20))
    repository.save_automation_run(
        AutomationRun(
            automation_run_id="automation-run:visible-retest-task",
            started_at=now + timedelta(minutes=30),
            completed_at=now + timedelta(minutes=30),
            status="RETEST_TASK_READY",
            symbol="BTC-USD",
            provider="research",
            command="revision-retest-plan",
            steps=[
                {
                    "name": "revision_card",
                    "status": "completed",
                    "artifact_id": "strategy-card:visible-revision",
                },
                {
                    "name": "source_outcome",
                    "status": "completed",
                    "artifact_id": "paper-shadow-outcome:visible",
                },
                {
                    "name": "lock_evaluation_protocol",
                    "status": "ready",
                    "artifact_id": "split-manifest:visible-revision-retest",
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
            automation_run_id="automation-run:visible-wrong-revision-newer",
            started_at=now + timedelta(minutes=35),
            completed_at=now + timedelta(minutes=35),
            status="RETEST_TASK_BLOCKED",
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
            automation_run_id="automation-run:visible-unrelated-newer",
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

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    research_html = render_operator_console_page(snapshot, page="research")
    overview_html = render_operator_console_page(snapshot, page="overview")

    for html in (research_html, overview_html):
        assert "最新 retest task run log" in html
        assert "automation-run:visible-retest-task" in html
        assert "RETEST_TASK_READY" in html
        assert "revision-retest-plan" in html
        assert "lock_evaluation_protocol" in html
        assert "automation-run:visible-wrong-revision-newer" not in html
    assert "automation-run:visible-unrelated-newer" not in research_html


def test_operator_console_shows_revision_retest_autopilot_run(tmp_path):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_visible_revision_retest_scaffold(repository, now + timedelta(minutes=20))
    _seed_visible_revision_retest_autopilot_run(repository, now + timedelta(minutes=30))
    repository.save_research_autopilot_run(
        ResearchAutopilotRun(
            run_id="research-autopilot-run:visible-parent-newer",
            created_at=now + timedelta(minutes=40),
            symbol="BTC-USD",
            agenda_id="research-agenda:visible",
            strategy_card_id="strategy-card:visible",
            experiment_trial_id="experiment-trial:visible",
            locked_evaluation_id="locked-evaluation:visible",
            leaderboard_entry_id="leaderboard-entry:visible",
            strategy_decision_id=None,
            paper_shadow_outcome_id="paper-shadow-outcome:visible",
            steps=[{"name": "parent_strategy", "status": "completed", "artifact_id": "strategy-card:visible"}],
            loop_status="REVISION_REQUIRED",
            next_research_action="PARENT_SHOULD_NOT_RENDER_AS_REVISION_RETEST",
            blocked_reasons=["parent_strategy_failure"],
            decision_basis="research_paper_autopilot_loop",
        )
    )

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    research_html = render_operator_console_page(snapshot, page="research")
    overview_html = render_operator_console_page(snapshot, page="overview")

    assert snapshot.latest_strategy_revision_retest_autopilot_run is not None
    assert snapshot.latest_strategy_revision_retest_autopilot_run.run_id == "research-autopilot-run:visible-revision-retest"
    for html in (research_html, overview_html):
        assert "最新 revision retest autopilot run" in html
        assert "research-autopilot-run:visible-revision-retest" in html
        assert "修復證據鏈 (REPAIR_EVIDENCE_CHAIN)" in html
        assert "locked_evaluation_not_rankable" in html
        assert "paper-shadow-outcome:visible-revision-retest" in html


def test_operator_console_shows_strategy_lineage_summary(tmp_path):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_visible_strategy_lineage(repository, now + timedelta(minutes=20))

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    research_html = render_operator_console_page(snapshot, page="research")
    overview_html = render_operator_console_page(snapshot, page="overview")

    assert snapshot.latest_strategy_lineage_summary is not None
    assert snapshot.latest_strategy_lineage_summary.revision_count == 1
    for html in (research_html, overview_html):
        assert "策略 lineage" in html
        assert "REVISE_STRATEGY" in html
        assert "QUARANTINE_STRATEGY" in html
        assert "negative_excess_return" in html
        assert "drawdown_breach" in html
        assert "-0.0250" in html
        assert "-0.0800" in html
        assert "paper-shadow-outcome:visible-revision-quarantine" in html


def test_operator_console_lineage_uses_parent_root_when_latest_chain_is_revision(tmp_path):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_visible_revision_retest_scaffold(repository, now + timedelta(minutes=20))
    _seed_visible_revision_retest_autopilot_run(repository, now + timedelta(minutes=30))
    _seed_visible_strategy_lineage(repository, now + timedelta(minutes=40))

    summary = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now).latest_strategy_lineage_summary

    assert summary is not None
    assert summary.root_card_id == "strategy-card:visible"
    assert summary.revision_card_ids == ["strategy-card:visible-revision"]
    assert summary.outcome_count == 2
    assert summary.action_counts == {"QUARANTINE_STRATEGY": 1, "REVISE_STRATEGY": 1}
    assert summary.best_excess_return_after_costs == -0.025


def test_operator_console_strategy_lineage_includes_multi_generation_revisions(tmp_path):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_visible_strategy_lineage(repository, now + timedelta(minutes=20))
    _seed_visible_second_generation_strategy_lineage(repository, now + timedelta(minutes=30))

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    research_html = render_operator_console_page(snapshot, page="research")
    overview_html = render_operator_console_page(snapshot, page="overview")

    assert snapshot.latest_strategy_lineage_summary is not None
    assert snapshot.latest_strategy_lineage_summary.root_card_id == "strategy-card:visible"
    assert snapshot.latest_strategy_lineage_summary.revision_card_ids == [
        "strategy-card:visible-revision",
        "strategy-card:visible-second-revision",
    ]
    assert [(node.card_id, node.parent_card_id, node.depth) for node in snapshot.latest_strategy_lineage_summary.revision_nodes] == [
        ("strategy-card:visible-revision", "strategy-card:visible", 1),
        ("strategy-card:visible-second-revision", "strategy-card:visible-revision", 2),
    ]
    assert snapshot.latest_strategy_lineage_summary.outcome_count == 3
    assert snapshot.latest_strategy_lineage_summary.action_counts == {
        "QUARANTINE_STRATEGY": 2,
        "REVISE_STRATEGY": 1,
    }
    assert snapshot.latest_strategy_lineage_summary.failure_attribution_counts == {
        "breakout_reversed": 1,
        "drawdown_breach": 2,
        "negative_excess_return": 2,
        "weak_baseline_edge": 1,
    }
    for html in (research_html, overview_html):
        if html is overview_html:
            assert "Paper-shadow：修訂策略 (REVISE_STRATEGY) / 失敗 (FAIL)" in html
        action_start = html.index("Action counts")
        action_end = html.index("Failure attribution", action_start)
        action_count_section = html[action_start:action_end]
        assert "隔離策略 (QUARANTINE_STRATEGY)" in action_count_section
        assert "修訂策略 (REVISE_STRATEGY)" in action_count_section
        attribution_start = html.index("Failure attribution", action_end)
        attribution_count_section = html[attribution_start : attribution_start + 500]
        assert "回撤超標 (drawdown_breach)" in attribution_count_section
        assert "基準優勢不足 (weak_baseline_edge)" in attribution_count_section
        assert "Revision Tree" in html
        assert "Depth 2" in html
        assert "Parent strategy-card:visible-revision" in html
        assert "Name BTC strategy visibility second revision" in html
        assert "草稿 (DRAFT)" in html
        assert "Hypothesis Second revision should inherit the original visible strategy lineage." in html
        assert "Source paper-shadow-outcome:visible-revision-quarantine" in html
        assert "Fixes 回撤超標 (drawdown_breach), 基準優勢不足 (weak_baseline_edge)" in html
        assert "表現結論" in html
        assert "改善 0 / 惡化 2 / 未知 0" in html
        assert "主要失敗 回撤超標 (drawdown_breach)" in html
        assert "最新動作 隔離策略 (QUARANTINE_STRATEGY)" in html
        assert "下一步研究焦點" in html
        assert "停止加碼此 lineage，優先研究 回撤超標 (drawdown_breach) 的修正或新策略。" in html
        assert "表現軌跡" in html
        assert "Outcome paper-shadow-outcome:visible-second-revision-quarantine" in html
        assert "Card strategy-card:visible-second-revision" in html
        assert "Excess -0.1100" in html
        assert "Delta -0.0300" in html
        assert "惡化" in html
        assert "weak_baseline_edge" in html
        assert "paper-shadow-outcome:visible-second-revision-quarantine" in html
        assert "-0.1100" in html


def test_operator_console_lineage_research_agenda_visibility(tmp_path):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_visible_strategy_lineage(repository, now + timedelta(minutes=20))
    _seed_visible_second_generation_strategy_lineage(repository, now + timedelta(minutes=30))
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

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    html = render_operator_console_page(snapshot, page="research")

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
    assert "<p>Required artifact：<code>策略卡 (strategy_card)</code></p>" in html
    assert "strategy_lineage_research_agenda" in html
    assert "停止加碼此 lineage" in html
    assert "drawdown_breach" in html


def test_operator_console_run_steps_translate_lineage_blocked_context():
    from forecast_loop.operator_console import _automation_steps

    run = AutomationRun(
        automation_run_id="automation-run:lineage-blocked",
        started_at=datetime(2026, 5, 1, 9, 0, tzinfo=UTC),
        completed_at=datetime(2026, 5, 1, 9, 0, tzinfo=UTC),
        status="LINEAGE_RESEARCH_TASK_BLOCKED",
        symbol="BTC-USD",
        provider="research",
        command="lineage-research-plan",
        steps=[
            {
                "name": "next_task_blocked_reason",
                "status": "blocked",
                "artifact_id": "cross_sample_autopilot_run_missing",
            },
            {
                "name": "next_task_missing_inputs",
                "status": "blocked",
                "artifact_id": "locked_evaluation, walk_forward_validation, paper_shadow_outcome, research_autopilot_run",
            },
        ],
        health_check_id=None,
        decision_id=None,
        repair_request_id=None,
        decision_basis="test",
    )

    html = _automation_steps(run)

    assert "下一個任務阻擋原因" in html
    assert "缺少證據輸入" in html
    assert "缺少 cross-sample autopilot run" in html
    assert "cross_sample_autopilot_run_missing" in html
    assert "鎖定評估, walk-forward 驗證, paper-shadow outcome, research autopilot run" in html
    assert "locked_evaluation, walk_forward_validation, paper_shadow_outcome, research_autopilot_run" in html
    assert "next_task_blocked_reason" not in html
    assert "next_task_missing_inputs" not in html


def test_operator_console_run_steps_translate_revision_retest_context():
    from forecast_loop.operator_console import _automation_steps

    run = AutomationRun(
        automation_run_id="automation-run:revision-retest",
        started_at=datetime(2026, 5, 1, 9, 0, tzinfo=UTC),
        completed_at=datetime(2026, 5, 1, 9, 0, tzinfo=UTC),
        status="RETEST_TASK_READY",
        symbol="BTC-USD",
        provider="research",
        command="revision-retest-plan",
        steps=[
            {"name": "revision_card", "status": "completed", "artifact_id": "strategy-card:test"},
            {"name": "source_outcome", "status": "completed", "artifact_id": "paper-shadow-outcome:test"},
            {"name": "lock_evaluation_protocol", "status": "ready", "artifact_id": "split-manifest:test"},
        ],
        health_check_id=None,
        decision_id=None,
        repair_request_id=None,
        decision_basis="test",
    )

    html = _automation_steps(run)

    assert "修正策略卡" in html
    assert "來源 paper-shadow 結果" in html
    assert "鎖定評估協議" in html


def test_operator_console_lineage_task_plan_translates_missing_inputs():
    from forecast_loop.lineage_research_plan import LineageResearchTask, LineageResearchTaskPlan
    from forecast_loop.operator_console import _lineage_research_task_plan_panel

    plan = LineageResearchTaskPlan(
        symbol="BTC-USD",
        agenda_id="research-agenda:test",
        root_card_id="strategy-card:test",
        latest_outcome_id="paper-shadow-outcome:test",
        performance_verdict="needs evidence",
        latest_recommended_strategy_action="RETEST_REVISION",
        next_research_focus="Collect missing evidence.",
        next_task_id="collect_missing_evidence",
        tasks=[
            LineageResearchTask(
                task_id="collect_missing_evidence",
                title="Collect missing evidence",
                status="blocked",
                required_artifact="research_autopilot_run",
                artifact_id=None,
                command_args=None,
                worker_prompt="Collect missing evidence.",
                blocked_reason="evidence_missing",
                missing_inputs=[
                    "locked_evaluation",
                    "walk_forward_validation",
                    "paper_shadow_outcome",
                ],
                rationale="Missing evidence blocks the next task.",
            )
        ],
    )

    html = _lineage_research_task_plan_panel(plan)

    assert (
        "鎖定評估, walk-forward 驗證, paper-shadow outcome "
        "(locked_evaluation, walk_forward_validation, paper_shadow_outcome)"
    ) in html


def test_operator_console_lineage_research_task_run_ignores_stale_run_after_new_outcome(tmp_path):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_visible_strategy_lineage(repository, now + timedelta(minutes=20))
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
    _seed_visible_second_generation_strategy_lineage(repository, now + timedelta(minutes=50))

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    html = render_operator_console_page(snapshot, page="research")

    assert snapshot.latest_lineage_research_task_plan is not None
    assert (
        snapshot.latest_lineage_research_task_plan.latest_outcome_id
        == "paper-shadow-outcome:visible-second-revision-quarantine"
    )
    assert snapshot.latest_lineage_research_task_run is None
    assert "Lineage 下一個研究任務" in html
    assert "最新 lineage task run log" not in html
    assert stale_recorded.automation_run.automation_run_id not in html


def test_operator_console_shows_lineage_replacement_strategy_hypothesis(tmp_path):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_visible_strategy_lineage(repository, now + timedelta(minutes=20))
    _seed_visible_second_generation_strategy_lineage(repository, now + timedelta(minutes=30))
    create_lineage_research_agenda(
        repository=repository,
        created_at=now + timedelta(minutes=40),
        symbol="BTC-USD",
    )
    executed = execute_lineage_research_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=50),
    )

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    html = render_operator_console_page(snapshot, page="research")

    assert snapshot.latest_lineage_replacement_strategy_card is not None
    assert snapshot.latest_lineage_replacement_strategy_card.card_id == executed.created_artifact_ids[0]
    assert "Lineage 替代策略假說" in html
    assert executed.created_artifact_ids[0] in html
    assert "lineage_replacement_strategy_hypothesis" in html
    assert "paper-shadow-outcome:visible-second-revision-quarantine" in html
    replacement_start = html.index("Lineage 替代策略假說")
    replacement_end = html.index("<h4>替代策略假說</h4>", replacement_start)
    replacement_section = html[replacement_start:replacement_end]
    assert "回撤超標 (drawdown_breach)" in replacement_section
    assert "基準優勢不足 (weak_baseline_edge)" in replacement_section
    assert "drawdown_breach" in html
    assert "weak_baseline_edge" in html
    assert "替代策略" in html


def test_operator_console_shows_lineage_cross_sample_validation_agenda(tmp_path):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_visible_strategy_lineage(repository, now + timedelta(minutes=20))
    _seed_visible_second_generation_strategy_lineage(repository, now + timedelta(minutes=30))
    create_lineage_research_agenda(
        repository=repository,
        created_at=now + timedelta(minutes=40),
        symbol="BTC-USD",
    )
    replacement = execute_lineage_research_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=50),
    )
    repository.save_paper_shadow_outcome(
        PaperShadowOutcome(
            outcome_id="paper-shadow-outcome:visible-replacement-pass",
            created_at=now + timedelta(minutes=60),
            leaderboard_entry_id="leaderboard-entry:visible-replacement-pass",
            evaluation_id="locked-evaluation:visible-replacement-pass",
            strategy_card_id=replacement.created_artifact_ids[0],
            trial_id="experiment-trial:visible-replacement-pass",
            symbol="BTC-USD",
            window_start=now - timedelta(hours=24),
            window_end=now,
            observed_return=0.06,
            benchmark_return=0.01,
            excess_return_after_costs=0.04,
            max_adverse_excursion=0.02,
            turnover=1.1,
            outcome_grade="PASS",
            failure_attributions=[],
            recommended_promotion_stage="PAPER_SHADOW_PASSED",
            recommended_strategy_action="PROMOTION_READY",
            blocked_reasons=[],
            notes=["Replacement improved on the first retest sample."],
            decision_basis="test",
        )
    )
    cross_sample = execute_lineage_research_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=70),
    )
    repository.save_paper_shadow_outcome(
        PaperShadowOutcome(
            outcome_id="paper-shadow-outcome:visible-cross-sample-pass",
            created_at=now + timedelta(minutes=80),
            leaderboard_entry_id="leaderboard-entry:visible-cross-sample-pass",
            evaluation_id="locked-evaluation:visible-cross-sample-pass",
            strategy_card_id=replacement.created_artifact_ids[0],
            trial_id="experiment-trial:visible-cross-sample-pass",
            symbol="BTC-USD",
            window_start=now,
            window_end=now + timedelta(hours=24),
            observed_return=0.04,
            benchmark_return=0.01,
            excess_return_after_costs=0.02,
            max_adverse_excursion=0.01,
            turnover=0.9,
            outcome_grade="PASS",
            failure_attributions=[],
            recommended_promotion_stage="PAPER_SHADOW_PASSED",
            recommended_strategy_action="PROMOTION_READY",
            blocked_reasons=[],
            notes=["Cross-sample validation stayed positive."],
            decision_basis="test",
        )
    )
    repository.save_research_autopilot_run(
        ResearchAutopilotRun(
            run_id="research-autopilot-run:visible-cross-sample",
            created_at=now + timedelta(minutes=90),
            symbol="BTC-USD",
            agenda_id=cross_sample.created_artifact_ids[0],
            strategy_card_id=replacement.created_artifact_ids[0],
            experiment_trial_id="experiment-trial:visible-cross-sample-pass",
            locked_evaluation_id="locked-evaluation:visible-cross-sample-pass",
            leaderboard_entry_id="leaderboard-entry:visible-cross-sample-pass",
            strategy_decision_id=None,
            paper_shadow_outcome_id="paper-shadow-outcome:visible-cross-sample-pass",
            steps=[
                {"name": "cross_sample_agenda", "status": "completed", "artifact_id": cross_sample.created_artifact_ids[0]},
                {"name": "paper_shadow_outcome", "status": "completed", "artifact_id": "paper-shadow-outcome:visible-cross-sample-pass"},
            ],
            loop_status="CROSS_SAMPLE_VALIDATION_COMPLETE",
            next_research_action="COMPARE_FRESH_SAMPLE_EDGE",
            blocked_reasons=[],
            decision_basis="research_paper_autopilot_loop",
        )
    )
    repository.save_research_autopilot_run(
        ResearchAutopilotRun(
            run_id="research-autopilot-run:visible-cross-sample-blocked",
            created_at=now + timedelta(minutes=92),
            symbol="BTC-USD",
            agenda_id=cross_sample.created_artifact_ids[0],
            strategy_card_id=replacement.created_artifact_ids[0],
            experiment_trial_id="experiment-trial:visible-cross-sample-blocked",
            locked_evaluation_id="locked-evaluation:visible-cross-sample-blocked",
            leaderboard_entry_id="leaderboard-entry:visible-cross-sample-blocked",
            strategy_decision_id=None,
            paper_shadow_outcome_id="paper-shadow-outcome:visible-cross-sample-missing",
            steps=[],
            loop_status="BLOCKED",
            next_research_action="REPAIR_EVIDENCE_CHAIN",
            blocked_reasons=["missing_paper_shadow_outcome"],
            decision_basis="research_paper_autopilot_loop",
        )
    )
    repository.save_research_agenda(
        ResearchAgenda(
            agenda_id="research-agenda:visible-unrelated-cross-sample",
            created_at=now + timedelta(minutes=95),
            symbol="BTC-USD",
            title="Unrelated cross-sample validation",
            hypothesis="A different same-symbol lineage should not override the visible lineage.",
            priority="HIGH",
            status="OPEN",
            target_strategy_family="other_lineage",
            strategy_card_ids=["strategy-card:visible-unrelated-root"],
            expected_artifacts=["paper_shadow_outcome"],
            acceptance_criteria=["Remain isolated from the current lineage panel."],
            blocked_actions=[],
            decision_basis="lineage_cross_sample_validation_agenda",
        )
    )
    repository.save_research_autopilot_run(
        ResearchAutopilotRun(
            run_id="research-autopilot-run:visible-unrelated-cross-sample",
            created_at=now + timedelta(minutes=100),
            symbol="BTC-USD",
            agenda_id="research-agenda:visible-unrelated-cross-sample",
            strategy_card_id="strategy-card:visible-unrelated-root",
            experiment_trial_id="experiment-trial:visible-unrelated",
            locked_evaluation_id="locked-evaluation:visible-unrelated",
            leaderboard_entry_id="leaderboard-entry:visible-unrelated",
            strategy_decision_id=None,
            paper_shadow_outcome_id="paper-shadow-outcome:visible-unrelated",
            steps=[],
            loop_status="UNRELATED_COMPLETE",
            next_research_action="IGNORE_FOR_CURRENT_LINEAGE",
            blocked_reasons=[],
            decision_basis="research_paper_autopilot_loop",
        )
    )

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    html = render_operator_console_page(snapshot, page="research")

    assert snapshot.latest_lineage_cross_sample_agenda is not None
    assert snapshot.latest_lineage_cross_sample_agenda.agenda_id == cross_sample.created_artifact_ids[0]
    assert snapshot.latest_lineage_cross_sample_autopilot_run is not None
    assert snapshot.latest_lineage_cross_sample_autopilot_run.run_id == "research-autopilot-run:visible-cross-sample"
    assert snapshot.latest_lineage_cross_sample_autopilot_run.loop_status == "CROSS_SAMPLE_VALIDATION_COMPLETE"
    assert "Lineage cross-sample validation agenda" in html
    assert "Strategy cards" in html
    assert "strategy-card:visible" in html
    assert replacement.created_artifact_ids[0] in html
    assert "lineage_cross_sample_validation_agenda" in html
    assert "paper-shadow-outcome:visible-replacement-pass" in html
    assert "Linked autopilot run" in html
    assert "research-autopilot-run:visible-cross-sample" in html
    assert "CROSS_SAMPLE_VALIDATION_COMPLETE" in html
    assert "paper-shadow-outcome:visible-cross-sample-pass" in html
    assert "research-autopilot-run:visible-cross-sample-blocked" not in html
    assert "missing_paper_shadow_outcome" not in html
    assert "locked_evaluation" in html
    assert "walk_forward_validation" in html
    assert "fresh sample" in html


def test_operator_console_shows_lineage_replacement_retest_scaffold(tmp_path):
    from forecast_loop.revision_retest_run_log import record_revision_retest_task_run

    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_visible_strategy_lineage(repository, now + timedelta(minutes=20))
    _seed_visible_second_generation_strategy_lineage(repository, now + timedelta(minutes=30))
    create_lineage_research_agenda(
        repository=repository,
        created_at=now + timedelta(minutes=40),
        symbol="BTC-USD",
    )
    executed = execute_lineage_research_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=50),
    )
    repository.save_research_dataset(
        ResearchDataset(
            dataset_id="research-dataset:visible-replacement-retest",
            created_at=now + timedelta(minutes=55),
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
    scaffolded = execute_revision_retest_next_task(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=60),
        revision_card_id=executed.created_artifact_ids[0],
    )
    inspected = record_revision_retest_task_run(
        repository=repository,
        storage_dir=tmp_path,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=65),
        revision_card_id=executed.created_artifact_ids[0],
    )
    repository.save_research_autopilot_run(
        ResearchAutopilotRun(
            run_id="research-autopilot-run:visible-replacement-retest",
            created_at=now + timedelta(minutes=70),
            symbol="BTC-USD",
            agenda_id="research-agenda:visible-lineage",
            strategy_card_id=executed.created_artifact_ids[0],
            experiment_trial_id=scaffolded.created_artifact_ids[0],
            locked_evaluation_id="locked-evaluation:visible-replacement-retest",
            leaderboard_entry_id="leaderboard-entry:visible-replacement-retest",
            strategy_decision_id=None,
            paper_shadow_outcome_id="paper-shadow-outcome:visible-replacement-retest",
            steps=[
                {"name": "strategy_card", "status": "completed", "artifact_id": executed.created_artifact_ids[0]},
                {"name": "paper_shadow_outcome", "status": "completed", "artifact_id": "paper-shadow-outcome:visible-replacement-retest"},
            ],
            loop_status="COMPLETE",
            next_research_action="UPDATE_LINEAGE_VERDICT",
            blocked_reasons=[],
            decision_basis="research_paper_autopilot_loop",
        )
    )
    repository.save_paper_shadow_outcome(
        PaperShadowOutcome(
            outcome_id="paper-shadow-outcome:visible-replacement-retest",
            created_at=now + timedelta(minutes=75),
            leaderboard_entry_id="leaderboard-entry:visible-replacement-retest",
            evaluation_id="locked-evaluation:visible-replacement-retest",
            strategy_card_id=executed.created_artifact_ids[0],
            trial_id=scaffolded.created_artifact_ids[0],
            symbol="BTC-USD",
            window_start=now - timedelta(hours=24),
            window_end=now,
            observed_return=0.06,
            benchmark_return=0.01,
            excess_return_after_costs=0.04,
            max_adverse_excursion=0.03,
            turnover=1.1,
            outcome_grade="PASS",
            failure_attributions=[],
            recommended_promotion_stage="PAPER_SHADOW_PASSED",
            recommended_strategy_action="PROMOTION_READY",
            blocked_reasons=[],
            notes=["Replacement retest passed its paper-shadow window."],
            decision_basis="test",
        )
    )
    repository.save_research_autopilot_run(
        ResearchAutopilotRun(
            run_id="research-autopilot-run:visible-replacement-generic-cross-sample",
            created_at=now + timedelta(minutes=80),
            symbol="BTC-USD",
            agenda_id="research-agenda:visible-cross-sample-generic",
            strategy_card_id=executed.created_artifact_ids[0],
            experiment_trial_id="experiment-trial:visible-cross-sample-generic",
            locked_evaluation_id="locked-evaluation:visible-cross-sample-generic",
            leaderboard_entry_id="leaderboard-entry:visible-cross-sample-generic",
            strategy_decision_id=None,
            paper_shadow_outcome_id="paper-shadow-outcome:visible-cross-sample-generic",
            steps=[
                {"name": "strategy_card", "status": "completed", "artifact_id": executed.created_artifact_ids[0]},
                {
                    "name": "cross_sample_agenda",
                    "status": "completed",
                    "artifact_id": "research-agenda:visible-cross-sample-generic",
                },
            ],
            loop_status="CROSS_SAMPLE_VALIDATION_COMPLETE",
            next_research_action="COMPARE_FRESH_SAMPLE_EDGE",
            blocked_reasons=[],
            decision_basis="research_paper_autopilot_loop",
        )
    )

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    html = render_operator_console_page(snapshot, page="research")

    assert snapshot.latest_strategy_lineage_summary is not None
    assert (
        snapshot.latest_strategy_lineage_summary.latest_outcome_id
        == "paper-shadow-outcome:visible-replacement-retest"
    )
    assert snapshot.latest_lineage_replacement_strategy_card is not None
    assert snapshot.latest_lineage_replacement_strategy_card.card_id == executed.created_artifact_ids[0]
    assert snapshot.latest_lineage_replacement_retest_task_plan is not None
    assert snapshot.latest_lineage_replacement_retest_task_plan.pending_trial_id == scaffolded.created_artifact_ids[0]
    assert snapshot.latest_lineage_replacement_retest_task_run is not None
    assert snapshot.latest_lineage_replacement_retest_task_run.automation_run_id == inspected.automation_run.automation_run_id
    assert snapshot.latest_lineage_replacement_retest_autopilot_run is not None
    assert snapshot.latest_lineage_replacement_retest_autopilot_run.run_id == "research-autopilot-run:visible-replacement-retest"
    assert "替代策略 Retest Scaffold" in html
    assert "替代策略 Retest Autopilot Run" in html
    assert "Latest retest activity" in html
    assert "research-dataset:visible-replacement-retest" in html
    assert scaffolded.created_artifact_ids[0] in html
    assert inspected.automation_run.automation_run_id in html
    assert inspected.automation_run.status in html
    assert "research-autopilot-run:visible-replacement-retest" in html
    assert "更新 lineage 判定 (UPDATE_LINEAGE_VERDICT)" in html
    assert "lineage_replacement" in html
    assert "Replacement Contributions" in html
    assert f"Replacement {executed.created_artifact_ids[0]}" in html
    assert "Source paper-shadow-outcome:visible-second-revision-quarantine" in html
    assert "Latest paper-shadow-outcome:visible-replacement-retest" in html
    assert "Action 可進入下一階段 (PROMOTION_READY)" in html


def test_operator_console_lineage_research_agenda_ignores_other_lineage(tmp_path):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_visible_strategy_lineage(repository, now + timedelta(minutes=20))
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

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    html = render_operator_console_page(snapshot, page="research")

    assert "Lineage 研究 agenda" not in html
    assert "research-agenda:other-lineage" not in html
    assert "This same-symbol agenda belongs to another lineage." not in html


def test_strategy_lineage_cli_outputs_latest_lineage_summary_json(tmp_path, capsys):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_visible_strategy_lineage(repository, now + timedelta(minutes=20))
    _seed_visible_second_generation_strategy_lineage(repository, now + timedelta(minutes=30))
    repository.save_strategy_card(
        replace(
            _visible_strategy_card(now + timedelta(minutes=35)),
            card_id="strategy-card:eth-distractor",
            strategy_name="ETH distractor revision",
            symbols=["ETH-USD"],
            parent_card_id="strategy-card:visible",
        )
    )
    repository.save_paper_shadow_outcome(
        PaperShadowOutcome(
            outcome_id="paper-shadow-outcome:eth-distractor",
            created_at=now + timedelta(minutes=36),
            leaderboard_entry_id="leaderboard-entry:eth-distractor",
            evaluation_id="locked-evaluation:eth-distractor",
            strategy_card_id="strategy-card:eth-distractor",
            trial_id="experiment-trial:eth-distractor",
            symbol="ETH-USD",
            window_start=now - timedelta(hours=24),
            window_end=now,
            observed_return=0.20,
            benchmark_return=0.01,
            excess_return_after_costs=0.18,
            max_adverse_excursion=0.02,
            turnover=0.5,
            outcome_grade="PASS",
            failure_attributions=[],
            recommended_promotion_stage="PAPER_SHADOW_PASSED",
            recommended_strategy_action="PROMOTE_TO_PAPER",
            blocked_reasons=[],
            notes=["Cross-symbol distractor must not enter BTC lineage CLI output."],
            decision_basis="test",
        )
    )

    assert main(["strategy-lineage", "--storage-dir", str(tmp_path), "--symbol", "BTC-USD"]) == 0
    payload = json.loads(capsys.readouterr().out)

    summary = payload["strategy_lineage"]
    assert summary["root_card_id"] == "strategy-card:visible"
    assert summary["revision_count"] == 2
    assert summary["outcome_count"] == 3
    assert summary["performance_verdict"] == "惡化"
    assert summary["latest_recommended_strategy_action"] == "QUARANTINE_STRATEGY"
    assert summary["next_research_focus"] == "停止加碼此 lineage，優先研究 drawdown_breach 的修正或新策略。"
    assert "paper-shadow-outcome:eth-distractor" not in {
        item["outcome_id"] for item in summary["outcome_nodes"]
    }


def test_strategy_lineage_cli_rejects_missing_storage_without_creating_directory(tmp_path, capsys):
    missing_storage = tmp_path / "typo-storage"

    with pytest.raises(SystemExit) as exc_info:
        main(["strategy-lineage", "--storage-dir", str(missing_storage), "--symbol", "BTC-USD"])

    assert exc_info.value.code == 2
    assert not missing_storage.exists()
    captured = capsys.readouterr()
    assert "storage directory does not exist" in captured.err
    assert "Traceback" not in captured.err


def test_create_lineage_research_agenda_cli_persists_focus_agenda(tmp_path, capsys):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_visible_strategy_lineage(repository, now + timedelta(minutes=20))
    _seed_visible_second_generation_strategy_lineage(repository, now + timedelta(minutes=30))

    assert main(
        [
            "create-lineage-research-agenda",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--created-at",
            "2026-04-29T10:00:00+00:00",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    agenda = payload["research_agenda"]
    assert agenda["symbol"] == "BTC-USD"
    assert agenda["decision_basis"] == "strategy_lineage_research_agenda"
    assert agenda["priority"] == "HIGH"
    assert agenda["strategy_card_ids"] == [
        "strategy-card:visible",
        "strategy-card:visible-revision",
        "strategy-card:visible-second-revision",
    ]
    assert "停止加碼此 lineage" in agenda["hypothesis"]
    assert "drawdown_breach" in agenda["hypothesis"]
    assert (
        payload["strategy_lineage"]["next_research_focus"]
        == "停止加碼此 lineage，優先研究 drawdown_breach 的修正或新策略。"
    )
    assert main(
        [
            "create-lineage-research-agenda",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--created-at",
            "2026-04-29T11:00:00+00:00",
        ]
    ) == 0
    second_payload = json.loads(capsys.readouterr().out)
    assert second_payload["research_agenda"]["agenda_id"] == agenda["agenda_id"]
    lineage_agendas = [
        item for item in repository.load_research_agendas() if item.decision_basis == "strategy_lineage_research_agenda"
    ]
    assert len(lineage_agendas) == 1
    assert lineage_agendas[0].agenda_id == agenda["agenda_id"]


def test_create_lineage_research_agenda_cli_rejects_missing_lineage(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["create-lineage-research-agenda", "--storage-dir", str(tmp_path), "--symbol", "BTC-USD"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "strategy lineage not found for symbol: BTC-USD" in captured.err
    assert "Traceback" not in captured.err


def test_operator_console_strategy_lineage_escapes_revision_change_summary(tmp_path):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_malicious_strategy_lineage(repository, now + timedelta(minutes=10))

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    research_html = render_operator_console_page(snapshot, page="research")
    overview_html = render_operator_console_page(snapshot, page="overview")

    for html in (research_html, overview_html):
        assert '<script>alert("name")</script>' not in html
        assert '<script>alert("hypothesis")</script>' not in html
        assert '<script>alert("source")</script>' not in html
        assert '<script>alert("fix")</script>' not in html
        assert 'Visible &lt;script&gt;alert(&quot;name&quot;)&lt;/script&gt; revision' in html
        assert 'Visible repair &lt;script&gt;alert(&quot;hypothesis&quot;)&lt;/script&gt;' in html
        assert 'paper-shadow-outcome:&lt;script&gt;alert(&quot;source&quot;)&lt;/script&gt;' in html
        assert 'weak_baseline_edge&lt;script&gt;alert(&quot;fix&quot;)&lt;/script&gt;' in html


def test_operator_console_revision_retest_task_plan_falls_back_when_source_missing(tmp_path):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_revision_candidate(repository, now + timedelta(minutes=10))
    (tmp_path / "paper_shadow_outcomes.jsonl").write_text("", encoding="utf-8")

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    research_html = render_operator_console_page(snapshot, page="research")
    overview_html = render_operator_console_page(snapshot, page="overview")

    for html in (research_html, overview_html):
        assert "策略修正候選" in html
        assert "目前沒有可解析的 retest task plan" in html


def test_overview_prioritizes_strategy_research_focus_before_artifact_counts(tmp_path):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_strategy_decision(_decision(now))
    _seed_visible_strategy_research(repository, now)

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)
    overview = render_operator_console_page(snapshot, page="overview")

    assert "策略研究焦點" in overview
    assert overview.index("策略研究焦點") < overview.index("Artifact Counts")
    assert "strategy-card:visible" in overview
    assert "leaderboard-entry:visible" in overview
    assert "REVISE_STRATEGY" in overview


def test_operator_console_cli_renders_one_page(tmp_path, capsys):
    now = datetime(2026, 4, 25, 1, 30, tzinfo=UTC)
    JsonFileRepository(tmp_path).save_strategy_decision(_decision(now))
    output_path = tmp_path / "console-health.html"

    assert (
        main(
            [
                "operator-console",
                "--storage-dir",
                str(tmp_path),
                "--page",
                "health",
                "--output",
                str(output_path),
                "--now",
                "2026-04-25T01:30:00+00:00",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "render_once"
    assert payload["page"] == "health"
    assert output_path.exists()
    assert "健康 / 修復" in output_path.read_text(encoding="utf-8")


def test_operator_console_rejects_non_local_bind_host():
    with pytest.raises(ValueError, match="local-only"):
        validate_local_bind_host("0.0.0.0")


def test_operator_console_uses_ipv6_family_for_ipv6_loopback():
    assert local_address_family_for_host("127.0.0.1") == socket.AF_INET
    assert local_address_family_for_host("localhost") == socket.AF_INET
    assert local_address_family_for_host("::1") == socket.AF_INET6


def test_operator_console_cli_rejects_non_local_host_before_serving(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "operator-console",
                "--storage-dir",
                str(tmp_path),
                "--host",
                "0.0.0.0",
            ]
        )

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "operator-console is local-only" in captured.err


def test_operator_console_requires_existing_storage_dir(tmp_path):
    with pytest.raises(ValueError, match="storage dir does not exist"):
        build_operator_console_snapshot(tmp_path / "missing")
