from datetime import UTC, datetime

import pytest

from forecast_loop.broker import BinanceTestnetBrokerAdapter, BrokerMode, build_broker_adapter


class FakeBrokerHttpClient:
    def __init__(self, response: dict | None = None) -> None:
        self.response = response or {"ok": True}
        self.requests: list[dict] = []

    def request(self, *, method: str, url: str, headers: dict[str, str], payload: dict | None = None) -> dict:
        self.requests.append({"method": method, "url": url, "headers": headers, "payload": payload})
        return self.response


def test_binance_testnet_adapter_requires_keys_and_testnet_endpoint():
    fake = FakeBrokerHttpClient()

    with pytest.raises(ValueError, match="requires API key"):
        build_broker_adapter("SANDBOX", broker="binance_testnet", http_client=fake)
    with pytest.raises(ValueError, match="refuses non-testnet"):
        BinanceTestnetBrokerAdapter(
            api_key="key",
            api_secret="secret",
            http_client=fake,
            base_url="https://api.binance.com",
        )


def test_binance_testnet_adapter_submit_is_mockable_and_uses_test_endpoint():
    fake = FakeBrokerHttpClient(response={"testOrder": "accepted"})
    adapter = build_broker_adapter(
        "SANDBOX",
        broker="binance_testnet",
        api_key="test-key",
        api_secret="test-secret",
        http_client=fake,
    )

    result = adapter.submit_order(
        symbol="BTC-USD",
        side="BUY",
        quantity=0.01,
        client_order_id="client:test",
    )

    assert isinstance(adapter, BinanceTestnetBrokerAdapter)
    assert adapter.mode == BrokerMode.SANDBOX
    assert result["status"] == "submitted"
    assert result["mode"] == "SANDBOX"
    assert fake.requests == [
        {
            "method": "POST",
            "url": "https://testnet.binance.vision/api/v3/order/test",
            "headers": {"X-MBX-APIKEY": "test-key"},
            "payload": {
                "symbol": "BTCUSD",
                "side": "BUY",
                "type": "MARKET",
                "quantity": 0.01,
                "newClientOrderId": "client:test",
            },
        }
    ]


def test_binance_testnet_health_redacts_secrets_and_blocks_lifecycle_methods():
    fake = FakeBrokerHttpClient(response={"paper_equity": 12_345.0})
    adapter = BinanceTestnetBrokerAdapter(api_key="test-key", api_secret="test-secret", http_client=fake)
    now = datetime(2026, 4, 25, 6, 0, tzinfo=UTC)

    health = adapter.health_check(now=now)
    snapshot = adapter.get_account_snapshot(now=now)

    assert health["status"] == "healthy"
    assert health["base_url"] == "https://testnet.binance.vision"
    assert health["live_trading_available"] is False
    assert health["secret_values_redacted"] is True
    assert "test-key" not in str(health)
    assert "test-secret" not in str(health)
    assert snapshot.equity == 12_345.0
    assert adapter.cancel_order(order_id="broker-order:test")["status"] == "blocked"
    assert adapter.get_order_status(order_id="broker-order:test")["status"] == "unavailable"
    assert adapter.get_fills() == []


def test_sandbox_without_fake_client_is_blocked_by_default():
    adapter = build_broker_adapter(
        "SANDBOX",
        broker="binance_testnet",
        api_key="test-key",
        api_secret="test-secret",
    )

    with pytest.raises(RuntimeError, match="external calls are blocked"):
        adapter.submit_order(symbol="BTC-USD", side="BUY", quantity=0.01)
