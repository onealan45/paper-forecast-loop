from datetime import UTC, datetime, timedelta
import json

from forecast_loop.cli import main
from forecast_loop.decision import generate_strategy_decision
from forecast_loop.health import run_health_check
from forecast_loop.models import EquityCurvePoint, Forecast, ForecastScore, PaperPortfolioSnapshot, PaperPosition
from forecast_loop.risk import evaluate_risk
from forecast_loop.storage import JsonFileRepository


def _save_strong_evidence(repository: JsonFileRepository, now: datetime) -> None:
    actual_regimes = ["trend_up", "trend_down", "trend_up", "trend_down", "trend_up"]
    for index, actual_regime in enumerate(actual_regimes):
        created_at = now - timedelta(hours=10 - index)
        forecast = Forecast(
            forecast_id=f"forecast:risk-{index}",
            symbol="BTC-USD",
            created_at=created_at,
            anchor_time=created_at,
            target_window_start=created_at,
            target_window_end=created_at + timedelta(hours=1),
            candle_interval_minutes=60,
            expected_candle_count=2,
            status="resolved",
            status_reason="scored",
            predicted_regime=actual_regime,
            confidence=0.8,
            provider_data_through=created_at + timedelta(hours=1),
            observed_candle_count=2,
        )
        score = ForecastScore(
            score_id=f"score:risk-{index}",
            forecast_id=forecast.forecast_id,
            scored_at=created_at + timedelta(hours=1),
            predicted_regime=actual_regime,
            actual_regime=actual_regime,
            score=1.0,
            target_window_start=forecast.target_window_start,
            target_window_end=forecast.target_window_end,
            candle_interval_minutes=60,
            expected_candle_count=2,
            observed_candle_count=2,
            provider_data_through=forecast.target_window_end,
            scoring_basis="test",
        )
        repository.save_forecast(forecast)
        repository.save_score(score)


def _portfolio(now: datetime, *, equity: float, cash: float, market_value: float) -> PaperPortfolioSnapshot:
    position_pct = market_value / equity if equity else 0.0
    position = PaperPosition(
        symbol="BTC-USD",
        quantity=market_value / 100.0,
        avg_price=100.0,
        market_price=100.0,
        market_value=market_value,
        unrealized_pnl=0.0,
        position_pct=position_pct,
    )
    return PaperPortfolioSnapshot(
        snapshot_id=f"portfolio:{equity}:{market_value}",
        created_at=now,
        equity=equity,
        cash=cash,
        gross_exposure_pct=abs(position_pct),
        net_exposure_pct=position_pct,
        max_drawdown_pct=None,
        positions=[position] if market_value else [],
        realized_pnl=equity - 10_000.0,
        unrealized_pnl=0.0,
        nav=equity,
    )


def _equity_point(created_at: datetime, *, equity: float) -> EquityCurvePoint:
    return EquityCurvePoint(
        point_id=f"equity:{created_at.timestamp()}:{equity}",
        created_at=created_at,
        equity=equity,
        cash=equity,
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        gross_exposure_pct=0.0,
        net_exposure_pct=0.0,
        max_drawdown_pct=None,
    )


def test_risk_check_reports_ok_state(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_portfolio_snapshot(_portfolio(now, equity=10_000.0, cash=9_000.0, market_value=1_000.0))
    repository.save_equity_curve_point(_equity_point(now - timedelta(hours=1), equity=10_000.0))

    snapshot = evaluate_risk(repository=repository, symbol="BTC-USD", now=now)

    assert snapshot.status == "OK"
    assert snapshot.severity == "none"
    assert snapshot.current_drawdown_pct == 0.0
    assert repository.load_risk_snapshots() == [snapshot]


def test_drawdown_gate_reduces_risk_before_buy_signal(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _save_strong_evidence(repository, now)
    repository.save_portfolio_snapshot(_portfolio(now, equity=9_400.0, cash=7_990.0, market_value=1_410.0))
    repository.save_equity_curve_point(_equity_point(now - timedelta(hours=1), equity=10_000.0))
    risk = evaluate_risk(repository=repository, symbol="BTC-USD", now=now)

    decision = generate_strategy_decision(repository=repository, symbol="BTC-USD", horizon_hours=24, now=now, risk_snapshot=risk)

    assert risk.status == "REDUCE_RISK"
    assert decision.action == "REDUCE_RISK"
    assert decision.tradeable is True
    assert decision.blocked_reason is None
    assert decision.recommended_position_pct == 0.075
    assert "risk=" in decision.decision_basis


def test_severe_drawdown_gate_stops_new_entries(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    _save_strong_evidence(repository, now)
    repository.save_portfolio_snapshot(_portfolio(now, equity=8_900.0, cash=7_565.0, market_value=1_335.0))
    repository.save_equity_curve_point(_equity_point(now - timedelta(hours=1), equity=10_000.0))
    risk = evaluate_risk(repository=repository, symbol="BTC-USD", now=now)

    decision = generate_strategy_decision(repository=repository, symbol="BTC-USD", horizon_hours=24, now=now, risk_snapshot=risk)

    assert risk.status == "STOP_NEW_ENTRIES"
    assert risk.severity == "blocking"
    assert decision.action == "STOP_NEW_ENTRIES"
    assert decision.tradeable is False
    assert decision.blocked_reason == "risk_stop_new_entries"


def test_exposure_gate_reduces_risk(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_portfolio_snapshot(_portfolio(now, equity=10_000.0, cash=7_500.0, market_value=2_500.0))

    snapshot = evaluate_risk(repository=repository, symbol="BTC-USD", now=now, max_gross_exposure_pct=0.20)

    assert snapshot.status == "REDUCE_RISK"
    assert snapshot.severity == "warning"
    assert any("gross_exposure" in finding for finding in snapshot.findings)


def test_cli_risk_check_writes_snapshot(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository.save_portfolio_snapshot(_portfolio(now, equity=10_000.0, cash=9_000.0, market_value=1_000.0))

    exit_code = main(
        [
            "risk-check",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--now",
            now.isoformat(),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "OK"
    assert repository.load_risk_snapshots()[0].risk_id == payload["risk_id"]


def test_health_check_detects_bad_risk_snapshot_row(tmp_path):
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _save_strong_evidence(repository, now)
    (tmp_path / "dashboard.html").write_text("Dashboard 產生時間：test", encoding="utf-8")
    (tmp_path / "risk_snapshots.jsonl").write_text("{bad json\n", encoding="utf-8")

    result = run_health_check(storage_dir=tmp_path, symbol="BTC-USD", now=now, create_repair_request=False)

    assert result.status == "unhealthy"
    assert result.repair_required is True
    assert any(finding.code == "bad_json_row" for finding in result.findings)
