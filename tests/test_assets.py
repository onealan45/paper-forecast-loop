import json

from forecast_loop.assets import get_asset, list_assets
from forecast_loop.cli import main


def test_asset_registry_contains_required_m3a_assets():
    assets = {asset.symbol: asset for asset in list_assets()}

    assert set(assets) == {"BTC-USD", "ETH-USD", "SPY", "QQQ", "TLT", "GLD", "0050.TW"}
    assert assets["BTC-USD"].status == "active"
    assert assets["ETH-USD"].default_provider == "coingecko"
    assert assets["SPY"].status == "planned"
    assert assets["0050.TW"].status == "inactive"


def test_asset_registry_status_filter():
    active_symbols = [asset.symbol for asset in list_assets(status="active")]
    planned_symbols = [asset.symbol for asset in list_assets(status="planned")]

    assert active_symbols == ["BTC-USD", "ETH-USD"]
    assert planned_symbols == ["SPY", "QQQ", "TLT", "GLD"]


def test_get_asset_is_case_insensitive():
    assert get_asset("btc-usd").symbol == "BTC-USD"
    assert get_asset("missing") is None


def test_cli_list_assets_outputs_json(capsys):
    assert main(["list-assets"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert [asset["symbol"] for asset in payload["assets"]] == [
        "BTC-USD",
        "ETH-USD",
        "SPY",
        "QQQ",
        "TLT",
        "GLD",
        "0050.TW",
    ]


def test_cli_list_assets_filters_and_outputs_text(capsys):
    assert main(["list-assets", "--status", "inactive", "--format", "text"]) == 0
    output = capsys.readouterr().out

    assert "0050.TW\tetf\tinactive\tTW\tnone" in output
    assert "BTC-USD" not in output
