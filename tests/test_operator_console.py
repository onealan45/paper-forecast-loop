from datetime import UTC, datetime
import json
import socket

import pytest

from forecast_loop.cli import main
from forecast_loop.models import AutomationRun, PaperControlEvent, PaperPortfolioSnapshot, PaperPosition, RepairRequest, RiskSnapshot, StrategyDecision
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


def test_operator_console_renders_required_pages_read_only(tmp_path):
    now = datetime(2026, 4, 25, 1, 30, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_strategy_decision(_decision(now))
    repository.save_portfolio_snapshot(_portfolio(now))
    repository.save_risk_snapshot(_risk(now))
    repository.save_control_event(_control_event(now))
    repository.save_automation_run(_automation_run(now))

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)

    overview = render_operator_console_page(snapshot, page="overview")
    assert 'lang="zh-Hant"' in overview
    assert "Operator console sections" in overview
    assert "買進" in overview
    assert "Paper-only" in overview
    assert "Automation Run" in overview
    assert "automation-run:test" in overview
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
