from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class Asset:
    symbol: str
    name: str
    asset_class: str
    market: str
    quote_currency: str
    timezone: str
    status: str
    default_provider: str | None
    data_status: str
    notes: str

    def to_dict(self) -> dict:
        return asdict(self)


ASSET_REGISTRY: tuple[Asset, ...] = (
    Asset(
        symbol="BTC-USD",
        name="Bitcoin / US Dollar",
        asset_class="crypto",
        market="global_crypto",
        quote_currency="USD",
        timezone="UTC",
        status="active",
        default_provider="coingecko",
        data_status="public_hourly_available",
        notes="Primary paper-only research symbol.",
    ),
    Asset(
        symbol="ETH-USD",
        name="Ethereum / US Dollar",
        asset_class="crypto",
        market="global_crypto",
        quote_currency="USD",
        timezone="UTC",
        status="active",
        default_provider="coingecko",
        data_status="public_hourly_available",
        notes="Data provider mapping exists; automation remains BTC-first until multi-asset stages.",
    ),
    Asset(
        symbol="SPY",
        name="SPDR S&P 500 ETF Trust",
        asset_class="etf",
        market="US",
        quote_currency="USD",
        timezone="America/New_York",
        status="planned",
        default_provider=None,
        data_status="provider_pending",
        notes="Requires market calendar and adjusted-close handling in M3D.",
    ),
    Asset(
        symbol="QQQ",
        name="Invesco QQQ Trust",
        asset_class="etf",
        market="US",
        quote_currency="USD",
        timezone="America/New_York",
        status="planned",
        default_provider=None,
        data_status="provider_pending",
        notes="Requires market calendar and adjusted-close handling in M3D.",
    ),
    Asset(
        symbol="TLT",
        name="iShares 20+ Year Treasury Bond ETF",
        asset_class="etf",
        market="US",
        quote_currency="USD",
        timezone="America/New_York",
        status="planned",
        default_provider=None,
        data_status="provider_pending",
        notes="Requires market calendar and adjusted-close handling in M3D.",
    ),
    Asset(
        symbol="GLD",
        name="SPDR Gold Shares",
        asset_class="etf",
        market="US",
        quote_currency="USD",
        timezone="America/New_York",
        status="planned",
        default_provider=None,
        data_status="provider_pending",
        notes="Requires market calendar and adjusted-close handling in M3D.",
    ),
    Asset(
        symbol="0050.TW",
        name="Yuanta Taiwan Top 50 ETF",
        asset_class="etf",
        market="TW",
        quote_currency="TWD",
        timezone="Asia/Taipei",
        status="inactive",
        default_provider=None,
        data_status="provider_pending",
        notes="Tracked for future Taiwan ETF research; inactive until calendar and provider support exist.",
    ),
)


def list_assets(*, status: str = "all") -> list[Asset]:
    if status == "all":
        return list(ASSET_REGISTRY)
    return [asset for asset in ASSET_REGISTRY if asset.status == status]


def get_asset(symbol: str) -> Asset | None:
    normalized = symbol.upper()
    return next((asset for asset in ASSET_REGISTRY if asset.symbol == normalized), None)
