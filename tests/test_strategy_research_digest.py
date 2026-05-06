from datetime import UTC, datetime, timedelta
import json

from forecast_loop.cli import main
from forecast_loop.models import (
    BacktestResult,
    BacktestRun,
    EventEdgeEvaluation,
    ExperimentTrial,
    LeaderboardEntry,
    LockedEvaluationResult,
    PaperShadowOutcome,
    ResearchAgenda,
    ResearchAutopilotRun,
    StrategyDecision,
    StrategyCard,
    StrategyResearchDigest,
    WalkForwardValidation,
    WalkForwardWindow,
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


def _digest_backtest(
    now: datetime,
    *,
    result_id: str = "backtest-result:digest-latest",
    symbol: str = "BTC-USD",
    strategy_return: float = -0.0872,
    benchmark_return: float = 0.0102,
) -> BacktestResult:
    return BacktestResult(
        result_id=result_id,
        backtest_id=f"backtest-run:{result_id}",
        created_at=now,
        symbol=symbol,
        start=now - timedelta(days=30),
        end=now,
        initial_cash=10_000,
        final_equity=9_128,
        strategy_return=strategy_return,
        benchmark_return=benchmark_return,
        max_drawdown=0.0921,
        sharpe=-3.108,
        turnover=0.75,
        win_rate=0.214,
        trade_count=14,
        equity_curve=[],
        decision_basis="test",
    )


def _digest_backtest_run(
    now: datetime,
    *,
    backtest_id: str,
    id_context: str,
    symbol: str = "BTC-USD",
) -> BacktestRun:
    return BacktestRun(
        backtest_id=backtest_id,
        created_at=now,
        symbol=symbol,
        start=now - timedelta(days=30),
        end=now,
        strategy_name="moving_average_trend",
        initial_cash=10_000,
        fee_bps=5,
        slippage_bps=10,
        moving_average_window=3,
        candle_ids=["market-candle:digest"],
        decision_basis=(
            "paper-only moving-average trend backtest using stored candles; "
            f"id_context={id_context}"
        ),
    )


def _digest_walk_forward(
    now: datetime,
    *,
    validation_id: str = "walk-forward:digest-latest",
    symbol: str = "BTC-USD",
    average_excess_return: float = -0.000930657,
) -> WalkForwardValidation:
    window = WalkForwardWindow(
        window_id=f"{validation_id}:window",
        train_start=now - timedelta(days=20),
        train_end=now - timedelta(days=15),
        validation_start=now - timedelta(days=14),
        validation_end=now - timedelta(days=10),
        test_start=now - timedelta(days=9),
        test_end=now,
        train_candle_count=120,
        validation_candle_count=96,
        test_candle_count=216,
        validation_backtest_result_id="backtest-result:digest-latest",
        test_backtest_result_id="backtest-result:digest-latest",
        validation_return=-0.001,
        test_return=-0.000834,
        benchmark_return=0.000096,
        excess_return=average_excess_return,
        overfit_flags=["aggregate_underperforms_benchmark"],
        decision_basis="test",
    )
    return WalkForwardValidation(
        validation_id=validation_id,
        created_at=now,
        symbol=symbol,
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
        average_excess_return=average_excess_return,
        test_win_rate=0.0,
        overfit_window_count=108,
        overfit_risk_flags=["aggregate_underperforms_benchmark"],
        backtest_result_ids=["backtest-result:digest-latest"],
        windows=[window],
        decision_basis="test",
    )


def _digest_event_edge(
    now: datetime,
    *,
    evaluation_id: str = "event-edge:digest-latest",
    symbol: str = "BTC-USD",
    average_excess_return_after_costs: float = -0.011366,
) -> EventEdgeEvaluation:
    return EventEdgeEvaluation(
        evaluation_id=evaluation_id,
        event_family="crypto_flow",
        event_type="CRYPTO_FLOW",
        symbol=symbol,
        created_at=now,
        split="historical_event_sample",
        horizon_hours=24,
        sample_n=2,
        average_forward_return=-0.02,
        average_benchmark_return=-0.008,
        average_excess_return_after_costs=average_excess_return_after_costs,
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


def test_strategy_research_digest_records_decision_blocker_research_artifact_ids(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    _seed_strategy_research_chain(repository, now)
    repository.save_strategy_decision(
        StrategyDecision(
            decision_id="decision:digest-blocker-evidence",
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
            invalidation_conditions=["補齊 decision-blocker research evidence。"],
            reason_summary="主要研究阻擋：event edge 未通過、backtest 未打贏 benchmark。",
            forecast_ids=["forecast:digest"],
            score_ids=["score:digest"],
            review_ids=["review:digest"],
            baseline_ids=["baseline:digest"],
            decision_basis=(
                "action=HOLD; "
                "event_edge=event-edge:blocker-current; "
                "backtest_result=backtest-result:blocker-current; "
                "walk_forward=walk-forward:blocker-current; "
                "event_edge=event-edge:blocker-current"
            ),
        )
    )

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=30),
    )

    assert digest.decision_research_artifact_ids == [
        "event-edge:blocker-current",
        "backtest-result:blocker-current",
        "walk-forward:blocker-current",
    ]
    assert "decision:digest-blocker-evidence" in digest.evidence_artifact_ids
    assert "決策阻擋研究仍未通過" in digest.next_step_rationale
    assert "event edge 未通過、backtest 未打贏 benchmark" in digest.next_step_rationale
    assert "已連結 3 個 blocker evidence" in digest.next_step_rationale
    assert "不是只等待 paper-shadow" in digest.next_step_rationale


def test_strategy_research_digest_does_not_use_decision_blocker_event_edge_as_strategy_metric(
    tmp_path,
):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    _seed_strategy_research_chain(repository, now)
    repository.save_event_edge_evaluation(
        _digest_event_edge(
            now + timedelta(minutes=21),
            evaluation_id="event-edge:blocker-current",
        )
    )
    repository.save_strategy_decision(
        StrategyDecision(
            decision_id="decision:digest-blocker-event-edge",
            created_at=now + timedelta(minutes=22),
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
            invalidation_conditions=["補齊 decision-blocker event edge。"],
            reason_summary=(
                "模型證據沒有打贏 baseline。 "
                "主要研究阻擋：event edge 未通過。"
            ),
            forecast_ids=["forecast:digest"],
            score_ids=["score:digest"],
            review_ids=["review:digest"],
            baseline_ids=["baseline:digest"],
            decision_basis="event_edge=event-edge:blocker-current; flags=research_event_edge_not_passed",
        )
    )

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=30),
    )

    assert digest.decision_research_artifact_ids == ["event-edge:blocker-current"]
    assert "event-edge:blocker-current" not in digest.evidence_artifact_ids
    assert "Event edge：" not in digest.research_summary


def test_strategy_research_digest_does_not_fallback_to_unlinked_event_edge(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    _seed_strategy_research_chain(repository, now)
    repository.save_event_edge_evaluation(
        _digest_event_edge(
            now + timedelta(minutes=21),
            evaluation_id="event-edge:unlinked-latest",
        )
    )

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=30),
    )

    assert "event-edge:unlinked-latest" not in digest.evidence_artifact_ids
    assert "Event edge：" not in digest.research_summary


def test_strategy_research_digest_does_not_use_decision_blocker_backtest_or_walk_forward_as_strategy_metric(
    tmp_path,
):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    _seed_strategy_research_chain(repository, now)
    blocker_backtest = _digest_backtest(
        now + timedelta(minutes=21),
        result_id="backtest-result:blocker-current",
        strategy_return=-0.0777,
        benchmark_return=0.0111,
    )
    repository.save_backtest_run(
        _digest_backtest_run(
            now + timedelta(minutes=21),
            backtest_id=blocker_backtest.backtest_id,
            id_context="decision_blocker_research:run_backtest:backtest_result",
        )
    )
    repository.save_backtest_result(blocker_backtest)
    repository.save_walk_forward_validation(
        _digest_walk_forward(
            now + timedelta(minutes=22),
            validation_id="walk-forward:blocker-current",
            average_excess_return=-0.0066,
        )
    )
    repository.save_strategy_decision(
        StrategyDecision(
            decision_id="decision:digest-blocker-metrics",
            created_at=now + timedelta(minutes=23),
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
            invalidation_conditions=["補齊 decision-blocker research evidence。"],
            reason_summary=(
                "模型證據沒有打贏 baseline。 "
                "主要研究阻擋：backtest 未打贏 benchmark、walk-forward 超額報酬不為正。"
            ),
            forecast_ids=["forecast:digest"],
            score_ids=["score:digest"],
            review_ids=["review:digest"],
            baseline_ids=["baseline:digest"],
            decision_basis=(
                "backtest_result=backtest-result:blocker-current; "
                "walk_forward=walk-forward:blocker-current; "
                "flags=research_backtest_not_beating_benchmark,research_walk_forward_excess_return_not_positive"
            ),
        )
    )

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=30),
    )

    assert digest.decision_research_artifact_ids == [
        "backtest-result:blocker-current",
        "walk-forward:blocker-current",
    ]
    assert "backtest-result:blocker-current" not in digest.evidence_artifact_ids
    assert "walk-forward:blocker-current" not in digest.evidence_artifact_ids
    assert "Backtest（背景參考）：策略 -7.77%" not in digest.research_summary
    assert "Walk-forward（背景參考）：excess -0.66%" not in digest.research_summary


def test_strategy_research_digest_does_not_label_tradeable_buy_evidence_as_blocker_research(
    tmp_path,
):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    _seed_strategy_research_chain(repository, now)
    repository.save_strategy_decision(
        StrategyDecision(
            decision_id="decision:digest-tradeable-buy",
            created_at=now + timedelta(minutes=20),
            symbol="BTC-USD",
            horizon_hours=24,
            action="BUY",
            confidence=0.72,
            evidence_grade="B",
            risk_level="MEDIUM",
            tradeable=True,
            blocked_reason=None,
            recommended_position_pct=0.1,
            current_position_pct=0.0,
            max_position_pct=0.15,
            invalidation_conditions=["edge disappears"],
            reason_summary="研究證據已通過，允許 BUY 模擬決策。",
            forecast_ids=["forecast:digest"],
            score_ids=["score:digest"],
            review_ids=["review:digest"],
            baseline_ids=["baseline:digest"],
            decision_basis=(
                "action=BUY; "
                "event_edge=event-edge:passing-gate; "
                "backtest_result=backtest-result:passing-gate; "
                "walk_forward=walk-forward:passing-gate; "
                "flags=none"
            ),
        )
    )

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=30),
    )

    assert digest.decision_research_artifact_ids == []
    assert "decision:digest-tradeable-buy" in digest.evidence_artifact_ids


def test_strategy_research_digest_does_not_label_risk_stop_evidence_as_blocker_research(
    tmp_path,
):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    _seed_strategy_research_chain(repository, now)
    repository.save_strategy_decision(
        StrategyDecision(
            decision_id="decision:digest-risk-stop",
            created_at=now + timedelta(minutes=20),
            symbol="BTC-USD",
            horizon_hours=24,
            action="STOP_NEW_ENTRIES",
            confidence=None,
            evidence_grade="B",
            risk_level="HIGH",
            tradeable=False,
            blocked_reason="risk_stop_new_entries",
            recommended_position_pct=0.0,
            current_position_pct=0.0,
            max_position_pct=0.15,
            invalidation_conditions=["risk control is lifted"],
            reason_summary="風險控制要求停止新進場；研究 gate 本身沒有阻擋。",
            forecast_ids=["forecast:digest"],
            score_ids=["score:digest"],
            review_ids=["review:digest"],
            baseline_ids=["baseline:digest"],
            decision_basis=(
                "action=STOP_NEW_ENTRIES; "
                "blocked_reason=risk_stop_new_entries; "
                "event_edge=event-edge:passing-gate; "
                "backtest_result=backtest-result:passing-gate; "
                "walk_forward=walk-forward:passing-gate; "
                "flags=none"
            ),
        )
    )

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=30),
    )

    assert digest.decision_research_artifact_ids == []
    assert "decision:digest-risk-stop" in digest.evidence_artifact_ids


def test_strategy_research_digest_surfaces_latest_backtest_and_walk_forward_metrics(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
    _seed_strategy_research_chain(repository, now)
    repository.save_event_edge_evaluation(
        _digest_event_edge(now - timedelta(hours=1), evaluation_id="event-edge:digest-stale")
    )
    repository.save_event_edge_evaluation(_digest_event_edge(now))
    repository.save_event_edge_evaluation(
        _digest_event_edge(now + timedelta(minutes=1), evaluation_id="event-edge:eth", symbol="ETH-USD")
    )
    repository.save_backtest_result(
        _digest_backtest(now - timedelta(hours=1), result_id="backtest-result:digest-stale")
    )
    repository.save_backtest_result(_digest_backtest(now))
    repository.save_backtest_result(
        _digest_backtest(now + timedelta(minutes=1), result_id="backtest-result:eth", symbol="ETH-USD")
    )
    repository.save_walk_forward_validation(
        _digest_walk_forward(now - timedelta(hours=1), validation_id="walk-forward:digest-stale")
    )
    repository.save_walk_forward_validation(_digest_walk_forward(now))
    repository.save_walk_forward_validation(
        _digest_walk_forward(now + timedelta(minutes=1), validation_id="walk-forward:eth", symbol="ETH-USD")
    )

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=5),
    )

    assert "event-edge:digest-latest" not in digest.evidence_artifact_ids
    assert "backtest-result:digest-latest" not in digest.evidence_artifact_ids
    assert "walk-forward:digest-latest" not in digest.evidence_artifact_ids
    assert "event-edge:digest-stale" not in digest.evidence_artifact_ids
    assert "event-edge:eth" not in digest.evidence_artifact_ids
    assert "Event edge：" not in digest.research_summary
    assert "Backtest（背景參考）：策略 -8.72%，benchmark +1.02%" in digest.research_summary
    assert "Walk-forward（背景參考）：excess -0.09%，windows 176" in digest.research_summary
    assert "aggregate_underperforms_benchmark" in digest.research_summary


def test_strategy_research_digest_prefers_decision_blocker_backtest_over_newer_walk_forward_internal_backtest(
    tmp_path,
):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    _seed_strategy_research_chain(repository, now)
    standalone = _digest_backtest(
        now + timedelta(minutes=30),
        result_id="backtest-result:digest-blocker-standalone",
        strategy_return=0.02,
        benchmark_return=0.01,
    )
    internal = _digest_backtest(
        now + timedelta(minutes=31),
        result_id="backtest-result:digest-walk-forward-internal",
        strategy_return=-0.03,
        benchmark_return=0.01,
    )
    repository.save_backtest_run(
        _digest_backtest_run(
            now + timedelta(minutes=30),
            backtest_id=standalone.backtest_id,
            id_context="decision_blocker_research:run_backtest:backtest_result",
        )
    )
    repository.save_backtest_run(
        _digest_backtest_run(
            now + timedelta(minutes=31),
            backtest_id=internal.backtest_id,
            id_context="decision_blocker_research:run_walk_forward_validation:walk_forward_validation",
        )
    )
    repository.save_backtest_result(standalone)
    repository.save_backtest_result(internal)
    repository.save_walk_forward_validation(_digest_walk_forward(now + timedelta(minutes=31)))

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=32),
    )

    assert "backtest-result:digest-blocker-standalone" not in digest.evidence_artifact_ids
    assert "backtest-result:digest-walk-forward-internal" not in digest.evidence_artifact_ids
    assert "Backtest（背景參考）：策略 +2.00%，benchmark +1.00%" in digest.research_summary
    assert "Backtest（背景參考）：策略 -3.00%" not in digest.research_summary


def test_strategy_research_digest_is_point_in_time_for_chain_decision_and_evidence(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
    artifacts = _seed_strategy_research_chain(repository, now)
    repository.save_strategy_decision(
        StrategyDecision(
            decision_id="decision:future-digest",
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
            invalidation_conditions=["future decision should be invisible"],
            reason_summary="Future decision should not leak into a backdated digest.",
            forecast_ids=[],
            score_ids=[],
            review_ids=[],
            baseline_ids=[],
            decision_basis="test",
        )
    )
    repository.save_event_edge_evaluation(_digest_event_edge(now))
    repository.save_event_edge_evaluation(
        _digest_event_edge(now + timedelta(minutes=20), evaluation_id="event-edge:future")
    )

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=1),
    )

    assert digest.strategy_card_id == artifacts["card"].card_id
    assert digest.paper_shadow_outcome_id == artifacts["outcome"].outcome_id
    assert digest.lineage_revision_count == 0
    assert artifacts["revision"].card_id not in digest.evidence_artifact_ids
    assert artifacts["revision_outcome"].outcome_id not in digest.evidence_artifact_ids
    assert digest.decision_id is None
    assert "decision:future-digest" not in digest.evidence_artifact_ids
    assert "event-edge:digest-latest" not in digest.evidence_artifact_ids
    assert "event-edge:future" not in digest.evidence_artifact_ids


def test_strategy_research_digest_keeps_card_shadow_outcome_when_decision_agenda_is_newer(
    tmp_path,
):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    artifacts = _seed_strategy_research_chain(repository, now)
    repository.save_research_agenda(
        ResearchAgenda(
            agenda_id="research-agenda:newer-decision-blocker",
            created_at=now + timedelta(minutes=20),
            symbol="BTC-USD",
            title="Decision blocker research: BTC-USD HOLD",
            hypothesis="Latest decision is blocked by research metrics; keep visible strategy outcome context.",
            priority="HIGH",
            status="OPEN",
            target_strategy_family="breakout_reversal",
            strategy_card_ids=[artifacts["revision"].card_id],
            expected_artifacts=[
                "strategy_decision",
                "event_edge_evaluation",
                "backtest_result",
                "walk_forward_validation",
            ],
            acceptance_criteria=["Remove BUY/SELL blockers before directionality is usable."],
            blocked_actions=["directional_buy_sell_without_research_evidence"],
            decision_basis="decision_blocker_research_agenda",
        )
    )

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=21),
    )

    assert digest.strategy_card_id == artifacts["revision"].card_id
    assert digest.paper_shadow_outcome_id == artifacts["revision_outcome"].outcome_id
    assert digest.outcome_grade == artifacts["revision_outcome"].outcome_grade
    assert digest.recommended_strategy_action == (
        artifacts["revision_outcome"].recommended_strategy_action
    )
    assert artifacts["revision_outcome"].outcome_id in digest.evidence_artifact_ids
    assert "尚未有 paper-shadow 結果" not in digest.research_summary


def test_strategy_research_digest_does_not_let_empty_decision_agenda_mask_current_strategy(
    tmp_path,
):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    artifacts = _seed_strategy_research_chain(repository, now)
    decision = StrategyDecision(
        decision_id="decision:empty-agenda-mask",
        created_at=now + timedelta(minutes=19),
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
        invalidation_conditions=["Keep current strategy visible."],
        reason_summary="Latest decision is blocked, but it should not hide the active strategy.",
        forecast_ids=[],
        score_ids=[],
        review_ids=[],
        baseline_ids=[],
        decision_basis="test",
    )
    repository.save_strategy_decision(decision)
    repository.save_research_agenda(
        ResearchAgenda(
            agenda_id="research-agenda:empty-decision-blocker",
            created_at=now + timedelta(minutes=20),
            symbol="BTC-USD",
            title="Decision blocker research: BTC-USD HOLD",
            hypothesis="Latest decision has blockers but no strategy card ownership.",
            priority="MEDIUM",
            status="OPEN",
            target_strategy_family="decision_blocker_research",
            strategy_card_ids=[],
            expected_artifacts=[
                "strategy_decision",
                "event_edge_evaluation",
                "backtest_result",
                "walk_forward_validation",
            ],
            acceptance_criteria=["Do not hide the active strategy context."],
            blocked_actions=["directional_buy_sell_without_research_evidence"],
            decision_basis="decision_blocker_research_agenda",
        )
    )

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=21),
    )

    assert digest.strategy_card_id == artifacts["revision"].card_id
    assert digest.paper_shadow_outcome_id == artifacts["revision_outcome"].outcome_id
    assert digest.strategy_name == artifacts["revision"].strategy_name
    assert digest.decision_id == decision.decision_id
    assert decision.decision_id in digest.evidence_artifact_ids
    assert digest.strategy_name != "no_strategy_card"
    assert "目前沒有策略卡" not in digest.research_summary


def test_strategy_research_digest_does_not_mask_newer_same_card_retest_waiting_for_shadow(
    tmp_path,
):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    artifacts = _seed_strategy_research_chain(repository, now)
    revision = artifacts["revision"]
    trial = ExperimentTrial(
        trial_id="experiment-trial:same-card-newer-retest",
        created_at=now + timedelta(minutes=21),
        strategy_card_id=revision.card_id,
        trial_index=2,
        status="PASSED",
        symbol="BTC-USD",
        seed=13,
        dataset_id="research-dataset:same-card-newer-retest",
        backtest_result_id="backtest-result:same-card-newer-retest",
        walk_forward_validation_id="walk-forward:same-card-newer-retest",
        event_edge_evaluation_id=None,
        prompt_hash="prompt-same-card-newer-retest",
        code_hash="code-same-card-newer-retest",
        parameters={"revision_retest_protocol": "pr14-v1"},
        metric_summary={"alpha_score": None},
        failure_reason=None,
        started_at=now + timedelta(minutes=20),
        completed_at=now + timedelta(minutes=21),
        decision_basis="test",
    )
    evaluation = LockedEvaluationResult(
        evaluation_id="locked-evaluation:same-card-newer-retest",
        created_at=now + timedelta(minutes=22),
        strategy_card_id=revision.card_id,
        trial_id=trial.trial_id,
        split_manifest_id="split-manifest:same-card-newer-retest",
        cost_model_id="cost-model:same-card-newer-retest",
        baseline_id="baseline:same-card-newer-retest",
        backtest_result_id="backtest-result:same-card-newer-retest",
        walk_forward_validation_id="walk-forward:same-card-newer-retest",
        event_edge_evaluation_id=None,
        passed=False,
        rankable=False,
        alpha_score=None,
        blocked_reasons=["leaderboard_entry_not_rankable"],
        gate_metrics={"holdout_excess_return": -0.01},
        decision_basis="test",
    )
    leaderboard = LeaderboardEntry(
        entry_id="leaderboard-entry:same-card-newer-retest",
        created_at=now + timedelta(minutes=23),
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
    repository.save_experiment_trial(trial)
    repository.save_locked_evaluation_result(evaluation)
    repository.save_leaderboard_entry(leaderboard)
    repository.save_research_agenda(
        ResearchAgenda(
            agenda_id="research-agenda:newer-decision-blocker-after-retest",
            created_at=now + timedelta(minutes=24),
            symbol="BTC-USD",
            title="Decision blocker research after newer retest",
            hypothesis="A newer same-card retest is waiting for shadow outcome.",
            priority="HIGH",
            status="OPEN",
            target_strategy_family="breakout_reversal",
            strategy_card_ids=[revision.card_id],
            expected_artifacts=["strategy_decision", "paper_shadow_outcome"],
            acceptance_criteria=["Wait for the new retest shadow result."],
            blocked_actions=["promote_without_retest_shadow"],
            decision_basis="decision_blocker_research_agenda",
        )
    )

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=25),
    )

    assert digest.strategy_card_id == revision.card_id
    assert digest.paper_shadow_outcome_id is None
    assert leaderboard.entry_id in digest.evidence_artifact_ids
    assert artifacts["revision_outcome"].outcome_id not in digest.evidence_artifact_ids[:5]
    assert digest.next_research_action == "WAIT_FOR_PAPER_SHADOW_OUTCOME"
    assert "等待 paper-shadow 視窗" in digest.research_summary
    assert "尚未有 paper-shadow 結果" in digest.research_summary


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


def test_strategy_research_digest_prefers_active_retest_evidence_over_newer_symbol_artifacts(
    tmp_path,
):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    _seed_strategy_research_chain(repository, now)
    revision = StrategyCard(
        card_id="strategy-card:digest-active-retest-evidence",
        created_at=now + timedelta(minutes=20),
        strategy_name="BTC active retest evidence strategy",
        strategy_family="breakout_reversal",
        version="v2",
        status="DRAFT",
        symbols=["BTC-USD"],
        hypothesis="Digest evidence must follow the active retest chain.",
        signal_description="Replacement retest signal.",
        entry_rules=["Enter only after active retest evidence passes."],
        exit_rules=["Exit when active retest invalidates."],
        risk_rules=["Wait for active retest paper-shadow outcome."],
        parameters={"revision_source_outcome_id": "paper-shadow-outcome:digest-revision"},
        data_requirements=["market_candles:BTC-USD:1h"],
        feature_snapshot_ids=[],
        backtest_result_ids=["backtest-result:active-retest-evidence"],
        walk_forward_validation_ids=["walk-forward:active-retest-evidence"],
        event_edge_evaluation_ids=[],
        parent_card_id="strategy-card:digest-revision",
        author="codex-runtime",
        decision_basis="paper_shadow_strategy_revision_candidate",
    )
    trial = ExperimentTrial(
        trial_id="experiment-trial:active-retest-evidence",
        created_at=now + timedelta(minutes=21),
        strategy_card_id=revision.card_id,
        trial_index=1,
        status="PASSED",
        symbol="BTC-USD",
        seed=11,
        dataset_id="research-dataset:active-retest-evidence",
        backtest_result_id="backtest-result:active-retest-evidence",
        walk_forward_validation_id="walk-forward:active-retest-evidence",
        event_edge_evaluation_id=None,
        prompt_hash="prompt-active-retest-evidence",
        code_hash="code-active-retest-evidence",
        parameters={"revision_retest_protocol": "pr14-v1"},
        metric_summary={"alpha_score": None},
        failure_reason=None,
        started_at=now + timedelta(minutes=20),
        completed_at=now + timedelta(minutes=21),
        decision_basis="test",
    )
    evaluation = LockedEvaluationResult(
        evaluation_id="locked-evaluation:active-retest-evidence",
        created_at=now + timedelta(minutes=22),
        strategy_card_id=revision.card_id,
        trial_id=trial.trial_id,
        split_manifest_id="split-manifest:active-retest-evidence",
        cost_model_id="cost-model:active-retest-evidence",
        baseline_id="baseline:active-retest-evidence",
        backtest_result_id="backtest-result:active-retest-evidence",
        walk_forward_validation_id="walk-forward:active-retest-evidence",
        event_edge_evaluation_id=None,
        passed=False,
        rankable=False,
        alpha_score=None,
        blocked_reasons=["leaderboard_entry_not_rankable"],
        gate_metrics={"holdout_excess_return": -0.01},
        decision_basis="test",
    )
    leaderboard = LeaderboardEntry(
        entry_id="leaderboard-entry:active-retest-evidence",
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
    repository.save_backtest_result(
        _digest_backtest(
            now + timedelta(minutes=22),
            result_id="backtest-result:active-retest-evidence",
            strategy_return=-0.02,
            benchmark_return=-0.01,
        )
    )
    repository.save_walk_forward_validation(
        _digest_walk_forward(
            now + timedelta(minutes=22),
            validation_id="walk-forward:active-retest-evidence",
            average_excess_return=-0.0025,
        )
    )
    repository.save_backtest_result(
        _digest_backtest(
            now + timedelta(minutes=23),
            result_id="backtest-result:newer-unrelated",
            strategy_return=0.09,
            benchmark_return=0.01,
        )
    )
    repository.save_walk_forward_validation(
        _digest_walk_forward(
            now + timedelta(minutes=23),
            validation_id="walk-forward:newer-unrelated",
            average_excess_return=0.0123,
        )
    )

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=24),
    )

    assert digest.strategy_card_id == revision.card_id
    assert "backtest-result:active-retest-evidence" in digest.evidence_artifact_ids
    assert "walk-forward:active-retest-evidence" in digest.evidence_artifact_ids
    assert "backtest-result:newer-unrelated" not in digest.evidence_artifact_ids
    assert "walk-forward:newer-unrelated" not in digest.evidence_artifact_ids
    assert "Backtest：策略 -2.00%，benchmark -1.00%" in digest.research_summary
    assert "Walk-forward：excess -0.25%" in digest.research_summary
    assert "Backtest：策略 +9.00%" not in digest.research_summary
    assert "Walk-forward：excess +1.23%" not in digest.research_summary


def test_strategy_research_digest_does_not_fallback_when_active_retest_evidence_ids_are_unresolved(
    tmp_path,
):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    _seed_strategy_research_chain(repository, now)
    revision = StrategyCard(
        card_id="strategy-card:digest-unresolved-retest-evidence",
        created_at=now + timedelta(minutes=20),
        strategy_name="BTC unresolved retest evidence strategy",
        strategy_family="breakout_reversal",
        version="v2",
        status="DRAFT",
        symbols=["BTC-USD"],
        hypothesis="Unresolved active retest evidence must not borrow newer same-symbol metrics.",
        signal_description="Replacement retest signal.",
        entry_rules=["Enter only after active retest evidence resolves."],
        exit_rules=["Exit when active retest invalidates."],
        risk_rules=["Treat unresolved linked evidence as missing evidence."],
        parameters={"revision_source_outcome_id": "paper-shadow-outcome:digest-revision"},
        data_requirements=["market_candles:BTC-USD:1h"],
        feature_snapshot_ids=[],
        backtest_result_ids=["backtest-result:unresolved-retest-evidence"],
        walk_forward_validation_ids=["walk-forward:unresolved-retest-evidence"],
        event_edge_evaluation_ids=[],
        parent_card_id="strategy-card:digest-revision",
        author="codex-runtime",
        decision_basis="paper_shadow_strategy_revision_candidate",
    )
    trial = ExperimentTrial(
        trial_id="experiment-trial:unresolved-retest-evidence",
        created_at=now + timedelta(minutes=21),
        strategy_card_id=revision.card_id,
        trial_index=1,
        status="PASSED",
        symbol="BTC-USD",
        seed=11,
        dataset_id="research-dataset:unresolved-retest-evidence",
        backtest_result_id="backtest-result:unresolved-retest-evidence",
        walk_forward_validation_id="walk-forward:unresolved-retest-evidence",
        event_edge_evaluation_id=None,
        prompt_hash="prompt-unresolved-retest-evidence",
        code_hash="code-unresolved-retest-evidence",
        parameters={"revision_retest_protocol": "pr14-v1"},
        metric_summary={"alpha_score": None},
        failure_reason=None,
        started_at=now + timedelta(minutes=20),
        completed_at=now + timedelta(minutes=21),
        decision_basis="test",
    )
    evaluation = LockedEvaluationResult(
        evaluation_id="locked-evaluation:unresolved-retest-evidence",
        created_at=now + timedelta(minutes=22),
        strategy_card_id=revision.card_id,
        trial_id=trial.trial_id,
        split_manifest_id="split-manifest:unresolved-retest-evidence",
        cost_model_id="cost-model:unresolved-retest-evidence",
        baseline_id="baseline:unresolved-retest-evidence",
        backtest_result_id="backtest-result:unresolved-retest-evidence",
        walk_forward_validation_id="walk-forward:unresolved-retest-evidence",
        event_edge_evaluation_id=None,
        passed=False,
        rankable=False,
        alpha_score=None,
        blocked_reasons=["leaderboard_entry_not_rankable"],
        gate_metrics={"holdout_excess_return": -0.01},
        decision_basis="test",
    )
    leaderboard = LeaderboardEntry(
        entry_id="leaderboard-entry:unresolved-retest-evidence",
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
    repository.save_backtest_result(
        _digest_backtest(
            now + timedelta(minutes=23),
            result_id="backtest-result:newer-unrelated",
            strategy_return=0.09,
            benchmark_return=0.01,
        )
    )
    repository.save_walk_forward_validation(
        _digest_walk_forward(
            now + timedelta(minutes=23),
            validation_id="walk-forward:newer-unrelated",
            average_excess_return=0.0123,
        )
    )

    digest = record_strategy_research_digest(
        repository=repository,
        symbol="BTC-USD",
        created_at=now + timedelta(minutes=24),
    )

    assert digest.strategy_card_id == revision.card_id
    assert "backtest-result:newer-unrelated" not in digest.evidence_artifact_ids
    assert "walk-forward:newer-unrelated" not in digest.evidence_artifact_ids
    assert "Backtest：" not in digest.research_summary
    assert "Walk-forward：" not in digest.research_summary


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
    assert "decision_blocker_research_agenda_id" in result


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
