from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json

from forecast_loop.cli import main
from forecast_loop.locked_evaluation import evaluate_leaderboard_gate, lock_evaluation_protocol
from forecast_loop.health import run_health_check
from forecast_loop.models import (
    BacktestResult,
    BaselineEvaluation,
    CostModelSnapshot,
    ExperimentTrial,
    LeaderboardEntry,
    LockedEvaluationResult,
    SplitManifest,
    StrategyCard,
    WalkForwardValidation,
)
from forecast_loop.storage import JsonFileRepository


def _now() -> datetime:
    return datetime(2026, 4, 28, 12, 0, tzinfo=UTC)


def _strategy_card(now: datetime) -> StrategyCard:
    return StrategyCard(
        card_id="strategy-card:leaderboard",
        created_at=now,
        strategy_name="MA trend BTC",
        strategy_family="trend_following",
        version="v1",
        status="ACTIVE",
        symbols=["BTC-USD"],
        hypothesis="BTC trend continuation after moving-average confirmation.",
        signal_description="Fast moving average above slow moving average.",
        entry_rules=["Enter long when fast_ma > slow_ma."],
        exit_rules=["Exit when fast_ma <= slow_ma."],
        risk_rules=["Max drawdown 10%."],
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


def _trial(now: datetime, card: StrategyCard, status: str = "PASSED") -> ExperimentTrial:
    return ExperimentTrial(
        trial_id=f"experiment-trial:{status.lower()}",
        created_at=now,
        strategy_card_id=card.card_id,
        trial_index=1,
        status=status,
        symbol="BTC-USD",
        seed=42,
        dataset_id="research-dataset:leaderboard",
        backtest_result_id="backtest-result:leaderboard",
        walk_forward_validation_id="walk-forward:leaderboard",
        event_edge_evaluation_id=None,
        prompt_hash="prompt-hash",
        code_hash="code-hash",
        parameters={"fast_window": 3, "slow_window": 7},
        metric_summary={"excess_return": 0.03},
        failure_reason=None if status == "PASSED" else "negative_after_cost_edge",
        started_at=now,
        completed_at=now,
        decision_basis="test",
    )


def _baseline(now: datetime) -> BaselineEvaluation:
    return BaselineEvaluation(
        baseline_id="baseline:leaderboard",
        created_at=now,
        symbol="BTC-USD",
        sample_size=20,
        directional_accuracy=0.65,
        baseline_accuracy=0.50,
        model_edge=0.15,
        recent_score=0.70,
        evidence_grade="B",
        forecast_ids=[],
        score_ids=[],
        decision_basis="test",
    )


def _backtest_result(now: datetime, strategy_return: float = 0.08, benchmark_return: float = 0.03) -> BacktestResult:
    return BacktestResult(
        result_id="backtest-result:leaderboard",
        backtest_id="backtest-run:leaderboard",
        created_at=now,
        symbol="BTC-USD",
        start=now - timedelta(days=30),
        end=now,
        initial_cash=10_000.0,
        final_equity=10_800.0,
        strategy_return=strategy_return,
        benchmark_return=benchmark_return,
        max_drawdown=0.04,
        sharpe=1.2,
        turnover=1.5,
        win_rate=0.6,
        trade_count=8,
        equity_curve=[],
        decision_basis="test",
    )


def _walk_forward(now: datetime, average_excess_return: float = 0.04) -> WalkForwardValidation:
    return WalkForwardValidation(
        validation_id="walk-forward:leaderboard",
        created_at=now,
        symbol="BTC-USD",
        start=now - timedelta(days=30),
        end=now,
        strategy_name="moving_average_trend",
        train_size=10,
        validation_size=5,
        test_size=5,
        step_size=1,
        initial_cash=10_000.0,
        fee_bps=5.0,
        slippage_bps=10.0,
        moving_average_window=3,
        window_count=3,
        average_validation_return=0.03,
        average_test_return=0.05,
        average_benchmark_return=0.01,
        average_excess_return=average_excess_return,
        test_win_rate=0.67,
        overfit_window_count=0,
        overfit_risk_flags=[],
        backtest_result_ids=["backtest-result:leaderboard"],
        windows=[],
        decision_basis="test",
    )


def _split(now: datetime, card: StrategyCard) -> SplitManifest:
    return SplitManifest(
        manifest_id="split-manifest:leaderboard",
        created_at=now,
        symbol="BTC-USD",
        strategy_card_id=card.card_id,
        dataset_id="research-dataset:leaderboard",
        train_start=now - timedelta(days=90),
        train_end=now - timedelta(days=60),
        validation_start=now - timedelta(days=59),
        validation_end=now - timedelta(days=30),
        holdout_start=now - timedelta(days=29),
        holdout_end=now,
        embargo_hours=24,
        status="LOCKED",
        locked_by="codex",
        decision_basis="test",
    )


def _cost_model(now: datetime) -> CostModelSnapshot:
    return CostModelSnapshot(
        cost_model_id="cost-model:leaderboard",
        created_at=now,
        symbol="BTC-USD",
        fee_bps=5.0,
        slippage_bps=10.0,
        max_turnover=5.0,
        max_drawdown=0.10,
        baseline_suite_version="m4b-v1",
        status="LOCKED",
        decision_basis="test",
    )


def _seed_passing_repository(tmp_path):
    now = _now()
    repository = JsonFileRepository(tmp_path)
    card = _strategy_card(now)
    split = _split(now, card)
    cost_model = _cost_model(now)
    trial = _trial(now, card)
    baseline = _baseline(now)
    backtest = _backtest_result(now)
    walk_forward = _walk_forward(now)
    repository.save_strategy_card(card)
    repository.save_split_manifest(split)
    repository.save_cost_model_snapshot(cost_model)
    repository.save_experiment_trial(trial)
    repository.save_baseline_evaluation(baseline)
    repository.save_backtest_result(backtest)
    repository.save_walk_forward_validation(walk_forward)
    return repository, card, split, cost_model, trial, baseline, backtest, walk_forward


def test_json_repository_round_trips_locked_evaluation_artifacts(tmp_path):
    repository, card, split, cost_model, trial, baseline, backtest, walk_forward = _seed_passing_repository(tmp_path)
    result = LockedEvaluationResult(
        evaluation_id="locked-evaluation:leaderboard",
        created_at=_now(),
        strategy_card_id=card.card_id,
        trial_id=trial.trial_id,
        split_manifest_id=split.manifest_id,
        cost_model_id=cost_model.cost_model_id,
        baseline_id=baseline.baseline_id,
        backtest_result_id=backtest.result_id,
        walk_forward_validation_id=walk_forward.validation_id,
        event_edge_evaluation_id=None,
        passed=True,
        rankable=True,
        alpha_score=0.23,
        blocked_reasons=[],
        gate_metrics={"model_edge": 0.15},
        decision_basis="test",
    )
    entry = LeaderboardEntry(
        entry_id="leaderboard-entry:leaderboard",
        created_at=_now(),
        strategy_card_id=card.card_id,
        evaluation_id=result.evaluation_id,
        trial_id=trial.trial_id,
        symbol="BTC-USD",
        rankable=True,
        alpha_score=0.23,
        promotion_stage="CANDIDATE",
        blocked_reasons=[],
        leaderboard_rules_version="pr7-v1",
        decision_basis="test",
    )

    repository.save_locked_evaluation_result(result)
    repository.save_leaderboard_entry(entry)
    repository.save_locked_evaluation_result(result)
    repository.save_leaderboard_entry(entry)

    assert repository.load_split_manifests() == [split]
    assert repository.load_cost_model_snapshots() == [cost_model]
    assert repository.load_locked_evaluation_results() == [result]
    assert repository.load_leaderboard_entries() == [entry]


def test_leaderboard_gate_blocks_without_locked_protocol(tmp_path):
    now = _now()
    repository = JsonFileRepository(tmp_path)
    card = _strategy_card(now)
    trial = _trial(now, card)
    repository.save_strategy_card(card)
    repository.save_experiment_trial(trial)

    result, entry = evaluate_leaderboard_gate(
        repository=repository,
        created_at=now,
        strategy_card_id=card.card_id,
        trial_id=trial.trial_id,
        split_manifest_id="split-manifest:missing",
        cost_model_id="cost-model:missing",
        baseline_id="baseline:missing",
        backtest_result_id="backtest-result:missing",
        walk_forward_validation_id="walk-forward:missing",
    )

    assert result.passed is False
    assert entry.rankable is False
    assert entry.alpha_score is None
    assert "split_manifest_missing" in result.blocked_reasons
    assert "cost_model_missing" in result.blocked_reasons


def test_leaderboard_gate_blocks_failed_trial_and_keeps_entry(tmp_path):
    repository, card, split, cost_model, trial, baseline, backtest, walk_forward = _seed_passing_repository(tmp_path)
    failed = _trial(_now(), card, status="FAILED")
    failed.trial_id = "experiment-trial:failed-leaderboard"
    repository.save_experiment_trial(failed)

    result, entry = evaluate_leaderboard_gate(
        repository=repository,
        created_at=_now(),
        strategy_card_id=card.card_id,
        trial_id=failed.trial_id,
        split_manifest_id=split.manifest_id,
        cost_model_id=cost_model.cost_model_id,
        baseline_id=baseline.baseline_id,
        backtest_result_id=backtest.result_id,
        walk_forward_validation_id=walk_forward.validation_id,
    )

    assert result.passed is False
    assert entry.rankable is False
    assert entry.alpha_score is None
    assert entry.promotion_stage == "BLOCKED"
    assert "experiment_trial_not_passed" in result.blocked_reasons
    assert repository.load_leaderboard_entries()[-1] == entry


def test_leaderboard_gate_blocks_mismatched_evidence_artifacts(tmp_path):
    repository, _btc_card, split, cost_model, _btc_trial, baseline, backtest, walk_forward = _seed_passing_repository(
        tmp_path
    )
    eth_card = replace(
        _strategy_card(_now()),
        card_id="strategy-card:eth",
        strategy_name="MA trend ETH",
        symbols=["ETH-USD"],
        data_requirements=["market_candles:ETH-USD:1h"],
    )
    eth_trial = replace(
        _trial(_now(), eth_card),
        trial_id="experiment-trial:eth",
        symbol="ETH-USD",
        dataset_id="research-dataset:eth",
        backtest_result_id="backtest-result:eth",
        walk_forward_validation_id="walk-forward:eth",
    )
    repository.save_strategy_card(eth_card)
    repository.save_experiment_trial(eth_trial)

    result, entry = evaluate_leaderboard_gate(
        repository=repository,
        created_at=_now(),
        strategy_card_id=eth_card.card_id,
        trial_id=eth_trial.trial_id,
        split_manifest_id=split.manifest_id,
        cost_model_id=cost_model.cost_model_id,
        baseline_id=baseline.baseline_id,
        backtest_result_id=backtest.result_id,
        walk_forward_validation_id=walk_forward.validation_id,
    )

    assert result.passed is False
    assert entry.rankable is False
    assert entry.alpha_score is None
    assert "split_manifest_strategy_card_mismatch" in result.blocked_reasons
    assert "split_manifest_dataset_mismatch" in result.blocked_reasons
    assert "split_manifest_symbol_mismatch" in result.blocked_reasons
    assert "cost_model_symbol_mismatch" in result.blocked_reasons
    assert "baseline_symbol_mismatch" in result.blocked_reasons
    assert "experiment_trial_backtest_result_mismatch" in result.blocked_reasons
    assert "backtest_symbol_mismatch" in result.blocked_reasons
    assert "experiment_trial_walk_forward_validation_mismatch" in result.blocked_reasons
    assert "walk_forward_symbol_mismatch" in result.blocked_reasons


def test_leaderboard_gate_ranks_only_when_hard_gates_pass(tmp_path):
    repository, card, split, cost_model, trial, baseline, backtest, walk_forward = _seed_passing_repository(tmp_path)

    result, entry = evaluate_leaderboard_gate(
        repository=repository,
        created_at=_now(),
        strategy_card_id=card.card_id,
        trial_id=trial.trial_id,
        split_manifest_id=split.manifest_id,
        cost_model_id=cost_model.cost_model_id,
        baseline_id=baseline.baseline_id,
        backtest_result_id=backtest.result_id,
        walk_forward_validation_id=walk_forward.validation_id,
    )

    assert result.passed is True
    assert result.rankable is True
    assert entry.rankable is True
    assert entry.alpha_score is not None
    assert entry.alpha_score > 0


def test_cli_locks_protocol_and_evaluates_leaderboard(tmp_path, capsys):
    repository, card, _split, _cost_model, trial, baseline, backtest, walk_forward = _seed_passing_repository(tmp_path)
    now = _now().isoformat()
    # Keep only the card/trial/evidence; CLI should create a fresh split and cost model.
    (tmp_path / "split_manifests.jsonl").unlink()
    (tmp_path / "cost_model_snapshots.jsonl").unlink()
    assert repository.load_split_manifests() == []

    assert main(
        [
            "lock-evaluation-protocol",
            "--storage-dir",
            str(tmp_path),
            "--strategy-card-id",
            card.card_id,
            "--dataset-id",
            "research-dataset:leaderboard",
            "--symbol",
            "BTC-USD",
            "--train-start",
            "2026-01-01T00:00:00+00:00",
            "--train-end",
            "2026-02-01T00:00:00+00:00",
            "--validation-start",
            "2026-02-02T00:00:00+00:00",
            "--validation-end",
            "2026-03-01T00:00:00+00:00",
            "--holdout-start",
            "2026-03-02T00:00:00+00:00",
            "--holdout-end",
            "2026-04-01T00:00:00+00:00",
            "--created-at",
            now,
        ]
    ) == 0
    protocol_payload = json.loads(capsys.readouterr().out)

    assert main(
        [
            "evaluate-leaderboard-gate",
            "--storage-dir",
            str(tmp_path),
            "--strategy-card-id",
            card.card_id,
            "--trial-id",
            trial.trial_id,
            "--split-manifest-id",
            protocol_payload["split_manifest"]["manifest_id"],
            "--cost-model-id",
            protocol_payload["cost_model_snapshot"]["cost_model_id"],
            "--baseline-id",
            baseline.baseline_id,
            "--backtest-result-id",
            backtest.result_id,
            "--walk-forward-validation-id",
            walk_forward.validation_id,
            "--created-at",
            now,
        ]
    ) == 0
    gate_payload = json.loads(capsys.readouterr().out)

    assert gate_payload["leaderboard_entry"]["rankable"] is True
    assert gate_payload["leaderboard_entry"]["alpha_score"] > 0


def test_health_check_flags_locked_evaluation_link_errors(tmp_path):
    now = _now()
    repository = JsonFileRepository(tmp_path)
    card = _strategy_card(now)
    split = _split(now, card)
    repository.save_strategy_card(card)
    repository.save_split_manifest(split)
    duplicate_payload = split.to_dict()
    with (tmp_path / "split_manifests.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(duplicate_payload) + "\n")
    result = LockedEvaluationResult(
        evaluation_id="locked-evaluation:broken",
        created_at=now,
        strategy_card_id=card.card_id,
        trial_id="experiment-trial:missing",
        split_manifest_id=split.manifest_id,
        cost_model_id="cost-model:missing",
        baseline_id="baseline:missing",
        backtest_result_id="backtest-result:missing",
        walk_forward_validation_id="walk-forward:missing",
        event_edge_evaluation_id="event-edge:missing",
        passed=False,
        rankable=False,
        alpha_score=None,
        blocked_reasons=["test"],
        gate_metrics={},
        decision_basis="test",
    )
    repository.save_locked_evaluation_result(result)

    health = run_health_check(storage_dir=tmp_path, symbol="BTC-USD", now=now, create_repair_request=False)
    codes = {finding.code for finding in health.findings}

    assert "duplicate_manifest_id" in codes
    assert "locked_evaluation_missing_trial" in codes
    assert "locked_evaluation_missing_cost_model" in codes
    assert "locked_evaluation_missing_baseline" in codes
    assert "locked_evaluation_missing_backtest_result" in codes
    assert "locked_evaluation_missing_walk_forward_validation" in codes
    assert "locked_evaluation_missing_event_edge_evaluation" in codes
