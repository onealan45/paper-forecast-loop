from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from forecast_loop.assets import get_asset, list_assets
from forecast_loop.autopilot import (
    create_research_agenda,
    record_research_autopilot_run,
    record_revision_retest_autopilot_run,
)
from forecast_loop.automation_log import automation_step, record_automation_run
from forecast_loop.backtest import run_backtest
from forecast_loop.broker_lifecycle import create_broker_order_lifecycle
from forecast_loop.broker_reconciliation import run_broker_reconciliation
from forecast_loop.candle_store import (
    StoredCandleProvider,
    export_market_candles,
    import_market_candles,
    run_candle_health,
)
from forecast_loop.config import LoopConfig
from forecast_loop.control import record_control_event
from forecast_loop.dashboard import write_dashboard_html
from forecast_loop.decision import generate_strategy_decision
from forecast_loop.evaluation import build_evaluation_summary
from forecast_loop.event_edge import build_event_edge_evaluations
from forecast_loop.execution_safety import evaluate_execution_safety_gate
from forecast_loop.event_reliability import build_event_reliability
from forecast_loop.experiment_registry import record_experiment_trial, register_strategy_card
from forecast_loop.health import run_health_check
from forecast_loop.lineage_agenda import create_lineage_research_agenda
from forecast_loop.locked_evaluation import evaluate_leaderboard_gate, lock_evaluation_protocol
from forecast_loop.macro_events import import_macro_events, macro_calendar
from forecast_loop.market_reaction import build_market_reactions
from forecast_loop.maintenance import repair_storage
from forecast_loop.models import PaperControlAction, StrategyDecision
from forecast_loop.notifications import generate_notification_artifacts
from forecast_loop.operator_console import (
    OPERATOR_CONSOLE_PAGES,
    serve_operator_console,
    validate_local_bind_host,
    write_operator_console_page,
)
from forecast_loop.orders import create_paper_order_from_decision
from forecast_loop.paper_shadow import record_paper_shadow_outcome
from forecast_loop.pipeline import ForecastingLoop
from forecast_loop.provider_audit import AuditedMarketDataProvider
from forecast_loop.portfolio import create_portfolio_snapshot, fill_paper_order, save_portfolio_mark
from forecast_loop.providers import CoinGeckoMarketDataProvider, build_sample_provider
from forecast_loop.replay import ReplayRunner
from forecast_loop.research_dataset import build_research_dataset
from forecast_loop.research_report import generate_research_report
from forecast_loop.risk import evaluate_risk
from forecast_loop.market_calendar import parse_date
from forecast_loop.source_documents import import_source_documents
from forecast_loop.source_registry import source_registry_payload
from forecast_loop.stock_data import (
    import_stock_csv,
    market_calendar_payload,
    run_stock_candle_health,
)
from forecast_loop.strategy_evolution import propose_strategy_revision
from forecast_loop.strategy_lineage import build_strategy_lineage_summary
from forecast_loop.strategy_research import resolve_latest_strategy_research_chain
from forecast_loop.revision_retest import create_revision_retest_scaffold
from forecast_loop.revision_retest_executor import execute_revision_retest_next_task
from forecast_loop.revision_retest_plan import build_revision_retest_task_plan
from forecast_loop.revision_retest_run_log import record_revision_retest_task_run
from forecast_loop.sqlite_repository import (
    export_sqlite_to_jsonl,
    initialize_sqlite_database,
    migrate_jsonl_to_sqlite,
    sqlite_db_health,
)
from forecast_loop.storage import JsonFileRepository
from forecast_loop.walk_forward import run_walk_forward_validation


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
    replay_range.add_argument("--provider", choices=["stored", "sample"], default="stored")
    replay_range.add_argument("--symbol", default="BTC-USD")
    replay_range.add_argument("--storage-dir", required=True)
    replay_range.add_argument("--start", required=True)
    replay_range.add_argument("--end", required=True)
    replay_range.add_argument("--horizon-hours", type=int, default=24)
    replay_range.add_argument("--lookback-candles", type=int, default=8)

    render_dashboard = subparsers.add_parser("render-dashboard")
    render_dashboard.add_argument("--storage-dir", required=True)
    render_dashboard.add_argument("--output")

    operator_console = subparsers.add_parser("operator-console")
    operator_console.add_argument("--storage-dir", required=True)
    operator_console.add_argument("--symbol", default="BTC-USD")
    operator_console.add_argument("--host", default="127.0.0.1")
    operator_console.add_argument("--port", type=int, default=8765)
    operator_console.add_argument("--page", choices=OPERATOR_CONSOLE_PAGES, default="overview")
    operator_console.add_argument("--output")
    operator_console.add_argument("--now")

    strategy_lineage = subparsers.add_parser("strategy-lineage")
    strategy_lineage.add_argument("--storage-dir", required=True)
    strategy_lineage.add_argument("--symbol", default="BTC-USD")

    lineage_agenda_cmd = subparsers.add_parser("create-lineage-research-agenda")
    lineage_agenda_cmd.add_argument("--storage-dir", required=True)
    lineage_agenda_cmd.add_argument("--symbol", default="BTC-USD")
    lineage_agenda_cmd.add_argument("--created-at")

    operator_control = subparsers.add_parser("operator-control")
    operator_control.add_argument("--storage-dir", required=True)
    operator_control.add_argument("--action", choices=[item.value for item in PaperControlAction], required=True)
    operator_control.add_argument("--reason", required=True)
    operator_control.add_argument("--actor", default="operator")
    operator_control.add_argument("--symbol")
    operator_control.add_argument("--confirm", action="store_true")
    operator_control.add_argument("--max-position-pct", type=float)
    operator_control.add_argument("--now")

    repair_storage_cmd = subparsers.add_parser("repair-storage")
    repair_storage_cmd.add_argument("--storage-dir", required=True)

    decide = subparsers.add_parser("decide")
    decide.add_argument("--storage-dir", required=True)
    decide.add_argument("--symbol", default="BTC-USD")
    decide.add_argument("--horizon-hours", type=int, default=24)
    decide.add_argument("--now")

    decide_all = subparsers.add_parser("decide-all")
    decide_all.add_argument("--storage-dir", required=True)
    decide_all.add_argument("--symbols", required=True)
    decide_all.add_argument("--horizon-hours", type=int, default=24)
    decide_all.add_argument("--now")

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

    broker_order = subparsers.add_parser("broker-order")
    broker_order.add_argument("--storage-dir", required=True)
    broker_order.add_argument("--order-id", required=True)
    broker_order.add_argument("--broker", default="binance_testnet")
    broker_order.add_argument("--broker-mode", choices=["EXTERNAL_PAPER", "SANDBOX"], default="SANDBOX")
    broker_order.add_argument("--mock-submit-status", default="CREATED")
    broker_order.add_argument("--broker-order-ref")
    broker_order.add_argument("--now")

    broker_reconcile = subparsers.add_parser("broker-reconcile")
    broker_reconcile.add_argument("--storage-dir", required=True)
    broker_reconcile.add_argument("--external-snapshot", required=True)
    broker_reconcile.add_argument("--broker", default="binance_testnet")
    broker_reconcile.add_argument("--broker-mode", choices=["EXTERNAL_PAPER", "SANDBOX"], default="SANDBOX")
    broker_reconcile.add_argument("--cash-tolerance", type=float, default=0.01)
    broker_reconcile.add_argument("--equity-tolerance", type=float, default=0.01)
    broker_reconcile.add_argument("--position-tolerance", type=float, default=1e-9)
    broker_reconcile.add_argument("--now")

    execution_gate = subparsers.add_parser("execution-gate")
    execution_gate.add_argument("--storage-dir", required=True)
    execution_gate.add_argument("--symbol", default="BTC-USD")
    execution_gate.add_argument("--decision-id", default="latest")
    execution_gate.add_argument("--order-id", default="latest")
    execution_gate.add_argument("--broker", default="binance_testnet")
    execution_gate.add_argument("--broker-mode", choices=["EXTERNAL_PAPER", "SANDBOX"], default="SANDBOX")
    execution_gate.add_argument("--broker-health", required=True)
    execution_gate.add_argument("--min-evidence-grade", choices=["A", "B", "C", "D"], default="B")
    execution_gate.add_argument("--max-order-position-pct", type=float, default=0.10)
    execution_gate.add_argument("--now")

    paper_fill = subparsers.add_parser("paper-fill")
    paper_fill.add_argument("--storage-dir", required=True)
    paper_fill.add_argument("--order-id", required=True)
    paper_fill.add_argument("--symbol", default="BTC-USD")
    paper_fill.add_argument("--market-price", type=float, default=100.0)
    paper_fill.add_argument("--fee-bps", type=float, default=5.0)
    paper_fill.add_argument("--slippage-bps", type=float, default=10.0)
    paper_fill.add_argument("--now")

    portfolio_snapshot = subparsers.add_parser("portfolio-snapshot")
    portfolio_snapshot.add_argument("--storage-dir", required=True)
    portfolio_snapshot.add_argument("--symbol", default="BTC-USD")
    portfolio_snapshot.add_argument("--market-price", type=float, default=100.0)
    portfolio_snapshot.add_argument("--now")

    risk_check = subparsers.add_parser("risk-check")
    risk_check.add_argument("--storage-dir", required=True)
    risk_check.add_argument("--symbol", default="BTC-USD")
    risk_check.add_argument("--now")
    risk_check.add_argument("--max-position-pct", type=float, default=0.15)
    risk_check.add_argument("--max-gross-exposure-pct", type=float, default=0.20)
    risk_check.add_argument("--reduce-risk-drawdown-pct", type=float, default=0.05)
    risk_check.add_argument("--stop-new-entries-drawdown-pct", type=float, default=0.10)

    list_assets_cmd = subparsers.add_parser("list-assets")
    list_assets_cmd.add_argument("--status", choices=["all", "active", "planned", "inactive"], default="all")
    list_assets_cmd.add_argument("--format", choices=["json", "text"], default="json")

    import_candles = subparsers.add_parser("import-candles")
    import_candles.add_argument("--storage-dir", required=True)
    import_candles.add_argument("--input", required=True)
    import_candles.add_argument("--symbol", default="BTC-USD")
    import_candles.add_argument("--source", default="manual-jsonl")
    import_candles.add_argument("--imported-at")

    export_candles = subparsers.add_parser("export-candles")
    export_candles.add_argument("--storage-dir", required=True)
    export_candles.add_argument("--output", required=True)
    export_candles.add_argument("--symbol", default="BTC-USD")

    candle_health = subparsers.add_parser("candle-health")
    candle_health.add_argument("--storage-dir", required=True)
    candle_health.add_argument("--symbol", default="BTC-USD")
    candle_health.add_argument("--start", required=True)
    candle_health.add_argument("--end", required=True)
    candle_health.add_argument("--interval-minutes", type=int, default=60)

    import_stock_csv_cmd = subparsers.add_parser("import-stock-csv")
    import_stock_csv_cmd.add_argument("--storage-dir", required=True)
    import_stock_csv_cmd.add_argument("--input", required=True)
    import_stock_csv_cmd.add_argument("--symbol", default="SPY")
    import_stock_csv_cmd.add_argument("--source", default="csv-fixture")
    import_stock_csv_cmd.add_argument("--imported-at")

    stock_candle_health = subparsers.add_parser("stock-candle-health")
    stock_candle_health.add_argument("--storage-dir", required=True)
    stock_candle_health.add_argument("--symbol", default="SPY")
    stock_candle_health.add_argument("--start-date", required=True)
    stock_candle_health.add_argument("--end-date", required=True)

    market_calendar = subparsers.add_parser("market-calendar")
    market_calendar.add_argument("--market", choices=["US"], default="US")
    market_calendar.add_argument("--start-date", required=True)
    market_calendar.add_argument("--end-date", required=True)

    import_macro_events_cmd = subparsers.add_parser("import-macro-events")
    import_macro_events_cmd.add_argument("--storage-dir", required=True)
    import_macro_events_cmd.add_argument("--input", required=True)
    import_macro_events_cmd.add_argument("--source", default="macro-fixture")
    import_macro_events_cmd.add_argument("--imported-at")

    macro_calendar_cmd = subparsers.add_parser("macro-calendar")
    macro_calendar_cmd.add_argument("--storage-dir", required=True)
    macro_calendar_cmd.add_argument("--start", required=True)
    macro_calendar_cmd.add_argument("--end", required=True)
    macro_calendar_cmd.add_argument("--event-type")
    macro_calendar_cmd.add_argument("--region")

    import_source_documents_cmd = subparsers.add_parser("import-source-documents")
    import_source_documents_cmd.add_argument("--storage-dir", required=True)
    import_source_documents_cmd.add_argument("--input", required=True)
    import_source_documents_cmd.add_argument("--source", required=True)
    import_source_documents_cmd.add_argument("--imported-at")

    source_registry_cmd = subparsers.add_parser("source-registry")
    source_registry_cmd.add_argument("--storage-dir", required=True)
    source_registry_cmd.add_argument("--format", choices=["json", "text"], default="json")

    build_events_cmd = subparsers.add_parser("build-events")
    build_events_cmd.add_argument("--storage-dir", required=True)
    build_events_cmd.add_argument("--symbol")
    build_events_cmd.add_argument("--created-at", required=True)
    build_events_cmd.add_argument("--min-reliability-score", type=float, default=70.0)

    build_market_reactions_cmd = subparsers.add_parser("build-market-reactions")
    build_market_reactions_cmd.add_argument("--storage-dir", required=True)
    build_market_reactions_cmd.add_argument("--symbol")
    build_market_reactions_cmd.add_argument("--created-at", required=True)
    build_market_reactions_cmd.add_argument("--already-priced-return-threshold", type=float, default=0.03)
    build_market_reactions_cmd.add_argument("--volume-shock-z-threshold", type=float, default=3.0)

    build_event_edge_cmd = subparsers.add_parser("build-event-edge")
    build_event_edge_cmd.add_argument("--storage-dir", required=True)
    build_event_edge_cmd.add_argument("--symbol")
    build_event_edge_cmd.add_argument("--created-at", required=True)
    build_event_edge_cmd.add_argument("--horizon-hours", type=int, default=24)
    build_event_edge_cmd.add_argument("--min-sample-size", type=int, default=3)
    build_event_edge_cmd.add_argument("--estimated-cost-bps", type=float, default=10.0)

    build_research_dataset_cmd = subparsers.add_parser("build-research-dataset")
    build_research_dataset_cmd.add_argument("--storage-dir", required=True)
    build_research_dataset_cmd.add_argument("--symbol", default="BTC-USD")
    build_research_dataset_cmd.add_argument("--created-at")

    research_report_cmd = subparsers.add_parser("research-report")
    research_report_cmd.add_argument("--storage-dir", required=True)
    research_report_cmd.add_argument("--symbol", default="BTC-USD")
    research_report_cmd.add_argument("--created-at")
    research_report_cmd.add_argument("--output-dir", default=str(Path("reports") / "research"))

    backtest_cmd = subparsers.add_parser("backtest")
    backtest_cmd.add_argument("--storage-dir", required=True)
    backtest_cmd.add_argument("--symbol", default="BTC-USD")
    backtest_cmd.add_argument("--start", required=True)
    backtest_cmd.add_argument("--end", required=True)
    backtest_cmd.add_argument("--created-at")
    backtest_cmd.add_argument("--initial-cash", type=float, default=10_000.0)
    backtest_cmd.add_argument("--fee-bps", type=float, default=5.0)
    backtest_cmd.add_argument("--slippage-bps", type=float, default=10.0)
    backtest_cmd.add_argument("--moving-average-window", type=int, default=3)

    walk_forward_cmd = subparsers.add_parser("walk-forward")
    walk_forward_cmd.add_argument("--storage-dir", required=True)
    walk_forward_cmd.add_argument("--symbol", default="BTC-USD")
    walk_forward_cmd.add_argument("--start", required=True)
    walk_forward_cmd.add_argument("--end", required=True)
    walk_forward_cmd.add_argument("--created-at")
    walk_forward_cmd.add_argument("--train-size", type=int, default=4)
    walk_forward_cmd.add_argument("--validation-size", type=int, default=3)
    walk_forward_cmd.add_argument("--test-size", type=int, default=3)
    walk_forward_cmd.add_argument("--step-size", type=int, default=1)
    walk_forward_cmd.add_argument("--initial-cash", type=float, default=10_000.0)
    walk_forward_cmd.add_argument("--fee-bps", type=float, default=5.0)
    walk_forward_cmd.add_argument("--slippage-bps", type=float, default=10.0)
    walk_forward_cmd.add_argument("--moving-average-window", type=int, default=3)

    strategy_card_cmd = subparsers.add_parser("register-strategy-card")
    strategy_card_cmd.add_argument("--storage-dir", required=True)
    strategy_card_cmd.add_argument("--name", required=True)
    strategy_card_cmd.add_argument("--family", required=True)
    strategy_card_cmd.add_argument("--version", default="v1")
    strategy_card_cmd.add_argument("--status", choices=["DRAFT", "ACTIVE", "RETIRED", "QUARANTINED"], default="ACTIVE")
    strategy_card_cmd.add_argument("--symbol", action="append", required=True)
    strategy_card_cmd.add_argument("--hypothesis", required=True)
    strategy_card_cmd.add_argument("--signal-description", required=True)
    strategy_card_cmd.add_argument("--entry-rule", action="append", default=[])
    strategy_card_cmd.add_argument("--exit-rule", action="append", default=[])
    strategy_card_cmd.add_argument("--risk-rule", action="append", default=[])
    strategy_card_cmd.add_argument("--parameter", action="append", default=[])
    strategy_card_cmd.add_argument("--data-requirement", action="append", default=[])
    strategy_card_cmd.add_argument("--feature-snapshot-id", action="append", default=[])
    strategy_card_cmd.add_argument("--backtest-result-id", action="append", default=[])
    strategy_card_cmd.add_argument("--walk-forward-validation-id", action="append", default=[])
    strategy_card_cmd.add_argument("--event-edge-evaluation-id", action="append", default=[])
    strategy_card_cmd.add_argument("--parent-card-id")
    strategy_card_cmd.add_argument("--author", default="codex")
    strategy_card_cmd.add_argument("--created-at")

    experiment_trial_cmd = subparsers.add_parser("record-experiment-trial")
    experiment_trial_cmd.add_argument("--storage-dir", required=True)
    experiment_trial_cmd.add_argument("--strategy-card-id", required=True)
    experiment_trial_cmd.add_argument("--trial-index", type=int, required=True)
    experiment_trial_cmd.add_argument(
        "--status",
        choices=["PENDING", "RUNNING", "PASSED", "FAILED", "ABORTED", "INVALID"],
        required=True,
    )
    experiment_trial_cmd.add_argument("--symbol", required=True)
    experiment_trial_cmd.add_argument("--max-trials", type=int, required=True)
    experiment_trial_cmd.add_argument("--seed", type=int)
    experiment_trial_cmd.add_argument("--dataset-id")
    experiment_trial_cmd.add_argument("--backtest-result-id")
    experiment_trial_cmd.add_argument("--walk-forward-validation-id")
    experiment_trial_cmd.add_argument("--event-edge-evaluation-id")
    experiment_trial_cmd.add_argument("--prompt-hash")
    experiment_trial_cmd.add_argument("--code-hash")
    experiment_trial_cmd.add_argument("--parameter", action="append", default=[])
    experiment_trial_cmd.add_argument("--metric", action="append", default=[])
    experiment_trial_cmd.add_argument("--failure-reason")
    experiment_trial_cmd.add_argument("--started-at")
    experiment_trial_cmd.add_argument("--completed-at")
    experiment_trial_cmd.add_argument("--created-at")

    lock_evaluation_cmd = subparsers.add_parser("lock-evaluation-protocol")
    lock_evaluation_cmd.add_argument("--storage-dir", required=True)
    lock_evaluation_cmd.add_argument("--strategy-card-id", required=True)
    lock_evaluation_cmd.add_argument("--dataset-id", required=True)
    lock_evaluation_cmd.add_argument("--symbol", required=True)
    lock_evaluation_cmd.add_argument("--train-start", required=True)
    lock_evaluation_cmd.add_argument("--train-end", required=True)
    lock_evaluation_cmd.add_argument("--validation-start", required=True)
    lock_evaluation_cmd.add_argument("--validation-end", required=True)
    lock_evaluation_cmd.add_argument("--holdout-start", required=True)
    lock_evaluation_cmd.add_argument("--holdout-end", required=True)
    lock_evaluation_cmd.add_argument("--embargo-hours", type=int, default=24)
    lock_evaluation_cmd.add_argument("--fee-bps", type=float, default=5.0)
    lock_evaluation_cmd.add_argument("--slippage-bps", type=float, default=10.0)
    lock_evaluation_cmd.add_argument("--max-turnover", type=float, default=5.0)
    lock_evaluation_cmd.add_argument("--max-drawdown", type=float, default=0.10)
    lock_evaluation_cmd.add_argument("--baseline-suite-version", default="m4b-v1")
    lock_evaluation_cmd.add_argument("--locked-by", default="codex")
    lock_evaluation_cmd.add_argument("--created-at")

    leaderboard_gate_cmd = subparsers.add_parser("evaluate-leaderboard-gate")
    leaderboard_gate_cmd.add_argument("--storage-dir", required=True)
    leaderboard_gate_cmd.add_argument("--strategy-card-id", required=True)
    leaderboard_gate_cmd.add_argument("--trial-id", required=True)
    leaderboard_gate_cmd.add_argument("--split-manifest-id", required=True)
    leaderboard_gate_cmd.add_argument("--cost-model-id", required=True)
    leaderboard_gate_cmd.add_argument("--baseline-id", required=True)
    leaderboard_gate_cmd.add_argument("--backtest-result-id", required=True)
    leaderboard_gate_cmd.add_argument("--walk-forward-validation-id", required=True)
    leaderboard_gate_cmd.add_argument("--event-edge-evaluation-id")
    leaderboard_gate_cmd.add_argument("--created-at")

    paper_shadow_cmd = subparsers.add_parser("record-paper-shadow-outcome")
    paper_shadow_cmd.add_argument("--storage-dir", required=True)
    paper_shadow_cmd.add_argument("--leaderboard-entry-id", required=True)
    paper_shadow_cmd.add_argument("--window-start", required=True)
    paper_shadow_cmd.add_argument("--window-end", required=True)
    paper_shadow_cmd.add_argument("--observed-return", type=float, required=True)
    paper_shadow_cmd.add_argument("--benchmark-return", type=float, required=True)
    paper_shadow_cmd.add_argument("--max-adverse-excursion", type=float)
    paper_shadow_cmd.add_argument("--turnover", type=float)
    paper_shadow_cmd.add_argument("--note")
    paper_shadow_cmd.add_argument("--created-at")

    research_agenda_cmd = subparsers.add_parser("create-research-agenda")
    research_agenda_cmd.add_argument("--storage-dir", required=True)
    research_agenda_cmd.add_argument("--symbol", required=True)
    research_agenda_cmd.add_argument("--title", required=True)
    research_agenda_cmd.add_argument("--hypothesis", required=True)
    research_agenda_cmd.add_argument("--strategy-family", required=True)
    research_agenda_cmd.add_argument("--strategy-card-id", action="append", default=[])
    research_agenda_cmd.add_argument("--priority", default="HIGH")
    research_agenda_cmd.add_argument("--created-at")

    research_autopilot_cmd = subparsers.add_parser("record-research-autopilot-run")
    research_autopilot_cmd.add_argument("--storage-dir", required=True)
    research_autopilot_cmd.add_argument("--agenda-id", required=True)
    research_autopilot_cmd.add_argument("--strategy-card-id", required=True)
    research_autopilot_cmd.add_argument("--experiment-trial-id", required=True)
    research_autopilot_cmd.add_argument("--locked-evaluation-id", required=True)
    research_autopilot_cmd.add_argument("--leaderboard-entry-id", required=True)
    research_autopilot_cmd.add_argument("--strategy-decision-id")
    research_autopilot_cmd.add_argument("--paper-shadow-outcome-id")
    research_autopilot_cmd.add_argument("--created-at")

    strategy_revision_cmd = subparsers.add_parser("propose-strategy-revision")
    strategy_revision_cmd.add_argument("--storage-dir", required=True)
    strategy_revision_cmd.add_argument("--paper-shadow-outcome-id", required=True)
    strategy_revision_cmd.add_argument("--author", default="codex-strategy-evolution")
    strategy_revision_cmd.add_argument("--revision-version")
    strategy_revision_cmd.add_argument("--created-at")

    revision_retest_cmd = subparsers.add_parser("create-revision-retest-scaffold")
    revision_retest_cmd.add_argument("--storage-dir", required=True)
    revision_retest_cmd.add_argument("--revision-card-id")
    revision_retest_cmd.add_argument("--symbol", default="BTC-USD")
    revision_retest_cmd.add_argument("--dataset-id", required=True)
    revision_retest_cmd.add_argument("--max-trials", type=int, default=20)
    revision_retest_cmd.add_argument("--seed", type=int)
    revision_retest_cmd.add_argument("--train-start")
    revision_retest_cmd.add_argument("--train-end")
    revision_retest_cmd.add_argument("--validation-start")
    revision_retest_cmd.add_argument("--validation-end")
    revision_retest_cmd.add_argument("--holdout-start")
    revision_retest_cmd.add_argument("--holdout-end")
    revision_retest_cmd.add_argument("--embargo-hours", type=int, default=24)
    revision_retest_cmd.add_argument("--fee-bps", type=float, default=5.0)
    revision_retest_cmd.add_argument("--slippage-bps", type=float, default=10.0)
    revision_retest_cmd.add_argument("--max-turnover", type=float, default=5.0)
    revision_retest_cmd.add_argument("--max-drawdown", type=float, default=0.10)
    revision_retest_cmd.add_argument("--baseline-suite-version", default="m4b-v1")
    revision_retest_cmd.add_argument("--locked-by", default="codex")
    revision_retest_cmd.add_argument("--created-at")

    revision_retest_plan_cmd = subparsers.add_parser("revision-retest-plan")
    revision_retest_plan_cmd.add_argument("--storage-dir", required=True)
    revision_retest_plan_cmd.add_argument("--revision-card-id")
    revision_retest_plan_cmd.add_argument("--symbol", default="BTC-USD")

    record_retest_task_run_cmd = subparsers.add_parser("record-revision-retest-task-run")
    record_retest_task_run_cmd.add_argument("--storage-dir", required=True)
    record_retest_task_run_cmd.add_argument("--revision-card-id")
    record_retest_task_run_cmd.add_argument("--symbol", default="BTC-USD")
    record_retest_task_run_cmd.add_argument("--now")

    record_retest_autopilot_run_cmd = subparsers.add_parser("record-revision-retest-autopilot-run")
    record_retest_autopilot_run_cmd.add_argument("--storage-dir", required=True)
    record_retest_autopilot_run_cmd.add_argument("--revision-card-id")
    record_retest_autopilot_run_cmd.add_argument("--symbol", default="BTC-USD")
    record_retest_autopilot_run_cmd.add_argument("--now")

    execute_retest_task_cmd = subparsers.add_parser("execute-revision-retest-next-task")
    execute_retest_task_cmd.add_argument("--storage-dir", required=True)
    execute_retest_task_cmd.add_argument("--revision-card-id")
    execute_retest_task_cmd.add_argument("--symbol", default="BTC-USD")
    execute_retest_task_cmd.add_argument("--now")
    execute_retest_task_cmd.add_argument("--shadow-window-start")
    execute_retest_task_cmd.add_argument("--shadow-window-end")
    execute_retest_task_cmd.add_argument("--shadow-observed-return", type=float)
    execute_retest_task_cmd.add_argument("--shadow-benchmark-return", type=float)
    execute_retest_task_cmd.add_argument("--shadow-max-adverse-excursion", type=float)
    execute_retest_task_cmd.add_argument("--shadow-turnover", type=float)
    execute_retest_task_cmd.add_argument("--shadow-note")

    args = parser.parse_args(argv)
    try:
        if args.command == "run-once":
            return _run_once(args)
        if args.command == "replay-range":
            return _replay_range(args)
        if args.command == "render-dashboard":
            return _render_dashboard(args)
        if args.command == "operator-console":
            return _operator_console(args)
        if args.command == "strategy-lineage":
            return _strategy_lineage(args)
        if args.command == "create-lineage-research-agenda":
            return _create_lineage_research_agenda(args)
        if args.command == "operator-control":
            return _operator_control(args)
        if args.command == "repair-storage":
            return _repair_storage(args)
        if args.command == "decide":
            return _decide(args)
        if args.command == "decide-all":
            return _decide_all(args)
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
        if args.command == "broker-order":
            return _broker_order(args)
        if args.command == "broker-reconcile":
            return _broker_reconcile(args)
        if args.command == "execution-gate":
            return _execution_gate(args)
        if args.command == "paper-fill":
            return _paper_fill(args)
        if args.command == "portfolio-snapshot":
            return _portfolio_snapshot(args)
        if args.command == "risk-check":
            return _risk_check(args)
        if args.command == "list-assets":
            return _list_assets(args)
        if args.command == "import-candles":
            return _import_candles(args)
        if args.command == "export-candles":
            return _export_candles(args)
        if args.command == "candle-health":
            return _candle_health(args)
        if args.command == "import-stock-csv":
            return _import_stock_csv(args)
        if args.command == "stock-candle-health":
            return _stock_candle_health(args)
        if args.command == "market-calendar":
            return _market_calendar(args)
        if args.command == "import-macro-events":
            return _import_macro_events(args)
        if args.command == "macro-calendar":
            return _macro_calendar(args)
        if args.command == "import-source-documents":
            return _import_source_documents(args)
        if args.command == "source-registry":
            return _source_registry(args)
        if args.command == "build-events":
            return _build_events(args)
        if args.command == "build-market-reactions":
            return _build_market_reactions(args)
        if args.command == "build-event-edge":
            return _build_event_edge(args)
        if args.command == "build-research-dataset":
            return _build_research_dataset(args)
        if args.command == "research-report":
            return _research_report(args)
        if args.command == "backtest":
            return _backtest(args)
        if args.command == "walk-forward":
            return _walk_forward(args)
        if args.command == "register-strategy-card":
            return _register_strategy_card(args)
        if args.command == "record-experiment-trial":
            return _record_experiment_trial(args)
        if args.command == "lock-evaluation-protocol":
            return _lock_evaluation_protocol(args)
        if args.command == "evaluate-leaderboard-gate":
            return _evaluate_leaderboard_gate(args)
        if args.command == "record-paper-shadow-outcome":
            return _record_paper_shadow_outcome(args)
        if args.command == "create-research-agenda":
            return _create_research_agenda(args)
        if args.command == "record-research-autopilot-run":
            return _record_research_autopilot_run(args)
        if args.command == "propose-strategy-revision":
            return _propose_strategy_revision(args)
        if args.command == "create-revision-retest-scaffold":
            return _create_revision_retest_scaffold(args)
        if args.command == "revision-retest-plan":
            return _revision_retest_plan(args)
        if args.command == "record-revision-retest-task-run":
            return _record_revision_retest_task_run(args)
        if args.command == "record-revision-retest-autopilot-run":
            return _record_revision_retest_autopilot_run(args)
        if args.command == "execute-revision-retest-next-task":
            return _execute_revision_retest_next_task(args)
    except ValueError as exc:
        parser.error(str(exc))
    return 1


def _run_once(args) -> int:
    now = _parse_datetime(args.now) if args.now else datetime.now(tz=UTC)
    started_at = now
    repository = JsonFileRepository(args.storage_dir)
    provider = AuditedMarketDataProvider(
        provider=_build_data_provider(args.provider, now, args.symbol),
        provider_name=args.provider,
        repository=repository,
    )
    steps: list[dict[str, str | None]] = []
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
        steps.extend(_cycle_steps(result))
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
        notifications = generate_notification_artifacts(
            repository=repository,
            symbol=args.symbol,
            now=now,
            health_result=health_result,
        )
        steps.append(automation_step("run_cycle", "failed", type(exc).__name__))
        steps.append(
            automation_step(
                "notifications",
                "completed" if notifications else "skipped",
                ",".join(notification.notification_id for notification in notifications) if notifications else None,
            )
        )
        automation_run = record_automation_run(
            repository=repository,
            started_at=started_at,
            completed_at=now,
            status="failed",
            symbol=args.symbol,
            provider=args.provider,
            command="run-once",
            steps=steps,
            health_result=health_result,
            decision=None,
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
                    "automation_run_id": automation_run.automation_run_id,
                    "notification_count": len(notifications),
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
    health_result = None
    notifications = []
    if args.also_decide:
        health_result = run_health_check(
            storage_dir=args.storage_dir,
            symbol=args.symbol,
            now=now,
            create_repair_request=True,
        )
        steps.append(automation_step("health_check", "completed", health_result.check_id))
        risk_snapshot = None
        if not health_result.repair_required:
            risk_snapshot = evaluate_risk(
                repository=repository,
                symbol=args.symbol,
                now=now,
            )
            steps.append(automation_step("risk_check", "completed", risk_snapshot.risk_id))
        else:
            steps.append(automation_step("risk_check", "skipped", health_result.repair_request_id))
        decision = generate_strategy_decision(
            repository=repository,
            symbol=args.symbol,
            horizon_hours=args.horizon_hours,
            now=now,
            health_result=health_result,
            risk_snapshot=risk_snapshot,
        )
        steps.append(automation_step("decide", "completed", decision.decision_id))
        notifications = generate_notification_artifacts(
            repository=repository,
            symbol=args.symbol,
            now=now,
            decision=decision,
            health_result=health_result,
            risk_snapshot=risk_snapshot,
        )
        steps.append(
            automation_step(
                "notifications",
                "completed" if notifications else "skipped",
                ",".join(notification.notification_id for notification in notifications) if notifications else None,
            )
        )
    automation_status = "repair_required" if health_result and health_result.repair_required else "completed"
    automation_run = record_automation_run(
        repository=repository,
        started_at=started_at,
        completed_at=now,
        status=automation_status,
        symbol=args.symbol,
        provider=args.provider,
        command="run-once",
        steps=steps,
        health_result=health_result,
        decision=decision,
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
                "automation_run_id": automation_run.automation_run_id,
                "notification_count": len(notifications),
            }
        )
    )
    return 0 if result.new_forecast is not None else 1


def _cycle_steps(result) -> list[dict[str, str | None]]:
    return [
        automation_step(
            "forecast",
            "created" if result.new_forecast else "missing",
            result.new_forecast.forecast_id if result.new_forecast else None,
        ),
        automation_step(
            "score",
            "completed" if result.scores else "skipped",
            ",".join(score.score_id for score in result.scores) if result.scores else None,
        ),
        automation_step(
            "review",
            "created" if result.review else "skipped",
            result.review.review_id if result.review else None,
        ),
        automation_step(
            "proposal",
            "created" if result.proposal else "skipped",
            result.proposal.proposal_id if result.proposal else None,
        ),
    ]


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
    base_storage_dir = Path(args.storage_dir)
    provider = _build_replay_provider(args.provider, end, args.symbol, base_storage_dir)
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


def _build_replay_provider(provider_name: str, end: datetime, symbol: str, storage_dir: Path):
    if provider_name == "stored":
        repository = JsonFileRepository(storage_dir)
        if not any(record.symbol == symbol for record in repository.load_market_candles()):
            raise ValueError(f"no stored market candles found for {symbol}. Run import-candles first.")
        return StoredCandleProvider(repository)
    return _build_data_provider(provider_name, end, symbol)


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


def _operator_console(args) -> int:
    now = _parse_datetime(args.now) if args.now else datetime.now(tz=UTC)
    if args.output:
        output_path = write_operator_console_page(
            storage_dir=args.storage_dir,
            output=args.output,
            page=args.page,
            symbol=args.symbol,
            now=now,
        )
        print(
            json.dumps(
                {
                    "storage_dir": str(Path(args.storage_dir).resolve()),
                    "console_path": str(output_path.resolve()),
                    "page": args.page,
                    "mode": "render_once",
                },
                ensure_ascii=False,
            )
        )
        return 0
    validate_local_bind_host(args.host)
    print(
        json.dumps(
            {
                "storage_dir": str(Path(args.storage_dir).resolve()),
                "url": f"http://{args.host}:{args.port}/{args.page}",
                "mode": "serve_forever",
                "local_only": True,
            },
            ensure_ascii=False,
        )
    )
    serve_operator_console(
        storage_dir=args.storage_dir,
        host=args.host,
        port=args.port,
        symbol=args.symbol,
        now=now,
    )
    return 0


def _strategy_lineage(args) -> int:
    storage_dir = Path(args.storage_dir)
    if not storage_dir.exists():
        raise ValueError(f"storage directory does not exist: {storage_dir}")
    if not storage_dir.is_dir():
        raise ValueError(f"storage path is not a directory: {storage_dir}")
    repository = JsonFileRepository(storage_dir)
    symbol = args.symbol.upper()
    strategy_cards = [item for item in repository.load_strategy_cards() if symbol in item.symbols]
    paper_shadow_outcomes = [item for item in repository.load_paper_shadow_outcomes() if item.symbol == symbol]
    research_chain = resolve_latest_strategy_research_chain(
        symbol=symbol,
        strategy_cards=strategy_cards,
        experiment_trials=repository.load_experiment_trials(),
        locked_evaluations=repository.load_locked_evaluation_results(),
        split_manifests=repository.load_split_manifests(),
        leaderboard_entries=repository.load_leaderboard_entries(),
        paper_shadow_outcomes=paper_shadow_outcomes,
        research_agendas=repository.load_research_agendas(),
        research_autopilot_runs=repository.load_research_autopilot_runs(),
    )
    summary = build_strategy_lineage_summary(
        root_card=research_chain.strategy_card,
        strategy_cards=strategy_cards,
        paper_shadow_outcomes=paper_shadow_outcomes,
    )
    print(
        json.dumps(
            {
                "storage_dir": str(storage_dir.resolve()),
                "symbol": symbol,
                "strategy_lineage": asdict(summary) if summary else None,
            },
            ensure_ascii=False,
        )
    )
    return 0


def _create_lineage_research_agenda(args) -> int:
    storage_dir = Path(args.storage_dir)
    if not storage_dir.exists():
        raise ValueError(f"storage directory does not exist: {storage_dir}")
    if not storage_dir.is_dir():
        raise ValueError(f"storage path is not a directory: {storage_dir}")
    created_at = _parse_datetime(args.created_at) if args.created_at else datetime.now(tz=UTC)
    result = create_lineage_research_agenda(
        repository=JsonFileRepository(storage_dir),
        created_at=created_at,
        symbol=args.symbol,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _operator_control(args) -> int:
    now = _parse_datetime(args.now) if args.now else datetime.now(tz=UTC)
    storage_dir = Path(args.storage_dir)
    if not storage_dir.exists():
        raise ValueError(f"storage directory does not exist: {storage_dir}")
    if not storage_dir.is_dir():
        raise ValueError(f"storage path is not a directory: {storage_dir}")
    repository = JsonFileRepository(storage_dir)
    result = record_control_event(
        repository=repository,
        action=args.action,
        now=now,
        reason=args.reason,
        actor=args.actor,
        symbol=args.symbol,
        confirmed=args.confirm,
        max_position_pct=args.max_position_pct,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0 if result.status == "recorded" else 2


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
    decision = _decision_for_symbol(
        storage_dir=Path(args.storage_dir),
        symbol=args.symbol,
        horizon_hours=args.horizon_hours,
        now=now,
    )
    print(json.dumps(decision.to_dict(), ensure_ascii=False))
    return 0


def _decide_all(args) -> int:
    now = _parse_datetime(args.now) if args.now else datetime.now(tz=UTC)
    symbols = _parse_symbol_list(args.symbols)
    storage_dir = Path(args.storage_dir)
    decisions = [
        _decision_for_symbol(
            storage_dir=storage_dir,
            symbol=symbol,
            horizon_hours=args.horizon_hours,
            now=now,
        )
        for symbol in symbols
    ]
    payload = {
        "created_at": now.isoformat(),
        "storage_dir": str(storage_dir.resolve()),
        "symbols": symbols,
        "horizon_hours": args.horizon_hours,
        "decision_count": len(decisions),
        "tradeable_count": sum(1 for decision in decisions if decision.tradeable),
        "blocked_count": sum(1 for decision in decisions if decision.blocked_reason is not None),
        "decisions": [decision.to_dict() for decision in decisions],
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def _decision_for_symbol(
    *,
    storage_dir: Path,
    symbol: str,
    horizon_hours: int,
    now: datetime,
) -> StrategyDecision:
    health_result = run_health_check(
        storage_dir=storage_dir,
        symbol=symbol,
        now=now,
        create_repair_request=True,
    )
    if health_result.repair_required and not storage_dir.is_dir():
        return StrategyDecision.build_fail_closed(
            symbol=symbol,
            horizon_hours=horizon_hours,
            created_at=now,
            blocked_reason="health_check_repair_required",
            reason_summary="health-check 需要修復；Codex 修復完成前停止新進場。",
            repair_request_id=health_result.repair_request_id,
        )

    repository = JsonFileRepository(storage_dir)
    risk_snapshot = None
    if not health_result.repair_required:
        risk_snapshot = evaluate_risk(
            repository=repository,
            symbol=symbol,
            now=now,
        )
    return generate_strategy_decision(
        repository=repository,
        symbol=symbol,
        horizon_hours=horizon_hours,
        now=now,
        health_result=health_result,
        risk_snapshot=risk_snapshot,
    )


def _parse_symbol_list(value: str) -> list[str]:
    raw_symbols = [item.strip().upper() for item in value.split(",")]
    if any(not item for item in raw_symbols):
        raise ValueError("--symbols must be a comma-separated list without empty entries")
    symbols = list(dict.fromkeys(raw_symbols))
    if not symbols:
        raise ValueError("--symbols must include at least one symbol")
    unsupported = [symbol for symbol in symbols if get_asset(symbol) is None]
    if unsupported:
        raise ValueError(f"unsupported asset symbol(s): {', '.join(unsupported)}; run list-assets")
    return symbols


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


def _broker_order(args) -> int:
    now = _parse_datetime(args.now) if args.now else datetime.now(tz=UTC)
    repository = JsonFileRepository(args.storage_dir)
    result = create_broker_order_lifecycle(
        repository=repository,
        order_id=args.order_id,
        now=now,
        broker=args.broker,
        broker_mode=args.broker_mode,
        mock_submit_status=args.mock_submit_status,
        broker_order_ref=args.broker_order_ref,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _broker_reconcile(args) -> int:
    now = _parse_datetime(args.now) if args.now else datetime.now(tz=UTC)
    snapshot_path = Path(args.external_snapshot)
    if not snapshot_path.exists():
        raise ValueError(f"external snapshot file does not exist: {snapshot_path}")
    try:
        external_snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"external snapshot file is not valid JSON: {snapshot_path}: {exc}") from exc
    repository = JsonFileRepository(args.storage_dir)
    reconciliation = run_broker_reconciliation(
        repository=repository,
        external_snapshot=external_snapshot,
        now=now,
        broker=args.broker,
        broker_mode=args.broker_mode,
        cash_tolerance=args.cash_tolerance,
        equity_tolerance=args.equity_tolerance,
        position_tolerance=args.position_tolerance,
    )
    print(json.dumps(reconciliation.to_dict(), ensure_ascii=False))
    return 0 if reconciliation.severity != "blocking" else 2


def _execution_gate(args) -> int:
    now = _parse_datetime(args.now) if args.now else datetime.now(tz=UTC)
    health_path = Path(args.broker_health)
    if not health_path.exists():
        raise ValueError(f"broker health file does not exist: {health_path}")
    try:
        broker_health = json.loads(health_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"broker health file is not valid JSON: {health_path}: {exc}") from exc
    storage_dir = Path(args.storage_dir)
    repository = JsonFileRepository(storage_dir)
    gate = evaluate_execution_safety_gate(
        repository=repository,
        storage_dir=storage_dir,
        symbol=args.symbol,
        now=now,
        broker=args.broker,
        broker_mode=args.broker_mode,
        broker_health=broker_health,
        decision_id=args.decision_id,
        order_id=args.order_id,
        min_evidence_grade=args.min_evidence_grade,
        max_order_position_pct=args.max_order_position_pct,
    )
    print(json.dumps(gate.to_dict(), ensure_ascii=False))
    return 0 if gate.allowed else 2


def _paper_fill(args) -> int:
    now = _parse_datetime(args.now) if args.now else datetime.now(tz=UTC)
    storage_dir = Path(args.storage_dir)
    health_result = run_health_check(
        storage_dir=storage_dir,
        symbol=args.symbol,
        now=now,
        create_repair_request=True,
    )
    if health_result.severity == "blocking" or health_result.repair_required:
        print(
            json.dumps(
                {
                    "status": "skipped",
                    "reason": "health_blocking",
                    "order_id": None if args.order_id == "latest" else args.order_id,
                    "fill_id": None,
                },
                ensure_ascii=False,
            )
        )
        return 0
    repository = JsonFileRepository(storage_dir)
    result = fill_paper_order(
        repository=repository,
        order_id=args.order_id,
        now=now,
        market_price=args.market_price,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _portfolio_snapshot(args) -> int:
    now = _parse_datetime(args.now) if args.now else datetime.now(tz=UTC)
    storage_dir = Path(args.storage_dir)
    health_result = run_health_check(
        storage_dir=storage_dir,
        symbol=args.symbol,
        now=now,
        create_repair_request=True,
    )
    if health_result.severity == "blocking" or health_result.repair_required:
        print(
            json.dumps(
                {
                    "status": "skipped",
                    "reason": "health_blocking",
                    "snapshot_id": None,
                },
                ensure_ascii=False,
            )
        )
        return 0
    repository = JsonFileRepository(storage_dir)
    snapshot = create_portfolio_snapshot(
        repository=repository,
        now=now,
        market_price=args.market_price,
        symbol=args.symbol,
    )
    point = save_portfolio_mark(repository, snapshot)
    print(
        json.dumps(
            {
                "status": "created",
                "snapshot_id": snapshot.snapshot_id,
                "equity_curve_point_id": point.point_id,
                "portfolio_snapshot": snapshot.to_dict(),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _risk_check(args) -> int:
    now = _parse_datetime(args.now) if args.now else datetime.now(tz=UTC)
    storage_dir = Path(args.storage_dir)
    if not storage_dir.exists():
        raise ValueError(f"storage directory does not exist: {storage_dir}")
    if not storage_dir.is_dir():
        raise ValueError(f"storage path is not a directory: {storage_dir}")
    repository = JsonFileRepository(storage_dir)
    snapshot = evaluate_risk(
        repository=repository,
        symbol=args.symbol,
        now=now,
        max_position_pct=args.max_position_pct,
        max_gross_exposure_pct=args.max_gross_exposure_pct,
        reduce_risk_drawdown_pct=args.reduce_risk_drawdown_pct,
        stop_new_entries_drawdown_pct=args.stop_new_entries_drawdown_pct,
    )
    print(json.dumps(snapshot.to_dict(), ensure_ascii=False))
    return 0 if snapshot.severity != "blocking" else 2


def _list_assets(args) -> int:
    assets = list_assets(status=args.status)
    if args.format == "text":
        for asset in assets:
            provider = asset.default_provider or "none"
            print(f"{asset.symbol}\t{asset.asset_class}\t{asset.status}\t{asset.market}\t{provider}")
    else:
        print(json.dumps({"assets": [asset.to_dict() for asset in assets]}, ensure_ascii=False))
    return 0


def _import_candles(args) -> int:
    imported_at = _parse_datetime(args.imported_at) if args.imported_at else datetime.now(tz=UTC)
    result = import_market_candles(
        storage_dir=args.storage_dir,
        input_path=args.input,
        symbol=args.symbol,
        source=args.source,
        imported_at=imported_at,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _export_candles(args) -> int:
    result = export_market_candles(
        storage_dir=args.storage_dir,
        output_path=args.output,
        symbol=args.symbol,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _candle_health(args) -> int:
    result = run_candle_health(
        storage_dir=args.storage_dir,
        symbol=args.symbol,
        start=_parse_datetime(args.start),
        end=_parse_datetime(args.end),
        interval_minutes=args.interval_minutes,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "healthy" else 2


def _import_stock_csv(args) -> int:
    imported_at = _parse_datetime(args.imported_at) if args.imported_at else datetime.now(tz=UTC)
    result = import_stock_csv(
        storage_dir=args.storage_dir,
        input_path=args.input,
        symbol=args.symbol,
        source=args.source,
        imported_at=imported_at,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _stock_candle_health(args) -> int:
    result = run_stock_candle_health(
        storage_dir=args.storage_dir,
        symbol=args.symbol,
        start_date=parse_date(args.start_date, label="start-date"),
        end_date=parse_date(args.end_date, label="end-date"),
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "healthy" else 2


def _market_calendar(args) -> int:
    result = market_calendar_payload(
        market=args.market,
        start_date=parse_date(args.start_date, label="start-date"),
        end_date=parse_date(args.end_date, label="end-date"),
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


def _import_macro_events(args) -> int:
    imported_at = _parse_datetime(args.imported_at) if args.imported_at else datetime.now(tz=UTC)
    result = import_macro_events(
        storage_dir=args.storage_dir,
        input_path=args.input,
        source=args.source,
        imported_at=imported_at,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _macro_calendar(args) -> int:
    result = macro_calendar(
        storage_dir=args.storage_dir,
        start=_parse_datetime(args.start),
        end=_parse_datetime(args.end),
        event_type=args.event_type,
        region=args.region,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


def _import_source_documents(args) -> int:
    imported_at = _parse_datetime(args.imported_at) if args.imported_at else datetime.now(tz=UTC)
    result = import_source_documents(
        storage_dir=args.storage_dir,
        input_path=args.input,
        source_id=args.source,
        imported_at=imported_at,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _source_registry(args) -> int:
    result = source_registry_payload(storage_dir=args.storage_dir)
    if args.format == "text":
        for source in result.sources:
            decision_status = "decision" if source.allowed_for_decision else "research-only"
            print(f"{source.source_id}\t{source.source_type}\t{source.provider}\t{decision_status}")
    else:
        print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _build_events(args) -> int:
    created_at = _parse_datetime(args.created_at)
    result = build_event_reliability(
        storage_dir=args.storage_dir,
        created_at=created_at,
        symbol=args.symbol,
        min_reliability_score=args.min_reliability_score,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _build_market_reactions(args) -> int:
    created_at = _parse_datetime(args.created_at)
    result = build_market_reactions(
        storage_dir=args.storage_dir,
        created_at=created_at,
        symbol=args.symbol,
        already_priced_return_threshold=args.already_priced_return_threshold,
        volume_shock_z_threshold=args.volume_shock_z_threshold,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _build_event_edge(args) -> int:
    created_at = _parse_datetime(args.created_at)
    result = build_event_edge_evaluations(
        storage_dir=args.storage_dir,
        created_at=created_at,
        symbol=args.symbol,
        horizon_hours=args.horizon_hours,
        min_sample_size=args.min_sample_size,
        estimated_cost_bps=args.estimated_cost_bps,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _build_research_dataset(args) -> int:
    created_at = _parse_datetime(args.created_at) if args.created_at else datetime.now(tz=UTC)
    result = build_research_dataset(
        storage_dir=args.storage_dir,
        symbol=args.symbol,
        created_at=created_at,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _research_report(args) -> int:
    created_at = _parse_datetime(args.created_at) if args.created_at else datetime.now(tz=UTC)
    result = generate_research_report(
        storage_dir=args.storage_dir,
        symbol=args.symbol,
        created_at=created_at,
        output_dir=args.output_dir,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _backtest(args) -> int:
    created_at = _parse_datetime(args.created_at) if args.created_at else datetime.now(tz=UTC)
    result = run_backtest(
        storage_dir=args.storage_dir,
        symbol=args.symbol,
        start=_parse_datetime(args.start),
        end=_parse_datetime(args.end),
        created_at=created_at,
        initial_cash=args.initial_cash,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
        moving_average_window=args.moving_average_window,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _walk_forward(args) -> int:
    created_at = _parse_datetime(args.created_at) if args.created_at else datetime.now(tz=UTC)
    result = run_walk_forward_validation(
        storage_dir=args.storage_dir,
        symbol=args.symbol,
        start=_parse_datetime(args.start),
        end=_parse_datetime(args.end),
        created_at=created_at,
        train_size=args.train_size,
        validation_size=args.validation_size,
        test_size=args.test_size,
        step_size=args.step_size,
        initial_cash=args.initial_cash,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
        moving_average_window=args.moving_average_window,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _register_strategy_card(args) -> int:
    created_at = _parse_datetime(args.created_at) if args.created_at else datetime.now(tz=UTC)
    repository = JsonFileRepository(args.storage_dir)
    card = register_strategy_card(
        repository=repository,
        created_at=created_at,
        strategy_name=args.name,
        strategy_family=args.family,
        version=args.version,
        status=args.status,
        symbols=[symbol.upper() for symbol in args.symbol],
        hypothesis=args.hypothesis,
        signal_description=args.signal_description,
        entry_rules=args.entry_rule,
        exit_rules=args.exit_rule,
        risk_rules=args.risk_rule,
        parameters=_parse_key_value_list(args.parameter),
        data_requirements=args.data_requirement,
        feature_snapshot_ids=args.feature_snapshot_id,
        backtest_result_ids=args.backtest_result_id,
        walk_forward_validation_ids=args.walk_forward_validation_id,
        event_edge_evaluation_ids=args.event_edge_evaluation_id,
        parent_card_id=args.parent_card_id,
        author=args.author,
    )
    print(json.dumps({"strategy_card": card.to_dict()}, ensure_ascii=False))
    return 0


def _record_experiment_trial(args) -> int:
    created_at = _parse_datetime(args.created_at) if args.created_at else datetime.now(tz=UTC)
    trial = record_experiment_trial(
        repository=JsonFileRepository(args.storage_dir),
        created_at=created_at,
        strategy_card_id=args.strategy_card_id,
        trial_index=args.trial_index,
        status=args.status,
        symbol=args.symbol.upper(),
        max_trials=args.max_trials,
        seed=args.seed,
        dataset_id=args.dataset_id,
        backtest_result_id=args.backtest_result_id,
        walk_forward_validation_id=args.walk_forward_validation_id,
        event_edge_evaluation_id=args.event_edge_evaluation_id,
        prompt_hash=args.prompt_hash,
        code_hash=args.code_hash,
        parameters=_parse_key_value_list(args.parameter),
        metric_summary=_parse_key_value_list(args.metric),
        failure_reason=args.failure_reason,
        started_at=_parse_datetime(args.started_at) if args.started_at else None,
        completed_at=_parse_datetime(args.completed_at) if args.completed_at else None,
    )
    print(json.dumps({"experiment_trial": trial.to_dict()}, ensure_ascii=False))
    return 0


def _lock_evaluation_protocol(args) -> int:
    created_at = _parse_datetime(args.created_at) if args.created_at else datetime.now(tz=UTC)
    split, cost_model = lock_evaluation_protocol(
        repository=JsonFileRepository(args.storage_dir),
        created_at=created_at,
        strategy_card_id=args.strategy_card_id,
        dataset_id=args.dataset_id,
        symbol=args.symbol.upper(),
        train_start=_parse_datetime(args.train_start),
        train_end=_parse_datetime(args.train_end),
        validation_start=_parse_datetime(args.validation_start),
        validation_end=_parse_datetime(args.validation_end),
        holdout_start=_parse_datetime(args.holdout_start),
        holdout_end=_parse_datetime(args.holdout_end),
        embargo_hours=args.embargo_hours,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
        max_turnover=args.max_turnover,
        max_drawdown=args.max_drawdown,
        baseline_suite_version=args.baseline_suite_version,
        locked_by=args.locked_by,
    )
    print(
        json.dumps(
            {
                "split_manifest": split.to_dict(),
                "cost_model_snapshot": cost_model.to_dict(),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _evaluate_leaderboard_gate(args) -> int:
    created_at = _parse_datetime(args.created_at) if args.created_at else datetime.now(tz=UTC)
    result, entry = evaluate_leaderboard_gate(
        repository=JsonFileRepository(args.storage_dir),
        created_at=created_at,
        strategy_card_id=args.strategy_card_id,
        trial_id=args.trial_id,
        split_manifest_id=args.split_manifest_id,
        cost_model_id=args.cost_model_id,
        baseline_id=args.baseline_id,
        backtest_result_id=args.backtest_result_id,
        walk_forward_validation_id=args.walk_forward_validation_id,
        event_edge_evaluation_id=args.event_edge_evaluation_id,
    )
    print(
        json.dumps(
            {
                "locked_evaluation_result": result.to_dict(),
                "leaderboard_entry": entry.to_dict(),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _record_paper_shadow_outcome(args) -> int:
    created_at = _parse_datetime(args.created_at) if args.created_at else datetime.now(tz=UTC)
    storage_dir = Path(args.storage_dir)
    if not storage_dir.exists():
        raise ValueError(f"storage directory does not exist: {storage_dir}")
    if not storage_dir.is_dir():
        raise ValueError(f"storage path is not a directory: {storage_dir}")
    outcome = record_paper_shadow_outcome(
        repository=JsonFileRepository(storage_dir),
        created_at=created_at,
        leaderboard_entry_id=args.leaderboard_entry_id,
        window_start=_parse_datetime(args.window_start),
        window_end=_parse_datetime(args.window_end),
        observed_return=args.observed_return,
        benchmark_return=args.benchmark_return,
        max_adverse_excursion=args.max_adverse_excursion,
        turnover=args.turnover,
        note=args.note,
    )
    print(json.dumps({"paper_shadow_outcome": outcome.to_dict()}, ensure_ascii=False))
    return 0


def _create_research_agenda(args) -> int:
    created_at = _parse_datetime(args.created_at) if args.created_at else datetime.now(tz=UTC)
    agenda = create_research_agenda(
        repository=JsonFileRepository(args.storage_dir),
        created_at=created_at,
        symbol=args.symbol.upper(),
        title=args.title,
        hypothesis=args.hypothesis,
        strategy_family=args.strategy_family,
        strategy_card_ids=args.strategy_card_id,
        priority=args.priority,
    )
    print(json.dumps({"research_agenda": agenda.to_dict()}, ensure_ascii=False))
    return 0


def _record_research_autopilot_run(args) -> int:
    created_at = _parse_datetime(args.created_at) if args.created_at else datetime.now(tz=UTC)
    run = record_research_autopilot_run(
        repository=JsonFileRepository(args.storage_dir),
        created_at=created_at,
        agenda_id=args.agenda_id,
        strategy_card_id=args.strategy_card_id,
        experiment_trial_id=args.experiment_trial_id,
        locked_evaluation_id=args.locked_evaluation_id,
        leaderboard_entry_id=args.leaderboard_entry_id,
        strategy_decision_id=args.strategy_decision_id,
        paper_shadow_outcome_id=args.paper_shadow_outcome_id,
    )
    print(json.dumps({"research_autopilot_run": run.to_dict()}, ensure_ascii=False))
    return 0


def _revision_retest_plan(args) -> int:
    storage_dir = Path(args.storage_dir)
    if not storage_dir.exists():
        raise ValueError(f"storage directory does not exist: {storage_dir}")
    if not storage_dir.is_dir():
        raise ValueError(f"storage path is not a directory: {storage_dir}")
    plan = build_revision_retest_task_plan(
        repository=JsonFileRepository(storage_dir),
        storage_dir=storage_dir,
        symbol=args.symbol.upper(),
        revision_card_id=args.revision_card_id,
    )
    print(json.dumps({"revision_retest_task_plan": plan.to_dict()}, ensure_ascii=False))
    return 0


def _record_revision_retest_task_run(args) -> int:
    storage_dir = Path(args.storage_dir)
    if not storage_dir.exists():
        raise ValueError(f"storage directory does not exist: {storage_dir}")
    if not storage_dir.is_dir():
        raise ValueError(f"storage path is not a directory: {storage_dir}")
    created_at = _parse_datetime(args.now) if args.now else datetime.now(tz=UTC)
    result = record_revision_retest_task_run(
        repository=JsonFileRepository(storage_dir),
        storage_dir=storage_dir,
        symbol=args.symbol.upper(),
        created_at=created_at,
        revision_card_id=args.revision_card_id,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _record_revision_retest_autopilot_run(args) -> int:
    storage_dir = Path(args.storage_dir)
    if not storage_dir.exists():
        raise ValueError(f"storage directory does not exist: {storage_dir}")
    if not storage_dir.is_dir():
        raise ValueError(f"storage path is not a directory: {storage_dir}")
    created_at = _parse_datetime(args.now) if args.now else datetime.now(tz=UTC)
    result = record_revision_retest_autopilot_run(
        repository=JsonFileRepository(storage_dir),
        storage_dir=storage_dir,
        created_at=created_at,
        symbol=args.symbol.upper(),
        revision_card_id=args.revision_card_id,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _execute_revision_retest_next_task(args) -> int:
    storage_dir = Path(args.storage_dir)
    if not storage_dir.exists():
        raise ValueError(f"storage directory does not exist: {storage_dir}")
    if not storage_dir.is_dir():
        raise ValueError(f"storage path is not a directory: {storage_dir}")
    created_at = _parse_datetime(args.now) if args.now else datetime.now(tz=UTC)
    result = execute_revision_retest_next_task(
        repository=JsonFileRepository(storage_dir),
        storage_dir=storage_dir,
        symbol=args.symbol.upper(),
        created_at=created_at,
        revision_card_id=args.revision_card_id,
        shadow_window_start=_parse_datetime(args.shadow_window_start) if args.shadow_window_start else None,
        shadow_window_end=_parse_datetime(args.shadow_window_end) if args.shadow_window_end else None,
        shadow_observed_return=args.shadow_observed_return,
        shadow_benchmark_return=args.shadow_benchmark_return,
        shadow_max_adverse_excursion=args.shadow_max_adverse_excursion,
        shadow_turnover=args.shadow_turnover,
        shadow_note=args.shadow_note,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _propose_strategy_revision(args) -> int:
    created_at = _parse_datetime(args.created_at) if args.created_at else datetime.now(tz=UTC)
    result = propose_strategy_revision(
        repository=JsonFileRepository(args.storage_dir),
        created_at=created_at,
        paper_shadow_outcome_id=args.paper_shadow_outcome_id,
        author=args.author,
        revision_version=args.revision_version,
    )
    print(
        json.dumps(
            {
                "revision_strategy_card": result.strategy_card.to_dict(),
                "revision_research_agenda": result.research_agenda.to_dict(),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _create_revision_retest_scaffold(args) -> int:
    created_at = _parse_datetime(args.created_at) if args.created_at else datetime.now(tz=UTC)
    scaffold = create_revision_retest_scaffold(
        repository=JsonFileRepository(args.storage_dir),
        created_at=created_at,
        revision_card_id=args.revision_card_id,
        symbol=args.symbol.upper(),
        dataset_id=args.dataset_id,
        max_trials=args.max_trials,
        seed=args.seed,
        train_start=_parse_datetime(args.train_start) if args.train_start else None,
        train_end=_parse_datetime(args.train_end) if args.train_end else None,
        validation_start=_parse_datetime(args.validation_start) if args.validation_start else None,
        validation_end=_parse_datetime(args.validation_end) if args.validation_end else None,
        holdout_start=_parse_datetime(args.holdout_start) if args.holdout_start else None,
        holdout_end=_parse_datetime(args.holdout_end) if args.holdout_end else None,
        embargo_hours=args.embargo_hours,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
        max_turnover=args.max_turnover,
        max_drawdown=args.max_drawdown,
        baseline_suite_version=args.baseline_suite_version,
        locked_by=args.locked_by,
    )
    print(json.dumps({"revision_retest_scaffold": scaffold.to_dict()}, ensure_ascii=False))
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


def _parse_key_value_list(items: list[str]) -> dict[str, object]:
    parsed: dict[str, object] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"invalid KEY=VALUE item: {item}")
        key, raw_value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"invalid KEY=VALUE item: {item}")
        parsed[key] = _parse_scalar(raw_value.strip())
    return parsed


def _parse_scalar(value: str) -> object:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"none", "null"}:
        return None
    try:
        if "." not in value:
            return int(value)
        return float(value)
    except ValueError:
        return value


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
