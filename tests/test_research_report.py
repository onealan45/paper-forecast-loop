from datetime import UTC, datetime, timedelta
import json

import pytest

from forecast_loop.cli import main
from forecast_loop.models import (
    BaselineEvaluation,
    BacktestRun,
    BacktestResult,
    Forecast,
    ForecastScore,
    MarketCandleRecord,
    StrategyDecision,
    WalkForwardValidation,
    WalkForwardWindow,
)
from forecast_loop.storage import JsonFileRepository


def _seed_report_artifacts(repository: JsonFileRepository) -> None:
    now = datetime(2026, 4, 24, 12, tzinfo=UTC)
    for index, close in enumerate([100, 102, 101]):
        timestamp = datetime(2026, 4, 1, tzinfo=UTC) + timedelta(days=index)
        repository.save_market_candle(
            MarketCandleRecord(
                candle_id=f"market-candle:report:{index}",
                symbol="BTC-USD",
                timestamp=timestamp,
                open=close - 1,
                high=close + 1,
                low=close - 2,
                close=close,
                volume=1000 + index,
                source="fixture",
                imported_at=now,
            )
        )
    forecast = Forecast(
        forecast_id="forecast:report",
        symbol="BTC-USD",
        created_at=now,
        anchor_time=now,
        target_window_start=now,
        target_window_end=now + timedelta(hours=24),
        candle_interval_minutes=60,
        expected_candle_count=25,
        status="resolved",
        status_reason="scored",
        predicted_regime="trend_up",
        confidence=0.6,
        provider_data_through=now,
        observed_candle_count=25,
    )
    score = ForecastScore(
        score_id="score:report",
        forecast_id=forecast.forecast_id,
        scored_at=now + timedelta(hours=24),
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
    baseline = BaselineEvaluation(
        baseline_id="baseline:report",
        created_at=now,
        symbol="BTC-USD",
        sample_size=3,
        directional_accuracy=0.67,
        baseline_accuracy=0.33,
        model_edge=0.34,
        recent_score=0.67,
        evidence_grade="C",
        forecast_ids=[forecast.forecast_id],
        score_ids=[score.score_id],
        decision_basis="test",
        baseline_results=[
            {
                "baseline_name": "naive_persistence",
                "accuracy": 0.33,
                "evaluated_count": 3,
                "hit_count": 1,
                "sample_size": 3,
            }
        ],
    )
    decision = StrategyDecision(
        decision_id="decision:report",
        created_at=now,
        symbol="BTC-USD",
        horizon_hours=24,
        action="HOLD",
        confidence=0.6,
        evidence_grade="C",
        risk_level="MEDIUM",
        tradeable=False,
        blocked_reason="model_not_beating_baseline",
        recommended_position_pct=0.0,
        current_position_pct=0.0,
        max_position_pct=0.15,
        invalidation_conditions=["test"],
        reason_summary="test",
        forecast_ids=[forecast.forecast_id],
        score_ids=[score.score_id],
        review_ids=[],
        baseline_ids=[baseline.baseline_id],
        decision_basis="test decision gate",
    )
    backtest = BacktestResult(
        result_id="backtest-result:report",
        backtest_id="backtest-run:report",
        created_at=now,
        symbol="BTC-USD",
        start=now,
        end=now + timedelta(days=2),
        initial_cash=10_000,
        final_equity=10_100,
        strategy_return=0.01,
        benchmark_return=0.02,
        max_drawdown=0.03,
        sharpe=1.2,
        turnover=0.4,
        win_rate=0.5,
        trade_count=2,
        equity_curve=[],
        decision_basis="test",
    )
    window = WalkForwardWindow(
        window_id="walk-forward-window:report",
        train_start=now,
        train_end=now + timedelta(days=1),
        validation_start=now + timedelta(days=2),
        validation_end=now + timedelta(days=3),
        test_start=now + timedelta(days=4),
        test_end=now + timedelta(days=5),
        train_candle_count=2,
        validation_candle_count=2,
        test_candle_count=2,
        validation_backtest_result_id=backtest.result_id,
        test_backtest_result_id=backtest.result_id,
        validation_return=0.01,
        test_return=-0.01,
        benchmark_return=0.02,
        excess_return=-0.03,
        overfit_flags=["test_underperforms_benchmark"],
        decision_basis="test",
    )
    walk_forward = WalkForwardValidation(
        validation_id="walk-forward:report",
        created_at=now,
        symbol="BTC-USD",
        start=now,
        end=now + timedelta(days=5),
        strategy_name="moving_average_trend",
        train_size=2,
        validation_size=2,
        test_size=2,
        step_size=1,
        initial_cash=10_000,
        fee_bps=5,
        slippage_bps=10,
        moving_average_window=2,
        window_count=1,
        average_validation_return=0.01,
        average_test_return=-0.01,
        average_benchmark_return=0.02,
        average_excess_return=-0.03,
        test_win_rate=0.0,
        overfit_window_count=1,
        overfit_risk_flags=["aggregate_underperforms_benchmark", "test_underperforms_benchmark"],
        backtest_result_ids=[backtest.result_id],
        windows=[window],
        decision_basis="test",
    )
    repository.save_forecast(forecast)
    repository.save_score(score)
    repository.save_baseline_evaluation(baseline)
    repository.save_strategy_decision(decision)
    repository.save_backtest_result(backtest)
    repository.save_walk_forward_validation(walk_forward)


def test_cli_research_report_writes_markdown_summary(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path / "storage")
    _seed_report_artifacts(repository)
    output_dir = tmp_path / "reports" / "research"

    exit_code = main(
        [
            "research-report",
            "--storage-dir",
            str(tmp_path / "storage"),
            "--symbol",
            "BTC-USD",
            "--created-at",
            "2026-04-24T12:00:00+00:00",
            "--output-dir",
            str(output_dir),
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    report_path = output_dir / f"2026-04-24-{payload['report_id']}.md"
    markdown = report_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert payload["report_path"] == str(report_path.resolve())
    assert "# Research Report: BTC-USD" in markdown
    assert "## Data Coverage" in markdown
    assert "## Model Vs Baselines" in markdown
    assert "naive_persistence" in markdown
    assert "## Backtest Metrics" in markdown
    assert "## Walk-Forward Validation" in markdown
    assert "## Drawdown" in markdown
    assert "## Overfit Risk" in markdown
    assert "aggregate_underperforms_benchmark" in markdown
    assert "## Decision Gate Result" in markdown
    assert "model_not_beating_baseline" in markdown
    assert "paper-only research report" in markdown


def test_research_report_prefers_decision_blocker_backtest_over_newer_internal_walk_forward_backtest(
    tmp_path,
    capsys,
):
    now = datetime(2026, 5, 6, 8, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path / "storage")
    standalone_run = BacktestRun(
        backtest_id="backtest-run:blocker",
        created_at=now - timedelta(minutes=5),
        symbol="BTC-USD",
        start=now - timedelta(days=10),
        end=now - timedelta(hours=1),
        strategy_name="moving_average_trend",
        initial_cash=10_000,
        fee_bps=5,
        slippage_bps=10,
        moving_average_window=24,
        candle_ids=["candle:blocker"],
        decision_basis="id_context=decision_blocker_research:run_backtest:backtest_result",
    )
    internal_run = BacktestRun(
        backtest_id="backtest-run:walk-forward-internal",
        created_at=now,
        symbol="BTC-USD",
        start=now - timedelta(days=10),
        end=now - timedelta(hours=1),
        strategy_name="moving_average_trend",
        initial_cash=10_000,
        fee_bps=5,
        slippage_bps=10,
        moving_average_window=24,
        candle_ids=["candle:internal"],
        decision_basis="walk_forward_internal_backtest",
    )
    repository.save_backtest_run(standalone_run)
    repository.save_backtest_run(internal_run)
    repository.save_backtest_result(
        BacktestResult(
            result_id="backtest-result:blocker",
            backtest_id=standalone_run.backtest_id,
            created_at=standalone_run.created_at,
            symbol="BTC-USD",
            start=standalone_run.start,
            end=standalone_run.end,
            initial_cash=10_000,
            final_equity=9_500,
            strategy_return=-0.05,
            benchmark_return=0.01,
            max_drawdown=0.07,
            sharpe=-1.0,
            turnover=0.5,
            win_rate=0.25,
            trade_count=4,
            equity_curve=[],
            decision_basis="standalone blocker evidence",
        )
    )
    repository.save_backtest_result(
        BacktestResult(
            result_id="backtest-result:walk-forward-internal",
            backtest_id=internal_run.backtest_id,
            created_at=internal_run.created_at,
            symbol="BTC-USD",
            start=internal_run.start,
            end=internal_run.end,
            initial_cash=10_000,
            final_equity=10_100,
            strategy_return=0.01,
            benchmark_return=0.0,
            max_drawdown=0.02,
            sharpe=0.4,
            turnover=0.9,
            win_rate=0.55,
            trade_count=8,
            equity_curve=[],
            decision_basis="walk-forward internal result",
        )
    )
    output_dir = tmp_path / "reports" / "research"

    exit_code = main(
        [
            "research-report",
            "--storage-dir",
            str(tmp_path / "storage"),
            "--symbol",
            "BTC-USD",
            "--created-at",
            now.isoformat(),
            "--output-dir",
            str(output_dir),
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    report_path = output_dir / f"2026-05-06-{payload['report_id']}.md"
    markdown = report_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert "- Result ID: `backtest-result:blocker`" in markdown
    assert "- Result ID: `backtest-result:walk-forward-internal`" not in markdown


def test_cli_research_report_missing_storage_is_operator_friendly(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "research-report",
                "--storage-dir",
                str(tmp_path / "missing"),
                "--created-at",
                "2026-04-24T12:00:00+00:00",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "storage directory does not exist" in captured.err
    assert "Traceback" not in captured.err
