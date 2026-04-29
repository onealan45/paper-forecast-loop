from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
import socket

import pytest

from forecast_loop.cli import main
from forecast_loop.models import (
    AutomationRun,
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
    RiskSnapshot,
    SplitManifest,
    StrategyCard,
    StrategyDecision,
)
from forecast_loop.operator_console import (
    build_operator_console_snapshot,
    local_address_family_for_host,
    render_operator_console_page,
    validate_local_bind_host,
)
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
    assert "BTC strategy visibility candidate" in html
    assert "Breakout continuation should beat the baseline after costs." in html
    assert "進場規則" in html
    assert "突破前高且成交量放大" in html
    assert "Evidence Gates" in html
    assert "locked-evaluation:visible" in html
    assert "alpha_score" in html
    assert "0.2100" in html
    assert "Leaderboard" in html
    assert "leaderboard-entry:visible" in html
    assert "Paper-shadow 歸因" in html
    assert "negative_excess_return" in html
    assert "下一步研究動作" in html
    assert "REVISE_STRATEGY" in html
    assert "research-autopilot-run:visible" in html
    assert "<form" not in html.lower()


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
        assert "cost_model_snapshot" in html
        assert "lock-evaluation-protocol" in html
        assert "--train-start" in html


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
        assert "REPAIR_EVIDENCE_CHAIN" in html
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
    for html in (research_html, overview_html):
        assert "Revision Tree" in html
        assert "Depth 2" in html
        assert "Parent strategy-card:visible-revision" in html
        assert "Name BTC strategy visibility second revision" in html
        assert "Hypothesis Second revision should inherit the original visible strategy lineage." in html
        assert "Source paper-shadow-outcome:visible-revision-quarantine" in html
        assert "Fixes drawdown_breach, weak_baseline_edge" in html
        assert "表現軌跡" in html
        assert "Outcome paper-shadow-outcome:visible-second-revision-quarantine" in html
        assert "Card strategy-card:visible-second-revision" in html
        assert "Excess -0.1100" in html
        assert "Delta -0.0300" in html
        assert "惡化" in html
        assert "weak_baseline_edge" in html
        assert "paper-shadow-outcome:visible-second-revision-quarantine" in html
        assert "-0.1100" in html


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
