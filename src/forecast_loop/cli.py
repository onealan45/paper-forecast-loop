from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from forecast_loop.config import LoopConfig
from forecast_loop.dashboard import write_dashboard_html
from forecast_loop.decision import generate_strategy_decision
from forecast_loop.evaluation import build_evaluation_summary
from forecast_loop.health import run_health_check
from forecast_loop.maintenance import repair_storage
from forecast_loop.models import StrategyDecision
from forecast_loop.orders import create_paper_order_from_decision
from forecast_loop.pipeline import ForecastingLoop
from forecast_loop.providers import CoinGeckoMarketDataProvider, build_sample_provider
from forecast_loop.replay import ReplayRunner
from forecast_loop.sqlite_repository import (
    export_sqlite_to_jsonl,
    initialize_sqlite_database,
    migrate_jsonl_to_sqlite,
    sqlite_db_health,
)
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
    run_once.add_argument("--also-decide", action="store_true")

    replay_range = subparsers.add_parser("replay-range")
    replay_range.add_argument("--provider", choices=["sample"], default="sample")
    replay_range.add_argument("--symbol", default="BTC-USD")
    replay_range.add_argument("--storage-dir", required=True)
    replay_range.add_argument("--start", required=True)
    replay_range.add_argument("--end", required=True)
    replay_range.add_argument("--horizon-hours", type=int, default=24)
    replay_range.add_argument("--lookback-candles", type=int, default=8)

    render_dashboard = subparsers.add_parser("render-dashboard")
    render_dashboard.add_argument("--storage-dir", required=True)
    render_dashboard.add_argument("--output")

    repair_storage_cmd = subparsers.add_parser("repair-storage")
    repair_storage_cmd.add_argument("--storage-dir", required=True)

    decide = subparsers.add_parser("decide")
    decide.add_argument("--storage-dir", required=True)
    decide.add_argument("--symbol", default="BTC-USD")
    decide.add_argument("--horizon-hours", type=int, default=24)
    decide.add_argument("--now")

    health_check = subparsers.add_parser("health-check")
    health_check.add_argument("--storage-dir", required=True)
    health_check.add_argument("--symbol", default="BTC-USD")
    health_check.add_argument("--now")
    health_check.add_argument("--stale-after-hours", type=int, default=48)

    init_db = subparsers.add_parser("init-db")
    init_db.add_argument("--storage-dir", required=True)
    init_db.add_argument("--db-path")

    migrate_jsonl = subparsers.add_parser("migrate-jsonl-to-sqlite")
    migrate_jsonl.add_argument("--storage-dir", required=True)
    migrate_jsonl.add_argument("--db-path")

    export_jsonl = subparsers.add_parser("export-jsonl")
    export_jsonl.add_argument("--storage-dir", required=True)
    export_jsonl.add_argument("--output-dir", required=True)
    export_jsonl.add_argument("--db-path")

    db_health = subparsers.add_parser("db-health")
    db_health.add_argument("--storage-dir", required=True)
    db_health.add_argument("--db-path")

    paper_order = subparsers.add_parser("paper-order")
    paper_order.add_argument("--storage-dir", required=True)
    paper_order.add_argument("--decision-id", required=True)
    paper_order.add_argument("--symbol", default="BTC-USD")
    paper_order.add_argument("--now")

    args = parser.parse_args(argv)
    try:
        if args.command == "run-once":
            return _run_once(args)
        if args.command == "replay-range":
            return _replay_range(args)
        if args.command == "render-dashboard":
            return _render_dashboard(args)
        if args.command == "repair-storage":
            return _repair_storage(args)
        if args.command == "decide":
            return _decide(args)
        if args.command == "health-check":
            return _health_check(args)
        if args.command == "init-db":
            return _init_db(args)
        if args.command == "migrate-jsonl-to-sqlite":
            return _migrate_jsonl_to_sqlite(args)
        if args.command == "export-jsonl":
            return _export_jsonl(args)
        if args.command == "db-health":
            return _db_health(args)
        if args.command == "paper-order":
            return _paper_order(args)
    except ValueError as exc:
        parser.error(str(exc))
    return 1


def _run_once(args) -> int:
    now = _parse_datetime(args.now) if args.now else datetime.now(tz=UTC)
    provider = _build_data_provider(args.provider, now, args.symbol)
    repository = JsonFileRepository(args.storage_dir)
    try:
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
    except Exception as exc:
        _write_failed_run_meta(
            storage_dir=Path(args.storage_dir),
            now_utc=now,
            symbol=args.symbol,
            provider=args.provider,
            exc=exc,
        )
        health_result = run_health_check(
            storage_dir=args.storage_dir,
            symbol=args.symbol,
            now=now,
            create_repair_request=True,
        )
        print(
            json.dumps(
                {
                    "symbol": args.symbol,
                    "run_status": "failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "repair_required": health_result.repair_required,
                    "repair_request_id": health_result.repair_request_id,
                }
            )
        )
        return 1
    _write_last_run_meta(
        storage_dir=Path(args.storage_dir),
        now_utc=now,
        symbol=args.symbol,
        provider=args.provider,
        result=result,
    )
    decision = None
    if args.also_decide:
        health_result = run_health_check(
            storage_dir=args.storage_dir,
            symbol=args.symbol,
            now=now,
            create_repair_request=True,
        )
        decision = generate_strategy_decision(
            repository=repository,
            symbol=args.symbol,
            horizon_hours=args.horizon_hours,
            now=now,
            health_result=health_result,
        )
    print(
        json.dumps(
            {
                "symbol": args.symbol,
                "new_forecast_status": result.new_forecast.status if result.new_forecast else None,
                "score_count": len(result.scores),
                "review_created": result.review is not None,
                "proposal_created": result.proposal is not None,
                "decision_id": decision.decision_id if decision else None,
                "decision_action": decision.action if decision else None,
            }
        )
    )
    return 0 if result.new_forecast is not None else 1


def _build_data_provider(provider_name: str, now: datetime, symbol: str):
    if provider_name == "sample":
        return build_sample_provider(now, symbol)
    if symbol not in CoinGeckoMarketDataProvider.SYMBOL_MAP:
        supported_symbols = ", ".join(sorted(CoinGeckoMarketDataProvider.SYMBOL_MAP))
        raise ValueError(
            f"unsupported symbol for coingecko: {symbol}. "
            f"Supported symbols: {supported_symbols}."
        )
    return CoinGeckoMarketDataProvider()


def _replay_range(args) -> int:
    start = _parse_datetime(args.start)
    end = _parse_datetime(args.end)
    provider = _build_data_provider(args.provider, end, args.symbol)
    base_storage_dir = Path(args.storage_dir)
    replay_storage_dir = _replay_storage_dir(
        storage_dir=base_storage_dir,
        provider=args.provider,
        symbol=args.symbol,
        start_utc=start.astimezone(UTC),
        end_utc=end.astimezone(UTC),
    )
    repository = JsonFileRepository(replay_storage_dir)
    runner = ReplayRunner(
        config=LoopConfig(
            symbol=args.symbol,
            horizon_hours=args.horizon_hours,
            lookback_candles=args.lookback_candles,
        ),
        data_provider=provider,
        repository=repository,
    )
    result = runner.run_range(start=start, end=end)

    summary = _build_replay_scoped_summary(
        replay_id=f"replay:{args.provider}:{args.symbol}:{start.isoformat()}:{end.isoformat()}",
        generated_at=datetime.now(tz=UTC),
        symbol=args.symbol,
        start_utc=start.astimezone(UTC),
        end_utc=end.astimezone(UTC),
        repository=repository,
    )
    summary_repository = JsonFileRepository(base_storage_dir)
    summary_repository.save_evaluation_summary(summary)
    _write_last_replay_meta(
        storage_dir=base_storage_dir,
        start_utc=start.astimezone(UTC),
        end_utc=end.astimezone(UTC),
        symbol=args.symbol,
        provider=args.provider,
        result=result,
        summary=summary,
    )
    print(
        json.dumps(
            {
                "symbol": args.symbol,
                "cycles_run": result.cycles_run,
                "scores_created": result.scores_created,
                "evaluation_summary_id": summary.summary_id,
            }
        )
    )
    return 0


def _render_dashboard(args) -> int:
    output_path = write_dashboard_html(
        storage_dir=args.storage_dir,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "storage_dir": str(Path(args.storage_dir).resolve()),
                "dashboard_path": str(output_path.resolve()),
            }
        )
    )
    return 0


def _repair_storage(args) -> int:
    result = repair_storage(args.storage_dir)
    print(
        json.dumps(
            {
                "storage_dir": str(result.storage_dir.resolve()),
                "generated_at_utc": result.generated_at_utc.isoformat(),
                "quarantined_forecast_count": result.quarantined_forecast_count,
                "kept_forecast_count": result.kept_forecast_count,
                "active_forecast_count": result.active_forecast_count,
                "latest_forecast_id": result.latest_forecast_id,
                "status": result.status,
            }
        )
    )
    return 0


def _decide(args) -> int:
    now = _parse_datetime(args.now) if args.now else datetime.now(tz=UTC)
    storage_dir = Path(args.storage_dir)
    health_result = run_health_check(
        storage_dir=storage_dir,
        symbol=args.symbol,
        now=now,
        create_repair_request=True,
    )
    if health_result.repair_required and not storage_dir.is_dir():
        decision = StrategyDecision.build_fail_closed(
            symbol=args.symbol,
            horizon_hours=args.horizon_hours,
            created_at=now,
            blocked_reason="health_check_repair_required",
            reason_summary="health-check 需要修復；Codex 修復完成前停止新進場。",
            repair_request_id=health_result.repair_request_id,
        )
        print(json.dumps(decision.to_dict(), ensure_ascii=False))
        return 0

    repository = JsonFileRepository(storage_dir)
    decision = generate_strategy_decision(
        repository=repository,
        symbol=args.symbol,
        horizon_hours=args.horizon_hours,
        now=now,
        health_result=health_result,
    )
    print(json.dumps(decision.to_dict(), ensure_ascii=False))
    return 0


def _health_check(args) -> int:
    now = _parse_datetime(args.now) if args.now else datetime.now(tz=UTC)
    result = run_health_check(
        storage_dir=args.storage_dir,
        symbol=args.symbol,
        now=now,
        stale_after_hours=args.stale_after_hours,
        create_repair_request=True,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0 if result.severity != "blocking" else 2


def _init_db(args) -> int:
    result = initialize_sqlite_database(args.storage_dir, db_path=args.db_path)
    print(json.dumps(result, ensure_ascii=False))
    return 0


def _migrate_jsonl_to_sqlite(args) -> int:
    result = migrate_jsonl_to_sqlite(args.storage_dir, db_path=args.db_path)
    print(json.dumps(result, ensure_ascii=False))
    return 0


def _export_jsonl(args) -> int:
    result = export_sqlite_to_jsonl(
        args.storage_dir,
        output_dir=args.output_dir,
        db_path=args.db_path,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


def _db_health(args) -> int:
    result = sqlite_db_health(args.storage_dir, db_path=args.db_path)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "healthy" else 2


def _paper_order(args) -> int:
    now = _parse_datetime(args.now) if args.now else datetime.now(tz=UTC)
    storage_dir = Path(args.storage_dir)
    health_result = run_health_check(
        storage_dir=storage_dir,
        symbol=args.symbol,
        now=now,
        create_repair_request=True,
    )
    if health_result.severity == "blocking" or health_result.repair_required:
        result = create_paper_order_from_decision(
            repository=None,
            decision_id=args.decision_id,
            symbol=args.symbol,
            now=now,
            health_result=health_result,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False))
        return 0

    repository = JsonFileRepository(storage_dir)
    result = create_paper_order_from_decision(
        repository=repository,
        decision_id=args.decision_id,
        symbol=args.symbol,
        now=now,
        health_result=health_result,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
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
        "run_status": "forecast_created" if result.new_forecast else "forecast_missing",
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


def _write_failed_run_meta(*, storage_dir: Path, now_utc: datetime, symbol: str, provider: str, exc: Exception) -> None:
    storage_dir.mkdir(parents=True, exist_ok=True)
    meta_path = storage_dir / "last_run_meta.json"
    payload = {
        "now_local": datetime.now().astimezone().isoformat(sep=" ", timespec="seconds"),
        "now_utc": now_utc.isoformat(),
        "workspace": str(Path.cwd()),
        "storage_dir": str(storage_dir.resolve()),
        "provider": provider,
        "symbol": symbol,
        "run_status": "failed",
        "error_type": type(exc).__name__,
        "error": str(exc),
        "new_forecast": None,
        "score_count": 0,
        "score_ids": [],
        "review_id": None,
        "review_created": False,
        "proposal_id": None,
        "proposal_created": False,
    }
    tmp_path = meta_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(meta_path)


def _write_last_replay_meta(
    *,
    storage_dir: Path,
    start_utc: datetime,
    end_utc: datetime,
    symbol: str,
    provider: str,
    result,
    summary,
) -> None:
    storage_dir.mkdir(parents=True, exist_ok=True)
    meta_path = storage_dir / "last_replay_meta.json"
    payload = {
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "workspace": str(Path.cwd()),
        "storage_dir": str(storage_dir.resolve()),
        "provider": provider,
        "symbol": symbol,
        "start_utc": start_utc.isoformat(),
        "end_utc": end_utc.isoformat(),
        "cycles_run": result.cycles_run,
        "forecasts_created": result.forecasts_created,
        "scores_created": result.scores_created,
        "first_cycle_at": result.first_cycle_at.isoformat(),
        "last_cycle_at": result.last_cycle_at.isoformat(),
        "evaluation_summary": summary.to_dict(),
    }
    tmp_path = meta_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(meta_path)


def _parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"invalid datetime '{value}'. Expected ISO 8601 with timezone, "
            "for example 2026-04-21T12:00:00+00:00."
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(
            f"invalid datetime '{value}'. Datetimes must be timezone-aware, "
            "for example 2026-04-21T12:00:00+00:00."
        )
    return parsed.astimezone(UTC)


def _replay_storage_dir(
    *,
    storage_dir: Path,
    provider: str,
    symbol: str,
    start_utc: datetime,
    end_utc: datetime,
) -> Path:
    def _safe_timestamp(value: datetime) -> str:
        return value.strftime("%Y%m%dT%H%M%SZ")

    return (
        storage_dir
        / ".replay"
        / provider
        / symbol
        / f"{_safe_timestamp(start_utc)}-{_safe_timestamp(end_utc)}"
    )


def _build_replay_scoped_summary(
    *,
    replay_id: str,
    generated_at: datetime,
    symbol: str,
    start_utc: datetime,
    end_utc: datetime,
    repository: JsonFileRepository,
):
    forecasts = [
        forecast
        for forecast in repository.load_forecasts()
        if forecast.symbol == symbol and start_utc <= forecast.anchor_time <= end_utc
    ]
    forecast_ids = {forecast.forecast_id for forecast in forecasts}
    scores = [score for score in repository.load_scores() if score.forecast_id in forecast_ids]
    score_ids = {score.score_id for score in scores}
    reviews = [
        review
        for review in repository.load_reviews()
        if review.forecast_ids and set(review.forecast_ids).issubset(forecast_ids)
    ]
    review_ids = {review.review_id for review in reviews}
    proposals = [
        proposal
        for proposal in repository.load_proposals()
        if proposal.review_id in review_ids
        and proposal.score_ids
        and set(proposal.score_ids).issubset(score_ids)
    ]
    return build_evaluation_summary(
        replay_id=replay_id,
        generated_at=generated_at,
        forecasts=forecasts,
        scores=scores,
        reviews=reviews,
        proposals=proposals,
    )


if __name__ == "__main__":
    raise SystemExit(main())
