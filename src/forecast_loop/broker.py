from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(slots=True)
class PaperBrokerAdapter:
    starting_equity: float = 10_000.0
    mode: BrokerMode = BrokerMode.INTERNAL_PAPER

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


def build_broker_adapter(mode: str = "paper") -> BrokerAdapter:
    normalized = mode.upper().replace("-", "_")
    aliases = {
        "PAPER": BrokerMode.INTERNAL_PAPER,
        "INTERNAL": BrokerMode.INTERNAL_PAPER,
        "INTERNAL_PAPER": BrokerMode.INTERNAL_PAPER,
    }
    broker_mode = aliases.get(normalized)
    if broker_mode == BrokerMode.INTERNAL_PAPER:
        return PaperBrokerAdapter()
    if normalized in {BrokerMode.EXTERNAL_PAPER.value, BrokerMode.SANDBOX.value}:
        raise ValueError(
            f"broker mode '{mode}' is defined by the M6A contract but not implemented yet; "
            "only INTERNAL_PAPER is available"
        )
    raise ValueError(
        f"broker mode '{mode}' is unavailable; only INTERNAL_PAPER is available and live mode is unsupported"
    )
