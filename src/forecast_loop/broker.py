from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from forecast_loop.models import PaperFill, PaperPortfolioSnapshot, PaperPosition


class BrokerMode(StrEnum):
    INTERNAL_PAPER = "INTERNAL_PAPER"
    EXTERNAL_PAPER = "EXTERNAL_PAPER"
    SANDBOX = "SANDBOX"


class BrokerAdapter(Protocol):
    @property
    def mode(self) -> BrokerMode:
        ...

    def get_account_snapshot(self, *, now: datetime) -> PaperPortfolioSnapshot:
        ...

    def get_positions(self, *, now: datetime) -> list[PaperPosition]:
        ...

    def submit_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        client_order_id: str | None = None,
    ) -> dict:
        ...

    def cancel_order(self, *, order_id: str) -> dict:
        ...

    def get_order_status(self, *, order_id: str) -> dict:
        ...

    def get_fills(self, *, since: datetime | None = None) -> list[PaperFill]:
        ...

    def health_check(self, *, now: datetime) -> dict:
        ...


class BrokerHttpClient(Protocol):
    def request(self, *, method: str, url: str, headers: dict[str, str], payload: dict | None = None) -> dict:
        ...


class BlockingBrokerHttpClient:
    def request(self, *, method: str, url: str, headers: dict[str, str], payload: dict | None = None) -> dict:
        raise RuntimeError("No broker HTTP client is configured; external calls are blocked by default")


@dataclass(slots=True)
class PaperBrokerAdapter:
    starting_equity: float = 10_000.0

    @property
    def mode(self) -> BrokerMode:
        return BrokerMode.INTERNAL_PAPER

    def get_account_snapshot(self, *, now: datetime) -> PaperPortfolioSnapshot:
        return PaperPortfolioSnapshot.empty(created_at=now, equity=self.starting_equity)

    def get_positions(self, *, now: datetime) -> list[PaperPosition]:
        return self.get_account_snapshot(now=now).positions

    def submit_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        client_order_id: str | None = None,
    ) -> dict:
        return {
            "status": "blocked",
            "mode": self.mode.value,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "client_order_id": client_order_id,
            "reason": (
                "M6A defines the broker adapter contract only. Use the local paper-order ledger; "
                "adapter submit is unavailable until gated paper/sandbox execution stages."
            ),
        }

    def cancel_order(self, *, order_id: str) -> dict:
        return {
            "status": "blocked",
            "mode": self.mode.value,
            "order_id": order_id,
            "reason": "M6A contract only; adapter cancellation is unavailable until the order lifecycle stage.",
        }

    def get_order_status(self, *, order_id: str) -> dict:
        return {
            "status": "unavailable",
            "mode": self.mode.value,
            "order_id": order_id,
            "reason": "No external or sandbox broker order lifecycle exists in M6A.",
        }

    def get_fills(self, *, since: datetime | None = None) -> list[PaperFill]:
        return []

    def health_check(self, *, now: datetime) -> dict:
        return {
            "status": "healthy",
            "mode": self.mode.value,
            "created_at": now.isoformat(),
            "live_trading_available": False,
            "external_submit_available": False,
            "reason": "Internal paper adapter is available; external paper/sandbox adapters are not implemented in M6A.",
        }


@dataclass(slots=True)
class BinanceTestnetBrokerAdapter:
    api_key: str = field(repr=False)
    api_secret: str = field(repr=False)
    http_client: BrokerHttpClient
    base_url: str = "https://testnet.binance.vision"

    def __post_init__(self) -> None:
        if not self.api_key or not self.api_secret:
            raise ValueError("Binance testnet adapter requires API key and API secret")
        if self.base_url != "https://testnet.binance.vision":
            raise ValueError("Binance testnet adapter refuses non-testnet endpoints")

    @property
    def mode(self) -> BrokerMode:
        return BrokerMode.SANDBOX

    def get_account_snapshot(self, *, now: datetime) -> PaperPortfolioSnapshot:
        response = self.http_client.request(
            method="GET",
            url=f"{self.base_url}/api/v3/account",
            headers=self._headers(),
        )
        equity = float(response.get("paper_equity", 0.0) or 0.0) if isinstance(response, dict) else 0.0
        return PaperPortfolioSnapshot.empty(created_at=now, equity=equity)

    def get_positions(self, *, now: datetime) -> list[PaperPosition]:
        return self.get_account_snapshot(now=now).positions

    def submit_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        client_order_id: str | None = None,
    ) -> dict:
        payload = {
            "symbol": self._to_binance_symbol(symbol),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": quantity,
        }
        if client_order_id:
            payload["newClientOrderId"] = client_order_id
        response = self.http_client.request(
            method="POST",
            url=f"{self.base_url}/api/v3/order/test",
            headers=self._headers(),
            payload=payload,
        )
        return {
            "status": "submitted",
            "mode": self.mode.value,
            "broker": "binance_testnet",
            "symbol": symbol,
            "side": side.upper(),
            "quantity": quantity,
            "order_type": order_type.upper(),
            "client_order_id": client_order_id,
            "broker_response": response,
        }

    def cancel_order(self, *, order_id: str) -> dict:
        return {
            "status": "blocked",
            "mode": self.mode.value,
            "broker": "binance_testnet",
            "order_id": order_id,
            "reason": "M6C does not implement sandbox cancellation lifecycle.",
        }

    def get_order_status(self, *, order_id: str) -> dict:
        return {
            "status": "unavailable",
            "mode": self.mode.value,
            "broker": "binance_testnet",
            "order_id": order_id,
            "reason": "M6C submit smoke uses test endpoint only; order status is deferred.",
        }

    def get_fills(self, *, since: datetime | None = None) -> list[PaperFill]:
        return []

    def health_check(self, *, now: datetime) -> dict:
        return {
            "status": "healthy",
            "mode": self.mode.value,
            "broker": "binance_testnet",
            "created_at": now.isoformat(),
            "base_url": self.base_url,
            "live_trading_available": False,
            "external_submit_available": True,
            "secret_values_redacted": True,
        }

    def _headers(self) -> dict[str, str]:
        return {"X-MBX-APIKEY": self.api_key}

    @staticmethod
    def _to_binance_symbol(symbol: str) -> str:
        return symbol.replace("-", "").upper()


def build_broker_adapter(
    mode: str = "paper",
    *,
    broker: str | None = None,
    api_key: str | None = None,
    api_secret: str | None = None,
    http_client: BrokerHttpClient | None = None,
) -> BrokerAdapter:
    normalized = mode.upper().replace("-", "_")
    aliases = {
        "PAPER": BrokerMode.INTERNAL_PAPER,
        "INTERNAL": BrokerMode.INTERNAL_PAPER,
        "INTERNAL_PAPER": BrokerMode.INTERNAL_PAPER,
    }
    broker_mode = aliases.get(normalized)
    if broker_mode == BrokerMode.INTERNAL_PAPER:
        return PaperBrokerAdapter()
    if normalized == BrokerMode.SANDBOX.value and (broker or "").lower() == "binance_testnet":
        if not api_key or not api_secret:
            raise ValueError("SANDBOX broker binance_testnet requires API key and API secret")
        return BinanceTestnetBrokerAdapter(
            api_key=api_key,
            api_secret=api_secret,
            http_client=http_client or BlockingBrokerHttpClient(),
        )
    if normalized in {BrokerMode.EXTERNAL_PAPER.value, BrokerMode.SANDBOX.value}:
        raise ValueError(
            f"broker mode '{mode}' requires an implemented sandbox/external paper broker; "
            "available sandbox broker: binance_testnet"
        )
    raise ValueError(
        f"broker mode '{mode}' is unavailable; only INTERNAL_PAPER is available and live mode is unsupported"
    )
