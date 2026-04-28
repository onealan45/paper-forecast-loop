from datetime import UTC, datetime
import json

from forecast_loop.cli import main
from forecast_loop.experiment_registry import record_experiment_trial, register_strategy_card
from forecast_loop.health import run_health_check
from forecast_loop.models import ExperimentBudget, ExperimentTrial, StrategyCard
from forecast_loop.storage import JsonFileRepository


def _now() -> datetime:
    return datetime(2026, 4, 28, 12, 0, tzinfo=UTC)


def _strategy_card(now: datetime) -> StrategyCard:
    return StrategyCard(
        card_id="strategy-card:ma-trend-v1",
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
        risk_rules=["Max position 10% during research simulation."],
        parameters={"fast_window": 3, "slow_window": 7},
        data_requirements=["market_candles:BTC-USD:1h"],
        feature_snapshot_ids=["feature-snapshot:ma-trend"],
        backtest_result_ids=["backtest-result:ma-trend"],
        walk_forward_validation_ids=["walk-forward:ma-trend"],
        event_edge_evaluation_ids=["event-edge:macro"],
        parent_card_id=None,
        author="codex",
        decision_basis="test",
    )


def _budget(now: datetime, card: StrategyCard) -> ExperimentBudget:
    return ExperimentBudget(
        budget_id="experiment-budget:ma-trend-v1",
        created_at=now,
        strategy_card_id=card.card_id,
        max_trials=3,
        used_trials=2,
        remaining_trials=1,
        status="OPEN",
        budget_scope="strategy_card",
        decision_basis="test",
    )


def _trial(now: datetime, card: StrategyCard, status: str = "FAILED") -> ExperimentTrial:
    return ExperimentTrial(
        trial_id=f"experiment-trial:{status.lower()}",
        created_at=now,
        strategy_card_id=card.card_id,
        trial_index=1,
        status=status,
        symbol="BTC-USD",
        seed=42,
        dataset_id="research-dataset:ma-trend",
        backtest_result_id="backtest-result:ma-trend",
        walk_forward_validation_id="walk-forward:ma-trend",
        event_edge_evaluation_id="event-edge:macro",
        prompt_hash="prompt-hash",
        code_hash="code-hash",
        parameters={"fast_window": 3, "slow_window": 7},
        metric_summary={"excess_return": -0.02},
        failure_reason="negative_after_cost_edge" if status == "FAILED" else None,
        started_at=now,
        completed_at=now,
        decision_basis="test",
    )


def test_json_repository_round_trips_strategy_cards_and_experiment_trials(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = _now()
    card = _strategy_card(now)
    budget = _budget(now, card)
    failed = _trial(now, card, "FAILED")
    aborted = _trial(now, card, "ABORTED")

    repository.save_strategy_card(card)
    repository.save_experiment_budget(budget)
    repository.save_experiment_trial(failed)
    repository.save_experiment_trial(aborted)
    repository.save_experiment_trial(failed)

    assert repository.load_strategy_cards() == [card]
    assert repository.load_experiment_budgets() == [budget]
    assert repository.load_experiment_trials() == [failed, aborted]


def test_register_strategy_card_is_idempotent(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = _now()

    first = register_strategy_card(
        repository=repository,
        created_at=now,
        strategy_name="MA trend BTC",
        strategy_family="trend_following",
        version="v1",
        symbols=["BTC-USD"],
        hypothesis="BTC trend continuation after moving-average confirmation.",
        signal_description="Fast moving average above slow moving average.",
        entry_rules=["Enter long when fast_ma > slow_ma."],
        exit_rules=["Exit when fast_ma <= slow_ma."],
        risk_rules=["Max position 10% during research simulation."],
        parameters={"fast_window": 3, "slow_window": 7},
        data_requirements=["market_candles:BTC-USD:1h"],
        author="codex",
    )
    second = register_strategy_card(
        repository=repository,
        created_at=now,
        strategy_name="MA trend BTC",
        strategy_family="trend_following",
        version="v1",
        symbols=["BTC-USD"],
        hypothesis="BTC trend continuation after moving-average confirmation.",
        signal_description="Fast moving average above slow moving average.",
        entry_rules=["Enter long when fast_ma > slow_ma."],
        exit_rules=["Exit when fast_ma <= slow_ma."],
        risk_rules=["Max position 10% during research simulation."],
        parameters={"fast_window": 3, "slow_window": 7},
        data_requirements=["market_candles:BTC-USD:1h"],
        author="codex",
    )

    assert first == second
    assert repository.load_strategy_cards() == [first]


def test_experiment_trial_budget_exhaustion_is_persisted_as_aborted(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = _now()
    card = _strategy_card(now)
    repository.save_strategy_card(card)

    first = record_experiment_trial(
        repository=repository,
        created_at=now,
        strategy_card_id=card.card_id,
        trial_index=1,
        status="PASSED",
        symbol="BTC-USD",
        max_trials=1,
        metric_summary={"excess_return": 0.01},
    )
    second = record_experiment_trial(
        repository=repository,
        created_at=now,
        strategy_card_id=card.card_id,
        trial_index=2,
        status="PASSED",
        symbol="BTC-USD",
        max_trials=1,
        metric_summary={"excess_return": 0.02},
    )

    assert first.status == "PASSED"
    assert second.status == "ABORTED"
    assert second.failure_reason == "trial_budget_exhausted"
    assert repository.load_experiment_trials() == [first, second]
    assert repository.load_experiment_budgets()[-1].status == "EXHAUSTED"


def test_failed_aborted_and_invalid_trials_are_persisted(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = _now()
    card = _strategy_card(now)
    repository.save_strategy_card(card)

    statuses = ["FAILED", "ABORTED", "INVALID"]
    trials = [
        record_experiment_trial(
            repository=repository,
            created_at=now,
            strategy_card_id=card.card_id,
            trial_index=index,
            status=status,
            symbol="BTC-USD",
            max_trials=10,
            failure_reason=f"{status.lower()}_fixture",
        )
        for index, status in enumerate(statuses, start=1)
    ]

    assert [trial.status for trial in repository.load_experiment_trials()] == statuses
    assert [trial.failure_reason for trial in trials] == [
        "failed_fixture",
        "aborted_fixture",
        "invalid_fixture",
    ]


def test_pending_trial_does_not_exhaust_budget_before_final_result(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = _now()
    card = _strategy_card(now)
    repository.save_strategy_card(card)

    pending = record_experiment_trial(
        repository=repository,
        created_at=now,
        strategy_card_id=card.card_id,
        trial_index=1,
        status="PENDING",
        symbol="BTC-USD",
        max_trials=1,
    )
    failed = record_experiment_trial(
        repository=repository,
        created_at=now,
        strategy_card_id=card.card_id,
        trial_index=1,
        status="FAILED",
        symbol="BTC-USD",
        max_trials=1,
        failure_reason="negative_after_cost_edge",
    )

    assert pending.status == "PENDING"
    assert failed.status == "FAILED"
    assert failed.failure_reason == "negative_after_cost_edge"
    assert [(trial.trial_index, trial.status, trial.failure_reason) for trial in repository.load_experiment_trials()] == [
        (1, "PENDING", None),
        (1, "FAILED", "negative_after_cost_edge"),
    ]


def test_cli_registers_strategy_card_and_records_failed_trial(tmp_path, capsys):
    now = _now().isoformat()

    assert main(
        [
            "register-strategy-card",
            "--storage-dir",
            str(tmp_path),
            "--name",
            "MA trend BTC",
            "--family",
            "trend_following",
            "--version",
            "v1",
            "--symbol",
            "BTC-USD",
            "--hypothesis",
            "BTC trend continuation after moving-average confirmation.",
            "--signal-description",
            "Fast moving average above slow moving average.",
            "--entry-rule",
            "Enter long when fast_ma > slow_ma.",
            "--exit-rule",
            "Exit when fast_ma <= slow_ma.",
            "--risk-rule",
            "Max position 10% during research simulation.",
            "--parameter",
            "fast_window=3",
            "--parameter",
            "slow_window=7",
            "--data-requirement",
            "market_candles:BTC-USD:1h",
            "--created-at",
            now,
        ]
    ) == 0
    card_payload = json.loads(capsys.readouterr().out)
    card_id = card_payload["strategy_card"]["card_id"]

    assert main(
        [
            "record-experiment-trial",
            "--storage-dir",
            str(tmp_path),
            "--strategy-card-id",
            card_id,
            "--trial-index",
            "1",
            "--status",
            "FAILED",
            "--symbol",
            "BTC-USD",
            "--max-trials",
            "5",
            "--failure-reason",
            "negative_after_cost_edge",
            "--metric",
            "excess_return=-0.02",
            "--created-at",
            now,
        ]
    ) == 0
    trial_payload = json.loads(capsys.readouterr().out)

    assert trial_payload["experiment_trial"]["status"] == "FAILED"
    assert trial_payload["experiment_trial"]["failure_reason"] == "negative_after_cost_edge"
    assert JsonFileRepository(tmp_path).load_experiment_trials()[0].status == "FAILED"


def test_health_check_flags_experiment_registry_link_errors(tmp_path):
    now = _now()
    repository = JsonFileRepository(tmp_path)
    card = _strategy_card(now)
    repository.save_strategy_card(card)
    repository.save_experiment_trial(_trial(now, card, "FAILED"))

    duplicate_payload = card.to_dict()
    with (tmp_path / "strategy_cards.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(duplicate_payload) + "\n")

    missing_card_trial = _trial(now, card, "INVALID")
    missing_card_trial.trial_id = "experiment-trial:missing-card"
    missing_card_trial.strategy_card_id = "strategy-card:missing"
    repository.save_experiment_trial(missing_card_trial)

    health = run_health_check(storage_dir=tmp_path, symbol="BTC-USD", now=now, create_repair_request=False)
    codes = {finding.code for finding in health.findings}

    assert "duplicate_card_id" in codes
    assert "experiment_trial_missing_strategy_card" in codes
    assert "experiment_trial_missing_research_dataset" in codes
    assert "experiment_trial_missing_backtest_result" in codes
    assert "experiment_trial_missing_walk_forward_validation" in codes
    assert "experiment_trial_missing_event_edge_evaluation" in codes
