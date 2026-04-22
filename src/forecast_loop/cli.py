from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from forecast_loop.config import LoopConfig
from forecast_loop.pipeline import ForecastingLoop
from forecast_loop.providers import CoinGeckoMarketDataProvider, build_sample_provider
from forecast_loop.storage import JsonFileRepository


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="forecast-loop")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_once = subparsers.add_parser("run-once")
    run_once.add_argument("--provider", choices=["sample", "coingecko"], default="sample")
    run_once.add_argument("--symbol", default="BTC-USD")
    run_once.add_argument("--storage-dir", required=True)
    run_once.add_argument("--horizon-hours", type=int, default=24)
    run_once.add_argument("--lookback-candles", type=int, default=8)
    run_once.add_argument("--now")

    args = parser.parse_args(argv)
    if args.command == "run-once":
        return _run_once(args)
    return 1


def _run_once(args) -> int:
    now = (
        datetime.fromisoformat(args.now).astimezone(UTC)
        if args.now
        else datetime.now(tz=UTC)
    )
    if args.provider == "sample":
        provider = build_sample_provider(now, args.symbol)
    else:
        provider = CoinGeckoMarketDataProvider()
    repository = JsonFileRepository(args.storage_dir)
    loop = ForecastingLoop(
        config=LoopConfig(
            symbol=args.symbol,
            horizon_hours=args.horizon_hours,
            lookback_candles=args.lookback_candles,
        ),
        data_provider=provider,
        repository=repository,
    )
    result = loop.run_cycle(now=now)
    _write_last_run_meta(
        storage_dir=Path(args.storage_dir),
        now_utc=now,
        symbol=args.symbol,
        provider=args.provider,
        result=result,
    )
    print(
        json.dumps(
            {
                "symbol": args.symbol,
                "new_forecast_status": result.new_forecast.status if result.new_forecast else None,
                "score_count": len(result.scores),
                "review_created": result.review is not None,
                "proposal_created": result.proposal is not None,
            }
        )
    )
    return 0


def _write_last_run_meta(*, storage_dir: Path, now_utc: datetime, symbol: str, provider: str, result) -> None:
    storage_dir.mkdir(parents=True, exist_ok=True)
    meta_path = storage_dir / "last_run_meta.json"
    payload = {
        "now_local": datetime.now().astimezone().isoformat(sep=" ", timespec="seconds"),
        "now_utc": now_utc.isoformat(),
        "workspace": str(Path.cwd()),
        "storage_dir": str(storage_dir.resolve()),
        "provider": provider,
        "symbol": symbol,
        "new_forecast": result.new_forecast.to_dict() if result.new_forecast else None,
        "score_count": len(result.scores),
        "score_ids": [score.score_id for score in result.scores],
        "review_id": result.review.review_id if result.review else None,
        "review_created": result.review is not None,
        "proposal_id": result.proposal.proposal_id if result.proposal else None,
        "proposal_created": result.proposal is not None,
    }
    tmp_path = meta_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(meta_path)


if __name__ == "__main__":
    raise SystemExit(main())
