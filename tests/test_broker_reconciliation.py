from datetime import UTC, datetime
import json

import pytest

from forecast_loop.broker_reconciliation import run_broker_reconciliation
from forecast_loop.cli import main
from forecast_loop.health import run_health_check
from forecast_loop.models import (
    BrokerOrder,
    BrokerOrderStatus,
    PaperPortfolioSnapshot,
    PaperPosition,
)
from forecast_loop.storage import JsonFileRepository


def _broker_order(
    now: datetime,
    *,
    broker_order_id: str = "broker-order:local",
    broker_order_ref: str | None = "external:1",
    status: str = BrokerOrderStatus.ACKNOWLEDGED.value,
) -> BrokerOrder:
    return BrokerOrder(
        broker_order_id=broker_order_id,
        created_at=now,
        updated_at=now,
        local_order_id=f"paper-order:{broker_order_id}",
        decision_id="decision:broker-reconcile",
        symbol="BTC-USD",
        side="BUY",
        quantity=0.1,
        target_position_pct=0.1,
        broker="binance_testnet",
        broker_mode="SANDBOX",
        status=status,
        broker_status=status,
        broker_order_ref=broker_order_ref,
        client_order_id=f"client:{broker_order_id}",
        error_message=None,
        raw_response={"mock": True, "live_trading": False},
        decision_basis="test",
    )


def _portfolio(now: datetime, *, quantity: float = 0.1, cash: float = 9_000.0, equity: float = 10_000.0):
    position = PaperPosition(
        symbol="BTC-USD",
        quantity=quantity,
        avg_price=10_000.0,
        market_price=10_000.0,
        market_value=1_000.0,
        unrealized_pnl=0.0,
        position_pct=0.1,
    )
    return PaperPortfolioSnapshot(
        snapshot_id=PaperPortfolioSnapshot.build_id(
            created_at=now,
            equity=equity,
            cash=cash,
            positions=[position],
        ),
        created_at=now,
        equity=equity,
        cash=cash,
        gross_exposure_pct=0.1,
        net_exposure_pct=0.1,
        max_drawdown_pct=None,
        positions=[position],
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        nav=equity,
    )


def _repository(tmp_path, now: datetime) -> JsonFileRepository:
    repository = JsonFileRepository(tmp_path)
    repository.save_broker_order(_broker_order(now))
    repository.save_portfolio_snapshot(_portfolio(now))
    return repository


def test_broker_reconciliation_matches_external_paper_snapshot(tmp_path):
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    repository = _repository(tmp_path, now)

    reconciliation = run_broker_reconciliation(
        repository=repository,
        now=now,
        broker="binance_testnet",
        broker_mode="SANDBOX",
        external_snapshot={
            "orders": [{"broker_order_ref": "external:1", "status": "ACKNOWLEDGED"}],
            "positions": [{"symbol": "BTC-USD", "quantity": 0.1}],
            "cash": 9_000.0,
            "equity": 10_000.0,
        },
    )

    assert reconciliation.status == "MATCHED"
    assert reconciliation.repair_required is False
    assert reconciliation.matched_order_refs == ["external:1"]
    assert repository.load_broker_reconciliations() == [reconciliation]


def test_broker_reconciliation_flags_missing_unknown_and_duplicate_orders(tmp_path):
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    repository = _repository(tmp_path, now)

    reconciliation = run_broker_reconciliation(
        repository=repository,
        now=now,
        broker="binance_testnet",
        broker_mode="SANDBOX",
        external_snapshot={
            "orders": [
                {"broker_order_ref": "external:unknown", "status": "ACKNOWLEDGED"},
                {"broker_order_ref": "external:unknown", "status": "ACKNOWLEDGED"},
            ],
            "positions": [{"symbol": "BTC-USD", "quantity": 0.1}],
            "cash": 9_000.0,
            "equity": 10_000.0,
        },
    )

    codes = {finding["code"] for finding in reconciliation.findings}
    assert reconciliation.status == "MISMATCH"
    assert reconciliation.repair_required is True
    assert "missing_external_order" in codes
    assert "unknown_external_order" in codes
    assert "duplicate_external_broker_order_ref" in codes


def test_cli_broker_reconcile_records_blocking_mismatch_and_health_finding(tmp_path, capsys):
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    _repository(tmp_path, now)
    snapshot_path = tmp_path / "external_snapshot.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "orders": [{"broker_order_ref": "external:1", "status": "ACKNOWLEDGED"}],
                "positions": [{"symbol": "BTC-USD", "quantity": 0.2}],
                "cash": 8_500.0,
                "equity": 9_500.0,
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "broker-reconcile",
            "--storage-dir",
            str(tmp_path),
            "--external-snapshot",
            str(snapshot_path),
            "--now",
            now.isoformat(),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["repair_required"] is True
    assert {finding["code"] for finding in payload["findings"]} >= {
        "cash_mismatch",
        "equity_mismatch",
        "position_mismatch",
    }

    health = run_health_check(
        storage_dir=tmp_path,
        symbol="BTC-USD",
        now=now,
        create_repair_request=False,
    )
    assert "broker_reconciliation_blocking" in {finding.code for finding in health.findings}


def test_cli_broker_reconcile_rejects_live_mode_before_writing(tmp_path, capsys):
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    _repository(tmp_path, now)
    snapshot_path = tmp_path / "external_snapshot.json"
    snapshot_path.write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "broker-reconcile",
                "--storage-dir",
                str(tmp_path),
                "--external-snapshot",
                str(snapshot_path),
                "--broker-mode",
                "LIVE",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "invalid choice" in captured.err
    assert "LIVE" in captured.err
    assert not (tmp_path / "broker_reconciliations.jsonl").exists()
