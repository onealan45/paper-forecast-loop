from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from forecast_loop.models import PaperPortfolioSnapshot


class BrokerAdapter(Protocol):
    def get_account_snapshot(self, *, now: datetime) -> PaperPortfolioSnapshot:
        ...

    def submit_order(self, *, symbol: str, side: str, quantity: float) -> dict:
        ...

    def cancel_order(self, *, order_id: str) -> dict:
        ...


@dataclass(slots=True)
class PaperBrokerAdapter:
    starting_equity: float = 10_000.0

    def get_account_snapshot(self, *, now: datetime) -> PaperPortfolioSnapshot:
        return PaperPortfolioSnapshot.empty(created_at=now, equity=self.starting_equity)

    def submit_order(self, *, symbol: str, side: str, quantity: float) -> dict:
        return {
            "status": "paper_rejected",
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "reason": "Use the local paper-order ledger; broker submit is unavailable until a later paper execution stage.",
        }

    def cancel_order(self, *, order_id: str) -> dict:
        return {
            "status": "paper_noop",
            "order_id": order_id,
            "reason": "Paper order cancellation is not implemented until the order lifecycle stage.",
        }


def build_broker_adapter(mode: str = "paper") -> BrokerAdapter:
    if mode == "paper":
        return PaperBrokerAdapter()
    raise ValueError(f"broker mode '{mode}' is unavailable; only paper mode is supported as internal paper mode")
