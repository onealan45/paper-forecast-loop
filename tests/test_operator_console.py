from datetime import UTC, datetime
import json
import socket

import pytest

from forecast_loop.cli import main
from forecast_loop.models import PaperPortfolioSnapshot, PaperPosition, StrategyDecision
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


def test_operator_console_renders_required_pages_read_only(tmp_path):
    now = datetime(2026, 4, 25, 1, 30, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    repository.save_strategy_decision(_decision(now))
    repository.save_portfolio_snapshot(_portfolio(now))

    snapshot = build_operator_console_snapshot(tmp_path, symbol="BTC-USD", now=now)

    overview = render_operator_console_page(snapshot, page="overview")
    assert 'lang="zh-Hant"' in overview
    assert "Operator console sections" in overview
    assert "買進" in overview
    assert "Paper-only" in overview
    assert "<form" not in overview.lower()

    for page_title, page in [
        ("決策", "decisions"),
        ("投資組合", "portfolio"),
        ("研究", "research"),
        ("健康 / 修復", "health"),
        ("控制 Placeholder", "control"),
    ]:
        html = render_operator_console_page(snapshot, page=page)
        assert page_title in html
        assert "<form" not in html.lower()

    control = render_operator_console_page(snapshot, page="control")
    assert "控制面板在 M5A 只顯示 skeleton" in control
    assert "disabled" in control
    assert "submit_order" not in control


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
