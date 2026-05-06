from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import re

from forecast_loop.models import (
    AutomationRun,
    BaselineEvaluation,
    BacktestResult,
    BacktestRun,
    BrokerOrder,
    BrokerReconciliation,
    CanonicalEvent,
    CostModelSnapshot,
    ExecutionSafetyGate,
    EquityCurvePoint,
    EventEdgeEvaluation,
    EventReliabilityCheck,
    ExperimentBudget,
    ExperimentTrial,
    EvaluationSummary,
    FeatureSnapshot,
    Forecast,
    ForecastScore,
    LeaderboardEntry,
    LockedEvaluationResult,
    HealthCheckResult,
    HealthFinding,
    MarketCandleRecord,
    MarketReactionCheck,
    NotificationArtifact,
    PaperShadowOutcome,
    PaperFill,
    PaperControlEvent,
    PaperOrder,
    PaperPortfolioSnapshot,
    Proposal,
    ProviderRun,
    RepairRequest,
    ResearchAgenda,
    ResearchAutopilotRun,
    ResearchDataset,
    RiskSnapshot,
    Review,
    SourceDocument,
    SourceIngestionRun,
    SourceRegistryEntry,
    StrategyCard,
    StrategyDecision,
    SplitManifest,
    WalkForwardValidation,
)
from forecast_loop.revision_retest import RETEST_PROTOCOL_VERSION
from forecast_loop.storage import JsonFileRepository
from forecast_loop.strategy_evolution import REPLACEMENT_DECISION_BASIS


def run_health_check(
    *,
    storage_dir: Path | str,
    symbol: str,
    now: datetime | None = None,
    stale_after_hours: int = 48,
    create_repair_request: bool = True,
) -> HealthCheckResult:
    now = now or datetime.now(tz=UTC)
    storage_path = Path(storage_dir)
    findings: list[HealthFinding] = []
    if not storage_path.exists():
        findings.append(
            HealthFinding(
                code="missing_storage_dir",
                severity="blocking",
                message=f"Storage directory does not exist: {storage_path}",
                artifact_path=str(storage_path),
                repair_required=True,
            )
        )
        return _finalize_health_result(
            storage_path=storage_path,
            symbol=symbol,
            now=now,
            findings=findings,
            create_repair_request=create_repair_request,
        )

    if not storage_path.is_dir():
        findings.append(
            HealthFinding(
                code="storage_path_not_directory",
                severity="blocking",
                message=f"Storage path exists but is not a directory: {storage_path}",
                artifact_path=str(storage_path),
                repair_required=True,
            )
        )
        return _finalize_health_result(
            storage_path=storage_path,
            symbol=symbol,
            now=now,
            findings=findings,
            create_repair_request=create_repair_request,
        )

    artifact_rows = {
        "forecasts": _load_jsonl(storage_path / "forecasts.jsonl", Forecast.from_dict, findings),
        "source_registry": _load_jsonl(
            storage_path / "source_registry.jsonl",
            SourceRegistryEntry.from_dict,
            findings,
        ),
        "source_documents": _load_jsonl(storage_path / "source_documents.jsonl", SourceDocument.from_dict, findings),
        "source_ingestion_runs": _load_jsonl(
            storage_path / "source_ingestion_runs.jsonl",
            SourceIngestionRun.from_dict,
            findings,
        ),
        "canonical_events": _load_jsonl(storage_path / "canonical_events.jsonl", CanonicalEvent.from_dict, findings),
        "event_reliability_checks": _load_jsonl(
            storage_path / "event_reliability_checks.jsonl",
            EventReliabilityCheck.from_dict,
            findings,
        ),
        "market_reaction_checks": _load_jsonl(
            storage_path / "market_reaction_checks.jsonl",
            MarketReactionCheck.from_dict,
            findings,
        ),
        "event_edge_evaluations": _load_jsonl(
            storage_path / "event_edge_evaluations.jsonl",
            EventEdgeEvaluation.from_dict,
            findings,
        ),
        "feature_snapshots": _load_jsonl(storage_path / "feature_snapshots.jsonl", FeatureSnapshot.from_dict, findings),
        "scores": _load_jsonl(storage_path / "scores.jsonl", ForecastScore.from_dict, findings),
        "reviews": _load_jsonl(storage_path / "reviews.jsonl", Review.from_dict, findings),
        "proposals": _load_jsonl(storage_path / "proposals.jsonl", Proposal.from_dict, findings),
        "decisions": _load_jsonl(storage_path / "strategy_decisions.jsonl", StrategyDecision.from_dict, findings),
        "paper_orders": _load_jsonl(storage_path / "paper_orders.jsonl", PaperOrder.from_dict, findings),
        "broker_orders": _load_jsonl(storage_path / "broker_orders.jsonl", BrokerOrder.from_dict, findings),
        "broker_reconciliations": _load_jsonl(
            storage_path / "broker_reconciliations.jsonl",
            BrokerReconciliation.from_dict,
            findings,
        ),
        "execution_safety_gates": _load_jsonl(
            storage_path / "execution_safety_gates.jsonl",
            ExecutionSafetyGate.from_dict,
            findings,
        ),
        "paper_fills": _load_jsonl(storage_path / "paper_fills.jsonl", PaperFill.from_dict, findings),
        "control_events": _load_jsonl(storage_path / "control_events.jsonl", PaperControlEvent.from_dict, findings),
        "baselines": _load_jsonl(storage_path / "baseline_evaluations.jsonl", BaselineEvaluation.from_dict, findings),
        "portfolios": _load_jsonl(storage_path / "portfolio_snapshots.jsonl", PaperPortfolioSnapshot.from_dict, findings),
        "equity_curve": _load_jsonl(storage_path / "equity_curve.jsonl", EquityCurvePoint.from_dict, findings),
        "risk_snapshots": _load_jsonl(storage_path / "risk_snapshots.jsonl", RiskSnapshot.from_dict, findings),
        "provider_runs": _load_jsonl(storage_path / "provider_runs.jsonl", ProviderRun.from_dict, findings),
        "automation_runs": _load_jsonl(storage_path / "automation_runs.jsonl", AutomationRun.from_dict, findings),
        "notification_artifacts": _load_jsonl(storage_path / "notification_artifacts.jsonl", NotificationArtifact.from_dict, findings),
        "evaluation_summaries": _load_jsonl(storage_path / "evaluation_summaries.jsonl", EvaluationSummary.from_dict, findings),
        "repair_requests": _load_jsonl(storage_path / "repair_requests.jsonl", RepairRequest.from_dict, findings),
        "research_datasets": _load_jsonl(storage_path / "research_datasets.jsonl", ResearchDataset.from_dict, findings),
        "market_candles": _load_jsonl(storage_path / "market_candles.jsonl", MarketCandleRecord.from_dict, findings),
        "backtest_runs": _load_jsonl(storage_path / "backtest_runs.jsonl", BacktestRun.from_dict, findings),
        "backtest_results": _load_jsonl(storage_path / "backtest_results.jsonl", BacktestResult.from_dict, findings),
        "walk_forward_validations": _load_jsonl(
            storage_path / "walk_forward_validations.jsonl",
            WalkForwardValidation.from_dict,
            findings,
        ),
        "strategy_cards": _load_jsonl(storage_path / "strategy_cards.jsonl", StrategyCard.from_dict, findings),
        "experiment_budgets": _load_jsonl(
            storage_path / "experiment_budgets.jsonl",
            ExperimentBudget.from_dict,
            findings,
        ),
        "experiment_trials": _load_jsonl(
            storage_path / "experiment_trials.jsonl",
            ExperimentTrial.from_dict,
            findings,
        ),
        "split_manifests": _load_jsonl(storage_path / "split_manifests.jsonl", SplitManifest.from_dict, findings),
        "cost_model_snapshots": _load_jsonl(
            storage_path / "cost_model_snapshots.jsonl",
            CostModelSnapshot.from_dict,
            findings,
        ),
        "locked_evaluation_results": _load_jsonl(
            storage_path / "locked_evaluation_results.jsonl",
            LockedEvaluationResult.from_dict,
            findings,
        ),
        "leaderboard_entries": _load_jsonl(
            storage_path / "leaderboard_entries.jsonl",
            LeaderboardEntry.from_dict,
            findings,
        ),
        "paper_shadow_outcomes": _load_jsonl(
            storage_path / "paper_shadow_outcomes.jsonl",
            PaperShadowOutcome.from_dict,
            findings,
        ),
        "research_agendas": _load_jsonl(storage_path / "research_agendas.jsonl", ResearchAgenda.from_dict, findings),
        "research_autopilot_runs": _load_jsonl(
            storage_path / "research_autopilot_runs.jsonl",
            ResearchAutopilotRun.from_dict,
            findings,
        ),
    }
    forecasts: list[Forecast] = artifact_rows["forecasts"]
    scores: list[ForecastScore] = artifact_rows["scores"]
    reviews: list[Review] = artifact_rows["reviews"]
    proposals: list[Proposal] = artifact_rows["proposals"]
    decisions: list[StrategyDecision] = artifact_rows["decisions"]
    paper_orders: list[PaperOrder] = artifact_rows["paper_orders"]
    broker_orders: list[BrokerOrder] = artifact_rows["broker_orders"]
    broker_reconciliations: list[BrokerReconciliation] = artifact_rows["broker_reconciliations"]
    execution_safety_gates: list[ExecutionSafetyGate] = artifact_rows["execution_safety_gates"]
    paper_fills: list[PaperFill] = artifact_rows["paper_fills"]
    control_events: list[PaperControlEvent] = artifact_rows["control_events"]
    baselines: list[BaselineEvaluation] = artifact_rows["baselines"]
    portfolios: list[PaperPortfolioSnapshot] = artifact_rows["portfolios"]
    equity_curve: list[EquityCurvePoint] = artifact_rows["equity_curve"]
    risk_snapshots: list[RiskSnapshot] = artifact_rows["risk_snapshots"]
    provider_runs: list[ProviderRun] = artifact_rows["provider_runs"]
    automation_runs: list[AutomationRun] = artifact_rows["automation_runs"]
    notification_artifacts: list[NotificationArtifact] = artifact_rows["notification_artifacts"]
    evaluation_summaries: list[EvaluationSummary] = artifact_rows["evaluation_summaries"]
    repair_requests: list[RepairRequest] = artifact_rows["repair_requests"]
    research_datasets: list[ResearchDataset] = artifact_rows["research_datasets"]
    market_candles: list[MarketCandleRecord] = artifact_rows["market_candles"]
    source_registry_entries: list[SourceRegistryEntry] = artifact_rows["source_registry"]
    source_documents: list[SourceDocument] = artifact_rows["source_documents"]
    source_ingestion_runs: list[SourceIngestionRun] = artifact_rows["source_ingestion_runs"]
    canonical_events: list[CanonicalEvent] = artifact_rows["canonical_events"]
    event_reliability_checks: list[EventReliabilityCheck] = artifact_rows["event_reliability_checks"]
    market_reaction_checks: list[MarketReactionCheck] = artifact_rows["market_reaction_checks"]
    event_edge_evaluations: list[EventEdgeEvaluation] = artifact_rows["event_edge_evaluations"]
    feature_snapshots: list[FeatureSnapshot] = artifact_rows["feature_snapshots"]
    backtest_runs: list[BacktestRun] = artifact_rows["backtest_runs"]
    backtest_results: list[BacktestResult] = artifact_rows["backtest_results"]
    walk_forward_validations: list[WalkForwardValidation] = artifact_rows["walk_forward_validations"]
    strategy_cards: list[StrategyCard] = artifact_rows["strategy_cards"]
    experiment_budgets: list[ExperimentBudget] = artifact_rows["experiment_budgets"]
    experiment_trials: list[ExperimentTrial] = artifact_rows["experiment_trials"]
    split_manifests: list[SplitManifest] = artifact_rows["split_manifests"]
    cost_model_snapshots: list[CostModelSnapshot] = artifact_rows["cost_model_snapshots"]
    locked_evaluation_results: list[LockedEvaluationResult] = artifact_rows["locked_evaluation_results"]
    leaderboard_entries: list[LeaderboardEntry] = artifact_rows["leaderboard_entries"]
    paper_shadow_outcomes: list[PaperShadowOutcome] = artifact_rows["paper_shadow_outcomes"]
    research_agendas: list[ResearchAgenda] = artifact_rows["research_agendas"]
    research_autopilot_runs: list[ResearchAutopilotRun] = artifact_rows["research_autopilot_runs"]

    _check_duplicate_ids(forecasts, "forecast_id", storage_path / "forecasts.jsonl", findings)
    _check_duplicate_ids(scores, "score_id", storage_path / "scores.jsonl", findings)
    _check_duplicate_ids(reviews, "review_id", storage_path / "reviews.jsonl", findings)
    _check_duplicate_ids(proposals, "proposal_id", storage_path / "proposals.jsonl", findings)
    _check_duplicate_ids(decisions, "decision_id", storage_path / "strategy_decisions.jsonl", findings)
    _check_duplicate_ids(paper_orders, "order_id", storage_path / "paper_orders.jsonl", findings)
    _check_duplicate_ids(broker_orders, "broker_order_id", storage_path / "broker_orders.jsonl", findings)
    _check_duplicate_ids(
        broker_reconciliations,
        "reconciliation_id",
        storage_path / "broker_reconciliations.jsonl",
        findings,
    )
    _check_duplicate_ids(execution_safety_gates, "gate_id", storage_path / "execution_safety_gates.jsonl", findings)
    _check_duplicate_ids(paper_fills, "fill_id", storage_path / "paper_fills.jsonl", findings)
    _check_duplicate_ids(control_events, "control_id", storage_path / "control_events.jsonl", findings)
    _check_duplicate_ids(baselines, "baseline_id", storage_path / "baseline_evaluations.jsonl", findings)
    _check_duplicate_ids(portfolios, "snapshot_id", storage_path / "portfolio_snapshots.jsonl", findings)
    _check_duplicate_ids(equity_curve, "point_id", storage_path / "equity_curve.jsonl", findings)
    _check_duplicate_ids(risk_snapshots, "risk_id", storage_path / "risk_snapshots.jsonl", findings)
    _check_duplicate_ids(provider_runs, "provider_run_id", storage_path / "provider_runs.jsonl", findings)
    _check_duplicate_ids(automation_runs, "automation_run_id", storage_path / "automation_runs.jsonl", findings)
    _check_duplicate_ids(notification_artifacts, "notification_id", storage_path / "notification_artifacts.jsonl", findings)
    _check_duplicate_ids(evaluation_summaries, "summary_id", storage_path / "evaluation_summaries.jsonl", findings)
    _check_duplicate_ids(repair_requests, "repair_request_id", storage_path / "repair_requests.jsonl", findings)
    _check_duplicate_ids(research_datasets, "dataset_id", storage_path / "research_datasets.jsonl", findings)
    _check_duplicate_ids(market_candles, "candle_id", storage_path / "market_candles.jsonl", findings)
    _check_duplicate_market_candle_timestamps(market_candles, storage_path / "market_candles.jsonl", findings)
    _check_duplicate_ids(source_registry_entries, "source_id", storage_path / "source_registry.jsonl", findings)
    _check_duplicate_ids(source_documents, "document_id", storage_path / "source_documents.jsonl", findings)
    _check_duplicate_ids(
        source_ingestion_runs,
        "ingestion_run_id",
        storage_path / "source_ingestion_runs.jsonl",
        findings,
    )
    _check_duplicate_ids(canonical_events, "event_id", storage_path / "canonical_events.jsonl", findings)
    _check_duplicate_ids(event_reliability_checks, "check_id", storage_path / "event_reliability_checks.jsonl", findings)
    _check_duplicate_ids(market_reaction_checks, "check_id", storage_path / "market_reaction_checks.jsonl", findings)
    _check_duplicate_ids(
        event_edge_evaluations,
        "evaluation_id",
        storage_path / "event_edge_evaluations.jsonl",
        findings,
    )
    _check_duplicate_ids(feature_snapshots, "feature_snapshot_id", storage_path / "feature_snapshots.jsonl", findings)
    _check_duplicate_ids(backtest_runs, "backtest_id", storage_path / "backtest_runs.jsonl", findings)
    _check_duplicate_ids(backtest_results, "result_id", storage_path / "backtest_results.jsonl", findings)
    _check_duplicate_ids(
        walk_forward_validations,
        "validation_id",
        storage_path / "walk_forward_validations.jsonl",
        findings,
    )
    _check_duplicate_ids(strategy_cards, "card_id", storage_path / "strategy_cards.jsonl", findings)
    _check_duplicate_ids(experiment_budgets, "budget_id", storage_path / "experiment_budgets.jsonl", findings)
    _check_duplicate_ids(experiment_trials, "trial_id", storage_path / "experiment_trials.jsonl", findings)
    _check_duplicate_ids(split_manifests, "manifest_id", storage_path / "split_manifests.jsonl", findings)
    _check_duplicate_ids(
        cost_model_snapshots,
        "cost_model_id",
        storage_path / "cost_model_snapshots.jsonl",
        findings,
    )
    _check_duplicate_ids(
        locked_evaluation_results,
        "evaluation_id",
        storage_path / "locked_evaluation_results.jsonl",
        findings,
    )
    _check_duplicate_ids(leaderboard_entries, "entry_id", storage_path / "leaderboard_entries.jsonl", findings)
    _check_duplicate_ids(
        paper_shadow_outcomes,
        "outcome_id",
        storage_path / "paper_shadow_outcomes.jsonl",
        findings,
    )
    _check_duplicate_ids(research_agendas, "agenda_id", storage_path / "research_agendas.jsonl", findings)
    _check_duplicate_ids(
        research_autopilot_runs,
        "run_id",
        storage_path / "research_autopilot_runs.jsonl",
        findings,
    )

    scoped_forecasts = [forecast for forecast in forecasts if forecast.symbol == symbol]
    latest_forecast = scoped_forecasts[-1] if scoped_forecasts else None
    if latest_forecast is None:
        findings.append(
            HealthFinding(
                code="missing_latest_forecast",
                severity="blocking",
                message=f"No latest forecast exists for {symbol}.",
                artifact_path=str(storage_path / "forecasts.jsonl"),
                repair_required=True,
            )
        )
    elif now - latest_forecast.anchor_time > timedelta(hours=stale_after_hours):
        findings.append(
            HealthFinding(
                code="stale_latest_forecast",
                severity="blocking",
                message=(
                    f"Latest forecast {latest_forecast.forecast_id} is stale: "
                    f"anchor_time={latest_forecast.anchor_time.isoformat()}."
                ),
                artifact_path=str(storage_path / "forecasts.jsonl"),
                repair_required=True,
            )
        )

    _check_last_run_meta(storage_path, symbol, latest_forecast, findings)
    _check_provider_runs(storage_path, symbol, now, provider_runs, findings)
    _check_links(
        storage_path,
        forecasts,
        scores,
        reviews,
        proposals,
        decisions,
        baselines,
        evaluation_summaries,
        research_datasets,
        source_documents,
        source_ingestion_runs,
        canonical_events,
        event_reliability_checks,
        market_reaction_checks,
        event_edge_evaluations,
        feature_snapshots,
        market_candles,
        backtest_runs,
        backtest_results,
        walk_forward_validations,
        strategy_cards,
        experiment_budgets,
        experiment_trials,
        split_manifests,
        cost_model_snapshots,
        locked_evaluation_results,
        leaderboard_entries,
        paper_shadow_outcomes,
        research_agendas,
        research_autopilot_runs,
        findings,
    )
    _check_revision_retest_passed_trial_contexts(
        storage_path=storage_path,
        experiment_trials=experiment_trials,
        backtest_runs=backtest_runs,
        backtest_results=backtest_results,
        walk_forward_validations=walk_forward_validations,
        findings=findings,
    )
    _check_m7_evidence_integrity(
        storage_path,
        source_registry_entries,
        source_documents,
        canonical_events,
        feature_snapshots,
        findings,
    )
    _check_research_dataset_leakage(storage_path, research_datasets, findings)
    _check_broker_reconciliations(storage_path, broker_reconciliations, findings)
    _check_dashboard(storage_path, findings)
    _check_secret_leakage(storage_path, findings)

    return _finalize_health_result(
        storage_path=storage_path,
        symbol=symbol,
        now=now,
        findings=findings,
        create_repair_request=create_repair_request,
    )


def _load_jsonl(path: Path, factory, findings: list[HealthFinding]) -> list:
    if not path.exists():
        return []
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(factory(json.loads(line)))
        except Exception as exc:
            findings.append(
                HealthFinding(
                    code="bad_json_row",
                    severity="blocking",
                    message=f"{path.name}:{line_number} cannot be parsed: {exc}",
                    artifact_path=str(path),
                    repair_required=True,
                )
            )
    return rows


def _check_duplicate_ids(rows: list, attribute: str, path: Path, findings: list[HealthFinding]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for row in rows:
        value = getattr(row, attribute)
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        findings.append(
            HealthFinding(
                code=f"duplicate_{attribute}",
                severity="blocking",
                message=f"{path.name} contains duplicate {attribute}: {', '.join(sorted(duplicates))}.",
                artifact_path=str(path),
                repair_required=True,
            )
        )


def _check_duplicate_market_candle_timestamps(
    candles: list[MarketCandleRecord],
    path: Path,
    findings: list[HealthFinding],
) -> None:
    seen: set[tuple[str, datetime]] = set()
    duplicates: set[tuple[str, datetime]] = set()
    for candle in candles:
        key = (candle.symbol, candle.timestamp.astimezone(UTC))
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    if not duplicates:
        return
    summary = ", ".join(f"{symbol}@{timestamp.isoformat()}" for symbol, timestamp in sorted(duplicates))
    findings.append(
        HealthFinding(
            code="duplicate_candle_timestamp",
            severity="blocking",
            message=f"{path.name} contains duplicate candle timestamp(s): {summary}.",
            artifact_path=str(path),
            repair_required=True,
        )
    )


def _check_broker_reconciliations(
    storage_path: Path,
    reconciliations: list[BrokerReconciliation],
    findings: list[HealthFinding],
) -> None:
    if not reconciliations:
        return
    latest = reconciliations[-1]
    if not latest.repair_required and latest.severity != "blocking":
        return
    findings.append(
        HealthFinding(
            code="broker_reconciliation_blocking",
            severity="blocking",
            message=(
                f"Latest broker reconciliation {latest.reconciliation_id} is blocking; "
                f"finding_count={len(latest.findings)}."
            ),
            artifact_path=str(storage_path / "broker_reconciliations.jsonl"),
            repair_required=True,
        )
    )


_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)['\"]?([A-Z0-9_-]*"
    r"(?:api[_-]?key|api[_-]?secret|secret[_-]?key|token|webhook[_-]?url|private[_-]?key)"
    r"[A-Z0-9_-]*)['\"]?"
    r"[ \t]*[:=][ \t]*['\"]?([^'\"\s,}\r\n]*)"
)
_SAFE_SECRET_PLACEHOLDERS = {
    "",
    "changeme",
    "example",
    "placeholder",
    "none",
    "null",
    "your_api_key",
    "your_api_secret",
    "<redacted>",
    "redacted",
}
_SECRET_SCAN_FILENAMES = {
    "provider_runs.jsonl",
    "repair_requests.jsonl",
    "notification_artifacts.jsonl",
    "last_run_meta.json",
    "storage_repair_report.json",
}


def _check_secret_leakage(storage_path: Path, findings: list[HealthFinding]) -> None:
    scan_paths = [path for path in _repo_secret_scan_paths()]
    scan_paths.extend(storage_path / filename for filename in _SECRET_SCAN_FILENAMES)
    for path in scan_paths:
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if _contains_secret_assignment(text):
            _append_secret_finding(path, "secret-looking value found; remove it or replace with a blank placeholder", findings)


def _repo_secret_scan_paths() -> list[Path]:
    root = Path.cwd()
    paths = [
        root / ".env",
        root / ".env.example",
        root / "config" / "brokers.example.yml",
    ]
    return paths


def _contains_secret_assignment(text: str) -> bool:
    for match in _SECRET_ASSIGNMENT_RE.finditer(text):
        key = match.group(1).strip().strip("'\"").lower()
        value = match.group(2).strip().strip("'\"")
        normalized = value.lower()
        if key.endswith("_env") or key.endswith("-env"):
            continue
        if normalized in _SAFE_SECRET_PLACEHOLDERS:
            continue
        if normalized.startswith("${") or normalized.endswith("_env"):
            continue
        return True
    return False


def _append_secret_finding(path: Path, message: str, findings: list[HealthFinding]) -> None:
    findings.append(
        HealthFinding(
            code="secret_leak_detected",
            severity="blocking",
            message=f"{path.name}: {message}.",
            artifact_path=str(path),
            repair_required=True,
        )
    )


def _check_last_run_meta(
    storage_path: Path,
    symbol: str,
    latest_forecast: Forecast | None,
    findings: list[HealthFinding],
) -> None:
    meta_path = storage_path / "last_run_meta.json"
    if not meta_path.exists() or latest_forecast is None:
        return
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:
        findings.append(
            HealthFinding(
                code="bad_last_run_meta",
                severity="blocking",
                message=f"last_run_meta.json cannot be parsed: {exc}",
                artifact_path=str(meta_path),
                repair_required=True,
            )
        )
        return
    meta_forecast = payload.get("new_forecast") or {}
    meta_symbol = payload.get("symbol") or meta_forecast.get("symbol")
    if meta_symbol and meta_symbol != symbol:
        return
    meta_forecast_id = meta_forecast.get("forecast_id")
    if meta_forecast_id and meta_forecast_id != latest_forecast.forecast_id:
        findings.append(
            HealthFinding(
                code="last_run_meta_mismatch",
                severity="blocking",
                message=(
                    "last_run_meta.json.new_forecast.forecast_id does not match latest forecast tail: "
                    f"{meta_forecast_id} != {latest_forecast.forecast_id}."
                ),
                artifact_path=str(meta_path),
                repair_required=True,
            )
        )


def _check_provider_runs(
    storage_path: Path,
    symbol: str,
    now: datetime,
    provider_runs: list[ProviderRun],
    findings: list[HealthFinding],
    stale_after_hours: int = 24,
) -> None:
    scoped_runs = [run for run in provider_runs if run.symbol == symbol]
    if not scoped_runs:
        return
    latest_run = scoped_runs[-1]
    if latest_run.status == "error":
        findings.append(
            HealthFinding(
                code="provider_failure",
                severity="blocking",
                message=f"Latest provider run failed: {latest_run.error_type}: {latest_run.error_message}",
                artifact_path=str(storage_path / "provider_runs.jsonl"),
                repair_required=True,
            )
        )
    elif latest_run.status == "empty":
        findings.append(
            HealthFinding(
                code="provider_empty_data",
                severity="blocking",
                message=f"Latest provider run returned no data for {symbol}.",
                artifact_path=str(storage_path / "provider_runs.jsonl"),
                repair_required=True,
            )
        )
    if latest_run.schema_version != "market_candles_v1":
        findings.append(
            HealthFinding(
                code="provider_schema_drift",
                severity="blocking",
                message=f"Unexpected provider schema version: {latest_run.schema_version}.",
                artifact_path=str(storage_path / "provider_runs.jsonl"),
                repair_required=True,
            )
        )
    if now - latest_run.completed_at > timedelta(hours=stale_after_hours):
        findings.append(
            HealthFinding(
                code="provider_stale",
                severity="warning",
                message=f"Latest provider run is stale: completed_at={latest_run.completed_at.isoformat()}.",
                artifact_path=str(storage_path / "provider_runs.jsonl"),
                repair_required=False,
            )
        )


def _check_links(
    storage_path: Path,
    forecasts: list[Forecast],
    scores: list[ForecastScore],
    reviews: list[Review],
    proposals: list[Proposal],
    decisions: list[StrategyDecision],
    baselines: list[BaselineEvaluation],
    evaluation_summaries: list[EvaluationSummary],
    research_datasets: list[ResearchDataset],
    source_documents: list[SourceDocument],
    source_ingestion_runs: list[SourceIngestionRun],
    canonical_events: list[CanonicalEvent],
    event_reliability_checks: list[EventReliabilityCheck],
    market_reaction_checks: list[MarketReactionCheck],
    event_edge_evaluations: list[EventEdgeEvaluation],
    feature_snapshots: list[FeatureSnapshot],
    market_candles: list[MarketCandleRecord],
    backtest_runs: list[BacktestRun],
    backtest_results: list[BacktestResult],
    walk_forward_validations: list[WalkForwardValidation],
    strategy_cards: list[StrategyCard],
    experiment_budgets: list[ExperimentBudget],
    experiment_trials: list[ExperimentTrial],
    split_manifests: list[SplitManifest],
    cost_model_snapshots: list[CostModelSnapshot],
    locked_evaluation_results: list[LockedEvaluationResult],
    leaderboard_entries: list[LeaderboardEntry],
    paper_shadow_outcomes: list[PaperShadowOutcome],
    research_agendas: list[ResearchAgenda],
    research_autopilot_runs: list[ResearchAutopilotRun],
    findings: list[HealthFinding],
) -> None:
    forecast_ids = {forecast.forecast_id for forecast in forecasts}
    score_ids = {score.score_id for score in scores}
    review_ids = {review.review_id for review in reviews}
    proposal_ids = {proposal.proposal_id for proposal in proposals}
    baseline_ids = {baseline.baseline_id for baseline in baselines}
    source_document_ids = {document.document_id for document in source_documents}
    canonical_event_ids = {event.event_id for event in canonical_events}
    market_reaction_check_ids = {check.check_id for check in market_reaction_checks}
    candle_ids = {candle.candle_id for candle in market_candles}
    backtest_run_ids = {run.backtest_id for run in backtest_runs}
    backtest_result_ids = {result.result_id for result in backtest_results}
    event_edge_evaluation_ids = {evaluation.evaluation_id for evaluation in event_edge_evaluations}
    strategy_card_ids = {card.card_id for card in strategy_cards}
    strategy_card_by_id = {card.card_id: card for card in strategy_cards}
    walk_forward_validation_ids = {validation.validation_id for validation in walk_forward_validations}
    trial_ids = {trial.trial_id for trial in experiment_trials}
    split_manifest_ids = {manifest.manifest_id for manifest in split_manifests}
    cost_model_ids = {snapshot.cost_model_id for snapshot in cost_model_snapshots}
    locked_evaluation_ids = {result.evaluation_id for result in locked_evaluation_results}
    locked_evaluation_by_id = {result.evaluation_id: result for result in locked_evaluation_results}
    decision_ids = {decision.decision_id for decision in decisions}
    decision_by_id = {decision.decision_id: decision for decision in decisions}
    paper_shadow_outcome_ids = {outcome.outcome_id for outcome in paper_shadow_outcomes}
    research_agenda_ids = {agenda.agenda_id for agenda in research_agendas}
    research_agenda_by_id = {agenda.agenda_id: agenda for agenda in research_agendas}

    for score in scores:
        if score.forecast_id not in forecast_ids:
            _add_link_finding("score_missing_forecast", storage_path / "scores.jsonl", score.score_id, score.forecast_id, findings)

    for review in reviews:
        missing_scores = [score_id for score_id in review.score_ids if score_id not in score_ids]
        if missing_scores:
            _add_link_finding("review_missing_score", storage_path / "reviews.jsonl", review.review_id, ", ".join(missing_scores), findings)

    for proposal in proposals:
        if proposal.review_id not in review_ids:
            _add_link_finding("proposal_missing_review", storage_path / "proposals.jsonl", proposal.proposal_id, proposal.review_id, findings)
        missing_scores = [score_id for score_id in proposal.score_ids if score_id not in score_ids]
        if missing_scores:
            _add_link_finding("proposal_missing_score", storage_path / "proposals.jsonl", proposal.proposal_id, ", ".join(missing_scores), findings)

    for baseline in baselines:
        missing_forecasts = [forecast_id for forecast_id in baseline.forecast_ids if forecast_id not in forecast_ids]
        missing_scores = [score_id for score_id in baseline.score_ids if score_id not in score_ids]
        if missing_forecasts:
            _add_link_finding(
                "baseline_missing_forecast",
                storage_path / "baseline_evaluations.jsonl",
                baseline.baseline_id,
                ", ".join(missing_forecasts),
                findings,
            )
        if missing_scores:
            _add_link_finding(
                "baseline_missing_score",
                storage_path / "baseline_evaluations.jsonl",
                baseline.baseline_id,
                ", ".join(missing_scores),
                findings,
            )

    for decision in decisions:
        missing_forecasts = [forecast_id for forecast_id in decision.forecast_ids if forecast_id not in forecast_ids]
        missing_scores = [score_id for score_id in decision.score_ids if score_id not in score_ids]
        missing_reviews = [review_id for review_id in decision.review_ids if review_id not in review_ids]
        missing_baselines = [baseline_id for baseline_id in decision.baseline_ids if baseline_id not in baseline_ids]
        if missing_forecasts:
            _add_link_finding("decision_missing_forecast", storage_path / "strategy_decisions.jsonl", decision.decision_id, ", ".join(missing_forecasts), findings)
        if missing_scores:
            _add_link_finding("decision_missing_score", storage_path / "strategy_decisions.jsonl", decision.decision_id, ", ".join(missing_scores), findings)
        if missing_reviews:
            _add_link_finding("decision_missing_review", storage_path / "strategy_decisions.jsonl", decision.decision_id, ", ".join(missing_reviews), findings)
        if missing_baselines:
            _add_link_finding("decision_missing_baseline", storage_path / "strategy_decisions.jsonl", decision.decision_id, ", ".join(missing_baselines), findings)

    for summary in evaluation_summaries:
        if summary.replay_window_start is not None or summary.replay_window_end is not None:
            continue
        missing_forecasts = [
            forecast_id
            for forecast_id in [*summary.forecast_ids, *summary.scored_forecast_ids]
            if forecast_id not in forecast_ids
        ]
        missing_scores = [score_id for score_id in summary.score_ids if score_id not in score_ids]
        missing_reviews = [review_id for review_id in summary.review_ids if review_id not in review_ids]
        missing_proposals = [proposal_id for proposal_id in summary.proposal_ids if proposal_id not in proposal_ids]
        if missing_forecasts:
            _add_link_finding(
                "evaluation_summary_missing_forecast",
                storage_path / "evaluation_summaries.jsonl",
                summary.summary_id,
                ", ".join(sorted(set(missing_forecasts))),
                findings,
            )
        if missing_scores:
            _add_link_finding(
                "evaluation_summary_missing_score",
                storage_path / "evaluation_summaries.jsonl",
                summary.summary_id,
                ", ".join(missing_scores),
                findings,
            )
        if missing_reviews:
            _add_link_finding(
                "evaluation_summary_missing_review",
                storage_path / "evaluation_summaries.jsonl",
                summary.summary_id,
                ", ".join(missing_reviews),
                findings,
            )
        if missing_proposals:
            _add_link_finding(
                "evaluation_summary_missing_proposal",
                storage_path / "evaluation_summaries.jsonl",
                summary.summary_id,
                ", ".join(missing_proposals),
                findings,
            )

    for dataset in research_datasets:
        missing_forecasts = [forecast_id for forecast_id in dataset.forecast_ids if forecast_id not in forecast_ids]
        missing_scores = [score_id for score_id in dataset.score_ids if score_id not in score_ids]
        row_forecast_ids = [row.forecast_id for row in dataset.rows]
        row_score_ids = [row.score_id for row in dataset.rows]
        missing_row_forecasts = [forecast_id for forecast_id in row_forecast_ids if forecast_id not in forecast_ids]
        missing_row_scores = [score_id for score_id in row_score_ids if score_id not in score_ids]
        if missing_forecasts or missing_row_forecasts:
            _add_link_finding(
                "research_dataset_missing_forecast",
                storage_path / "research_datasets.jsonl",
                dataset.dataset_id,
                ", ".join(sorted(set([*missing_forecasts, *missing_row_forecasts]))),
                findings,
            )
        if missing_scores or missing_row_scores:
            _add_link_finding(
                "research_dataset_missing_score",
                storage_path / "research_datasets.jsonl",
                dataset.dataset_id,
                ", ".join(sorted(set([*missing_scores, *missing_row_scores]))),
                findings,
            )

    for run in source_ingestion_runs:
        missing_documents = [document_id for document_id in run.document_ids if document_id not in source_document_ids]
        if missing_documents:
            _add_link_finding(
                "source_ingestion_run_missing_document",
                storage_path / "source_ingestion_runs.jsonl",
                run.ingestion_run_id,
                ", ".join(missing_documents),
                findings,
            )

    for event in canonical_events:
        missing_documents = [
            document_id for document_id in event.source_document_ids if document_id not in source_document_ids
        ]
        if missing_documents:
            _add_link_finding(
                "canonical_event_missing_source_document",
                storage_path / "canonical_events.jsonl",
                event.event_id,
                ", ".join(missing_documents),
                findings,
            )
        if event.primary_document_id and event.primary_document_id not in source_document_ids:
            _add_link_finding(
                "canonical_event_missing_primary_document",
                storage_path / "canonical_events.jsonl",
                event.event_id,
                event.primary_document_id,
                findings,
            )

    for check in event_reliability_checks:
        if check.event_id not in canonical_event_ids:
            _add_link_finding(
                "event_reliability_missing_event",
                storage_path / "event_reliability_checks.jsonl",
                check.check_id,
                check.event_id,
                findings,
            )

    for check in market_reaction_checks:
        if check.event_id not in canonical_event_ids:
            _add_link_finding(
                "market_reaction_missing_event",
                storage_path / "market_reaction_checks.jsonl",
                check.check_id,
                check.event_id,
                findings,
            )

    for evaluation in event_edge_evaluations:
        missing_events = [event_id for event_id in evaluation.input_event_ids if event_id not in canonical_event_ids]
        missing_reactions = [
            check_id for check_id in evaluation.input_reaction_check_ids if check_id not in market_reaction_check_ids
        ]
        missing_candles = [candle_id for candle_id in evaluation.input_candle_ids if candle_id not in candle_ids]
        if missing_events:
            _add_link_finding(
                "event_edge_missing_event",
                storage_path / "event_edge_evaluations.jsonl",
                evaluation.evaluation_id,
                ", ".join(missing_events),
                findings,
            )
        if missing_reactions:
            _add_link_finding(
                "event_edge_missing_market_reaction",
                storage_path / "event_edge_evaluations.jsonl",
                evaluation.evaluation_id,
                ", ".join(missing_reactions),
                findings,
            )
        if missing_candles:
            _add_link_finding(
                "event_edge_missing_candle",
                storage_path / "event_edge_evaluations.jsonl",
                evaluation.evaluation_id,
                ", ".join(missing_candles),
                findings,
            )

    for snapshot in feature_snapshots:
        missing_documents = [
            document_id for document_id in snapshot.source_document_ids if document_id not in source_document_ids
        ]
        missing_events = [event_id for event_id in snapshot.event_ids if event_id not in canonical_event_ids]
        if missing_documents:
            _add_link_finding(
                "feature_snapshot_missing_source_document",
                storage_path / "feature_snapshots.jsonl",
                snapshot.feature_snapshot_id,
                ", ".join(missing_documents),
                findings,
            )
        if missing_events:
            _add_link_finding(
                "feature_snapshot_missing_event",
                storage_path / "feature_snapshots.jsonl",
                snapshot.feature_snapshot_id,
                ", ".join(missing_events),
                findings,
            )

    for result in backtest_results:
        if result.backtest_id not in backtest_run_ids:
            _add_link_finding(
                "backtest_result_missing_run",
                storage_path / "backtest_results.jsonl",
                result.result_id,
                result.backtest_id,
                findings,
            )

    for run in backtest_runs:
        missing_candles = [candle_id for candle_id in run.candle_ids if candle_id not in candle_ids]
        if missing_candles:
            _add_link_finding(
                "backtest_run_missing_candle",
                storage_path / "backtest_runs.jsonl",
                run.backtest_id,
                ", ".join(missing_candles),
                findings,
            )

    for validation in walk_forward_validations:
        nested_result_ids = [
            result_id
            for window in validation.windows
            for result_id in [window.validation_backtest_result_id, window.test_backtest_result_id]
        ]
        missing_results = [
            result_id
            for result_id in [*validation.backtest_result_ids, *nested_result_ids]
            if result_id not in backtest_result_ids
        ]
        if missing_results:
            _add_link_finding(
                "walk_forward_missing_backtest_result",
                storage_path / "walk_forward_validations.jsonl",
                validation.validation_id,
                ", ".join(sorted(set(missing_results))),
                findings,
            )

    for card in strategy_cards:
        if card.parent_card_id and card.parent_card_id not in strategy_card_ids:
            _add_link_finding(
                "strategy_card_missing_parent",
                storage_path / "strategy_cards.jsonl",
                card.card_id,
                card.parent_card_id,
                findings,
            )
        missing_features = [
            feature_snapshot_id
            for feature_snapshot_id in card.feature_snapshot_ids
            if feature_snapshot_id not in {snapshot.feature_snapshot_id for snapshot in feature_snapshots}
        ]
        missing_backtests = [result_id for result_id in card.backtest_result_ids if result_id not in backtest_result_ids]
        missing_walk_forward = [
            validation_id
            for validation_id in card.walk_forward_validation_ids
            if validation_id not in walk_forward_validation_ids
        ]
        missing_event_edges = [
            evaluation_id
            for evaluation_id in card.event_edge_evaluation_ids
            if evaluation_id not in event_edge_evaluation_ids
        ]
        if missing_features:
            _add_link_finding(
                "strategy_card_missing_feature_snapshot",
                storage_path / "strategy_cards.jsonl",
                card.card_id,
                ", ".join(missing_features),
                findings,
            )
        if missing_backtests:
            _add_link_finding(
                "strategy_card_missing_backtest_result",
                storage_path / "strategy_cards.jsonl",
                card.card_id,
                ", ".join(missing_backtests),
                findings,
            )
        if missing_walk_forward:
            _add_link_finding(
                "strategy_card_missing_walk_forward_validation",
                storage_path / "strategy_cards.jsonl",
                card.card_id,
                ", ".join(missing_walk_forward),
                findings,
            )
        if missing_event_edges:
            _add_link_finding(
                "strategy_card_missing_event_edge_evaluation",
                storage_path / "strategy_cards.jsonl",
                card.card_id,
                ", ".join(missing_event_edges),
                findings,
            )

    for budget in experiment_budgets:
        if budget.strategy_card_id not in strategy_card_ids:
            _add_link_finding(
                "experiment_budget_missing_strategy_card",
                storage_path / "experiment_budgets.jsonl",
                budget.budget_id,
                budget.strategy_card_id,
                findings,
            )

    for trial in experiment_trials:
        if trial.strategy_card_id not in strategy_card_ids:
            _add_link_finding(
                "experiment_trial_missing_strategy_card",
                storage_path / "experiment_trials.jsonl",
                trial.trial_id,
                trial.strategy_card_id,
                findings,
            )
        if trial.dataset_id and trial.dataset_id not in {dataset.dataset_id for dataset in research_datasets}:
            _add_link_finding(
                "experiment_trial_missing_research_dataset",
                storage_path / "experiment_trials.jsonl",
                trial.trial_id,
                trial.dataset_id,
                findings,
            )
        if trial.backtest_result_id and trial.backtest_result_id not in backtest_result_ids:
            _add_link_finding(
                "experiment_trial_missing_backtest_result",
                storage_path / "experiment_trials.jsonl",
                trial.trial_id,
                trial.backtest_result_id,
                findings,
            )
        if trial.walk_forward_validation_id and trial.walk_forward_validation_id not in walk_forward_validation_ids:
            _add_link_finding(
                "experiment_trial_missing_walk_forward_validation",
                storage_path / "experiment_trials.jsonl",
                trial.trial_id,
                trial.walk_forward_validation_id,
                findings,
            )
        if trial.event_edge_evaluation_id and trial.event_edge_evaluation_id not in event_edge_evaluation_ids:
            _add_link_finding(
                "experiment_trial_missing_event_edge_evaluation",
                storage_path / "experiment_trials.jsonl",
                trial.trial_id,
                trial.event_edge_evaluation_id,
                findings,
            )

    for split in split_manifests:
        if split.strategy_card_id not in strategy_card_ids:
            _add_link_finding(
                "split_manifest_missing_strategy_card",
                storage_path / "split_manifests.jsonl",
                split.manifest_id,
                split.strategy_card_id,
                findings,
            )
        if split.dataset_id not in {dataset.dataset_id for dataset in research_datasets}:
            _add_link_finding(
                "split_manifest_missing_research_dataset",
                storage_path / "split_manifests.jsonl",
                split.manifest_id,
                split.dataset_id,
                findings,
            )

    for result in locked_evaluation_results:
        if result.strategy_card_id not in strategy_card_ids:
            _add_link_finding(
                "locked_evaluation_missing_strategy_card",
                storage_path / "locked_evaluation_results.jsonl",
                result.evaluation_id,
                result.strategy_card_id,
                findings,
            )
        if result.trial_id not in trial_ids:
            _add_link_finding(
                "locked_evaluation_missing_trial",
                storage_path / "locked_evaluation_results.jsonl",
                result.evaluation_id,
                result.trial_id,
                findings,
            )
        if result.split_manifest_id not in split_manifest_ids:
            _add_link_finding(
                "locked_evaluation_missing_split_manifest",
                storage_path / "locked_evaluation_results.jsonl",
                result.evaluation_id,
                result.split_manifest_id,
                findings,
            )
        if result.cost_model_id not in cost_model_ids:
            _add_link_finding(
                "locked_evaluation_missing_cost_model",
                storage_path / "locked_evaluation_results.jsonl",
                result.evaluation_id,
                result.cost_model_id,
                findings,
            )
        if result.baseline_id not in baseline_ids:
            _add_link_finding(
                "locked_evaluation_missing_baseline",
                storage_path / "locked_evaluation_results.jsonl",
                result.evaluation_id,
                result.baseline_id,
                findings,
            )
        if result.backtest_result_id not in backtest_result_ids:
            _add_link_finding(
                "locked_evaluation_missing_backtest_result",
                storage_path / "locked_evaluation_results.jsonl",
                result.evaluation_id,
                result.backtest_result_id,
                findings,
            )
        if result.walk_forward_validation_id not in walk_forward_validation_ids:
            _add_link_finding(
                "locked_evaluation_missing_walk_forward_validation",
                storage_path / "locked_evaluation_results.jsonl",
                result.evaluation_id,
                result.walk_forward_validation_id,
                findings,
            )
        if result.event_edge_evaluation_id and result.event_edge_evaluation_id not in event_edge_evaluation_ids:
            _add_link_finding(
                "locked_evaluation_missing_event_edge_evaluation",
                storage_path / "locked_evaluation_results.jsonl",
                result.evaluation_id,
                result.event_edge_evaluation_id,
                findings,
            )

    for entry in leaderboard_entries:
        if entry.strategy_card_id not in strategy_card_ids:
            _add_link_finding(
                "leaderboard_entry_missing_strategy_card",
                storage_path / "leaderboard_entries.jsonl",
                entry.entry_id,
                entry.strategy_card_id,
                findings,
            )
        if entry.evaluation_id not in locked_evaluation_ids:
            _add_link_finding(
                "leaderboard_entry_missing_locked_evaluation",
                storage_path / "leaderboard_entries.jsonl",
                entry.entry_id,
                entry.evaluation_id,
                findings,
            )
        if entry.trial_id not in trial_ids:
            _add_link_finding(
                "leaderboard_entry_missing_trial",
                storage_path / "leaderboard_entries.jsonl",
                entry.entry_id,
                entry.trial_id,
                findings,
            )

    leaderboard_by_id = {entry.entry_id: entry for entry in leaderboard_entries}
    for outcome in paper_shadow_outcomes:
        entry = leaderboard_by_id.get(outcome.leaderboard_entry_id)
        if entry is None:
            _add_link_finding(
                "paper_shadow_outcome_missing_leaderboard_entry",
                storage_path / "paper_shadow_outcomes.jsonl",
                outcome.outcome_id,
                outcome.leaderboard_entry_id,
                findings,
            )
        elif outcome.symbol != entry.symbol:
            _add_link_finding(
                "paper_shadow_outcome_symbol_mismatch",
                storage_path / "paper_shadow_outcomes.jsonl",
                outcome.outcome_id,
                entry.symbol,
                findings,
            )
        else:
            if outcome.evaluation_id != entry.evaluation_id:
                _add_link_finding(
                    "paper_shadow_outcome_leaderboard_evaluation_mismatch",
                    storage_path / "paper_shadow_outcomes.jsonl",
                    outcome.outcome_id,
                    entry.evaluation_id,
                    findings,
                )
            if outcome.strategy_card_id != entry.strategy_card_id:
                _add_link_finding(
                    "paper_shadow_outcome_leaderboard_strategy_card_mismatch",
                    storage_path / "paper_shadow_outcomes.jsonl",
                    outcome.outcome_id,
                    entry.strategy_card_id,
                    findings,
                )
            if outcome.trial_id != entry.trial_id:
                _add_link_finding(
                    "paper_shadow_outcome_leaderboard_trial_mismatch",
                    storage_path / "paper_shadow_outcomes.jsonl",
                    outcome.outcome_id,
                    entry.trial_id,
                    findings,
                )
        if outcome.evaluation_id not in locked_evaluation_ids:
            _add_link_finding(
                "paper_shadow_outcome_missing_locked_evaluation",
                storage_path / "paper_shadow_outcomes.jsonl",
                outcome.outcome_id,
                outcome.evaluation_id,
                findings,
            )
        else:
            evaluation = locked_evaluation_by_id[outcome.evaluation_id]
            if outcome.strategy_card_id != evaluation.strategy_card_id:
                _add_link_finding(
                    "paper_shadow_outcome_evaluation_strategy_card_mismatch",
                    storage_path / "paper_shadow_outcomes.jsonl",
                    outcome.outcome_id,
                    evaluation.strategy_card_id,
                    findings,
                )
            if outcome.trial_id != evaluation.trial_id:
                _add_link_finding(
                    "paper_shadow_outcome_evaluation_trial_mismatch",
                    storage_path / "paper_shadow_outcomes.jsonl",
                    outcome.outcome_id,
                    evaluation.trial_id,
                    findings,
                )
        if outcome.strategy_card_id not in strategy_card_ids:
            _add_link_finding(
                "paper_shadow_outcome_missing_strategy_card",
                storage_path / "paper_shadow_outcomes.jsonl",
                outcome.outcome_id,
                outcome.strategy_card_id,
                findings,
            )
        if outcome.trial_id not in trial_ids:
            _add_link_finding(
                "paper_shadow_outcome_missing_experiment_trial",
                storage_path / "paper_shadow_outcomes.jsonl",
                outcome.outcome_id,
                outcome.trial_id,
                findings,
            )

    for agenda in research_agendas:
        missing_cards = [card_id for card_id in agenda.strategy_card_ids if card_id not in strategy_card_ids]
        if missing_cards:
            _add_link_finding(
                "research_agenda_missing_strategy_card",
                storage_path / "research_agendas.jsonl",
                agenda.agenda_id,
                ", ".join(missing_cards),
                findings,
            )

    leaderboard_entry_ids = set(leaderboard_by_id)
    trial_by_id = {trial.trial_id: trial for trial in experiment_trials}
    for run in research_autopilot_runs:
        if run.agenda_id not in research_agenda_ids:
            _add_link_finding(
                "research_autopilot_run_missing_agenda",
                storage_path / "research_autopilot_runs.jsonl",
                run.run_id,
                run.agenda_id,
                findings,
            )
        else:
            agenda = research_agenda_by_id[run.agenda_id]
            if not _research_run_strategy_card_matches_agenda(run.strategy_card_id, agenda, strategy_card_by_id):
                _add_link_finding(
                    "research_autopilot_run_agenda_strategy_card_mismatch",
                    storage_path / "research_autopilot_runs.jsonl",
                    run.run_id,
                    run.strategy_card_id,
                    findings,
                )
        if run.strategy_card_id not in strategy_card_ids:
            _add_link_finding(
                "research_autopilot_run_missing_strategy_card",
                storage_path / "research_autopilot_runs.jsonl",
                run.run_id,
                run.strategy_card_id,
                findings,
            )
        if run.experiment_trial_id not in trial_ids:
            _add_link_finding(
                "research_autopilot_run_missing_experiment_trial",
                storage_path / "research_autopilot_runs.jsonl",
                run.run_id,
                run.experiment_trial_id,
                findings,
            )
        else:
            trial = trial_by_id[run.experiment_trial_id]
            if trial.strategy_card_id != run.strategy_card_id:
                _add_link_finding(
                    "research_autopilot_run_trial_strategy_card_mismatch",
                    storage_path / "research_autopilot_runs.jsonl",
                    run.run_id,
                    trial.strategy_card_id,
                    findings,
                )
        if run.locked_evaluation_id not in locked_evaluation_ids:
            _add_link_finding(
                "research_autopilot_run_missing_locked_evaluation",
                storage_path / "research_autopilot_runs.jsonl",
                run.run_id,
                run.locked_evaluation_id,
                findings,
            )
        else:
            evaluation = locked_evaluation_by_id[run.locked_evaluation_id]
            if evaluation.strategy_card_id != run.strategy_card_id:
                _add_link_finding(
                    "research_autopilot_run_locked_evaluation_strategy_card_mismatch",
                    storage_path / "research_autopilot_runs.jsonl",
                    run.run_id,
                    evaluation.strategy_card_id,
                    findings,
                )
            if evaluation.trial_id != run.experiment_trial_id:
                _add_link_finding(
                    "research_autopilot_run_locked_evaluation_trial_mismatch",
                    storage_path / "research_autopilot_runs.jsonl",
                    run.run_id,
                    evaluation.trial_id,
                    findings,
                )
        if run.leaderboard_entry_id not in leaderboard_entry_ids:
            _add_link_finding(
                "research_autopilot_run_missing_leaderboard_entry",
                storage_path / "research_autopilot_runs.jsonl",
                run.run_id,
                run.leaderboard_entry_id,
                findings,
            )
        else:
            entry = leaderboard_by_id[run.leaderboard_entry_id]
            if entry.strategy_card_id != run.strategy_card_id:
                _add_link_finding(
                    "research_autopilot_run_leaderboard_strategy_card_mismatch",
                    storage_path / "research_autopilot_runs.jsonl",
                    run.run_id,
                    entry.strategy_card_id,
                    findings,
                )
            if entry.trial_id != run.experiment_trial_id:
                _add_link_finding(
                    "research_autopilot_run_leaderboard_trial_mismatch",
                    storage_path / "research_autopilot_runs.jsonl",
                    run.run_id,
                    entry.trial_id,
                    findings,
                )
            if entry.evaluation_id != run.locked_evaluation_id:
                _add_link_finding(
                    "research_autopilot_run_leaderboard_evaluation_mismatch",
                    storage_path / "research_autopilot_runs.jsonl",
                    run.run_id,
                    entry.evaluation_id,
                    findings,
                )
        if run.strategy_decision_id and run.strategy_decision_id not in decision_ids:
            _add_link_finding(
                "research_autopilot_run_missing_strategy_decision",
                storage_path / "research_autopilot_runs.jsonl",
                run.run_id,
                run.strategy_decision_id,
                findings,
            )
        elif run.strategy_decision_id:
            decision = decision_by_id[run.strategy_decision_id]
            entry = leaderboard_by_id.get(run.leaderboard_entry_id)
            if entry is not None and decision.symbol != entry.symbol:
                _add_link_finding(
                    "research_autopilot_run_strategy_decision_symbol_mismatch",
                    storage_path / "research_autopilot_runs.jsonl",
                    run.run_id,
                    decision.symbol,
                    findings,
                )
            if not decision.tradeable:
                _add_link_finding(
                    "research_autopilot_run_strategy_decision_not_tradeable",
                    storage_path / "research_autopilot_runs.jsonl",
                    run.run_id,
                    decision.decision_id,
                    findings,
                )
            if decision.action in {"STOP_NEW_ENTRIES", "REDUCE_RISK"}:
                _add_link_finding(
                    "research_autopilot_run_strategy_decision_fail_closed",
                    storage_path / "research_autopilot_runs.jsonl",
                    run.run_id,
                    decision.action,
                    findings,
                )
            if decision.blocked_reason:
                _add_link_finding(
                    "research_autopilot_run_strategy_decision_blocked",
                    storage_path / "research_autopilot_runs.jsonl",
                    run.run_id,
                    decision.blocked_reason,
                    findings,
                )
        if run.paper_shadow_outcome_id and run.paper_shadow_outcome_id not in paper_shadow_outcome_ids:
            _add_link_finding(
                "research_autopilot_run_missing_paper_shadow_outcome",
                storage_path / "research_autopilot_runs.jsonl",
                run.run_id,
                run.paper_shadow_outcome_id,
                findings,
            )
        elif run.paper_shadow_outcome_id:
            outcome = next(outcome for outcome in paper_shadow_outcomes if outcome.outcome_id == run.paper_shadow_outcome_id)
            if outcome.leaderboard_entry_id != run.leaderboard_entry_id:
                _add_link_finding(
                    "research_autopilot_run_shadow_leaderboard_mismatch",
                    storage_path / "research_autopilot_runs.jsonl",
                    run.run_id,
                    outcome.leaderboard_entry_id,
                    findings,
                )
            if outcome.evaluation_id != run.locked_evaluation_id:
                _add_link_finding(
                    "research_autopilot_run_shadow_evaluation_mismatch",
                    storage_path / "research_autopilot_runs.jsonl",
                    run.run_id,
                    outcome.evaluation_id,
                    findings,
                )
            if outcome.strategy_card_id != run.strategy_card_id:
                _add_link_finding(
                    "research_autopilot_run_shadow_strategy_card_mismatch",
                    storage_path / "research_autopilot_runs.jsonl",
                    run.run_id,
                    outcome.strategy_card_id,
                    findings,
                )
            if outcome.trial_id != run.experiment_trial_id:
                _add_link_finding(
                    "research_autopilot_run_shadow_trial_mismatch",
                    storage_path / "research_autopilot_runs.jsonl",
                    run.run_id,
                    outcome.trial_id,
                    findings,
                )


def _check_revision_retest_passed_trial_contexts(
    *,
    storage_path: Path,
    experiment_trials: list[ExperimentTrial],
    backtest_runs: list[BacktestRun],
    backtest_results: list[BacktestResult],
    walk_forward_validations: list[WalkForwardValidation],
    findings: list[HealthFinding],
) -> None:
    backtest_results_by_id = {result.result_id: result for result in backtest_results}
    backtest_runs_by_id = {run.backtest_id: run for run in backtest_runs}
    walk_forwards_by_id = {validation.validation_id: validation for validation in walk_forward_validations}
    for trial in experiment_trials:
        if not _is_revision_retest_passed_trial(trial):
            continue
        valid_contexts = _valid_revision_retest_contexts(trial, experiment_trials)
        if not valid_contexts:
            _add_integrity_finding(
                "revision_retest_passed_trial_context_unverifiable",
                storage_path / "experiment_trials.jsonl",
                trial.trial_id,
                (
                    "PASSED revision retest trial is missing source outcome "
                    "metadata needed to verify retest evidence id_context"
                ),
                findings,
            )
            continue
        if trial.backtest_result_id:
            backtest = backtest_results_by_id.get(trial.backtest_result_id)
            backtest_run = backtest_runs_by_id.get(backtest.backtest_id) if backtest is not None else None
            if backtest_run is not None and not _decision_basis_has_any_id_context(
                backtest_run.decision_basis,
                valid_contexts,
            ):
                _add_integrity_finding(
                    "revision_retest_passed_trial_backtest_context_mismatch",
                    storage_path / "experiment_trials.jsonl",
                    trial.trial_id,
                    (
                        "PASSED revision retest trial links a backtest whose run "
                        "does not carry this retest chain id_context"
                    ),
                    findings,
                )
        if trial.walk_forward_validation_id:
            walk_forward = walk_forwards_by_id.get(trial.walk_forward_validation_id)
            if walk_forward is not None and not _decision_basis_has_any_id_context(
                walk_forward.decision_basis,
                valid_contexts,
            ):
                _add_integrity_finding(
                    "revision_retest_passed_trial_walk_forward_context_mismatch",
                    storage_path / "experiment_trials.jsonl",
                    trial.trial_id,
                    (
                        "PASSED revision retest trial links a walk-forward validation "
                        "whose decision_basis does not carry this retest chain id_context"
                    ),
                    findings,
                )


def _is_revision_retest_passed_trial(trial: ExperimentTrial) -> bool:
    return (
        trial.status == "PASSED"
        and trial.parameters.get("revision_retest_protocol") == RETEST_PROTOCOL_VERSION
        and (trial.backtest_result_id is not None or trial.walk_forward_validation_id is not None)
    )


def _valid_revision_retest_contexts(
    trial: ExperimentTrial,
    experiment_trials: list[ExperimentTrial],
) -> list[str]:
    source_outcome_id = trial.parameters.get("revision_source_outcome_id")
    if not isinstance(source_outcome_id, str) or not source_outcome_id:
        return []
    contexts = [f"revision_retest:{trial.strategy_card_id}:{trial.trial_id}:{source_outcome_id}"]
    for candidate in experiment_trials:
        if candidate.trial_id == trial.trial_id:
            continue
        if candidate.status != "PENDING":
            continue
        if not _same_revision_retest_chain(candidate, trial, source_outcome_id=source_outcome_id):
            continue
        contexts.append(f"revision_retest:{candidate.strategy_card_id}:{candidate.trial_id}:{source_outcome_id}")
    return list(dict.fromkeys(contexts))


def _same_revision_retest_chain(
    candidate: ExperimentTrial,
    trial: ExperimentTrial,
    *,
    source_outcome_id: str,
) -> bool:
    return (
        candidate.strategy_card_id == trial.strategy_card_id
        and candidate.symbol == trial.symbol
        and candidate.dataset_id == trial.dataset_id
        and candidate.trial_index == trial.trial_index
        and candidate.parameters.get("revision_retest_protocol") == RETEST_PROTOCOL_VERSION
        and candidate.parameters.get("revision_retest_source_card_id") == trial.strategy_card_id
        and candidate.parameters.get("revision_source_outcome_id") == source_outcome_id
    )


def _decision_basis_has_any_id_context(decision_basis: str, contexts: list[str]) -> bool:
    return bool(set(contexts) & set(_id_context_tokens(decision_basis)))


def _id_context_tokens(decision_basis: str) -> list[str]:
    return re.findall(r"(?:^|[;,\s])id_context=([^;,\s]+)", decision_basis)


def _add_link_finding(code: str, path: Path, source_id: str, missing_id: str, findings: list[HealthFinding]) -> None:
    findings.append(
        HealthFinding(
            code=code,
            severity="blocking",
            message=f"{source_id} references missing artifact {missing_id}.",
            artifact_path=str(path),
            repair_required=True,
        )
    )


def _research_run_strategy_card_matches_agenda(
    strategy_card_id: str,
    agenda: ResearchAgenda,
    strategy_card_by_id: dict[str, StrategyCard],
) -> bool:
    if strategy_card_id in agenda.strategy_card_ids:
        return True
    if agenda.decision_basis != "strategy_lineage_research_agenda":
        return False
    card = strategy_card_by_id.get(strategy_card_id)
    if card is None or card.decision_basis != REPLACEMENT_DECISION_BASIS:
        return False
    root_card_id = card.parameters.get("replacement_source_lineage_root_card_id")
    return isinstance(root_card_id, str) and root_card_id in agenda.strategy_card_ids


def _check_m7_evidence_integrity(
    storage_path: Path,
    source_registry_entries: list[SourceRegistryEntry],
    source_documents: list[SourceDocument],
    canonical_events: list[CanonicalEvent],
    feature_snapshots: list[FeatureSnapshot],
    findings: list[HealthFinding],
) -> None:
    source_registry_path = storage_path / "source_registry.jsonl"
    source_path = storage_path / "source_documents.jsonl"
    event_path = storage_path / "canonical_events.jsonl"
    feature_path = storage_path / "feature_snapshots.jsonl"
    documents_by_id = {document.document_id: document for document in source_documents}
    source_registry_ids = {entry.source_id for entry in source_registry_entries}

    for entry in source_registry_entries:
        invalid_secret_names = [item for item in entry.secret_env_vars if "=" in item]
        if invalid_secret_names:
            _add_integrity_finding(
                "source_registry_secret_assignment_present",
                source_registry_path,
                entry.source_id,
                "source registry secret_env_vars must contain variable names only, not secret assignments",
                findings,
            )

    for document in source_documents:
        if document.source_id and document.source_id not in source_registry_ids:
            _add_integrity_finding(
                "source_document_missing_source_registry_entry",
                source_path,
                document.document_id,
                f"source document references missing source registry entry: {document.source_id}",
                findings,
            )
        if document.published_at is None or document.available_at is None:
            _add_integrity_finding(
                "source_document_missing_required_timestamp",
                source_path,
                document.document_id,
                "source document must include published_at and available_at before it can become decision-time evidence",
                findings,
            )
        if not document.source_url and not document.stable_source_id:
            _add_integrity_finding(
                "source_document_missing_stable_source",
                source_path,
                document.document_id,
                "source document must include source_url or stable_source_id",
                findings,
            )
        if not document.raw_text_hash or not document.normalized_text_hash:
            _add_integrity_finding(
                "source_document_missing_text_hash",
                source_path,
                document.document_id,
                "source document must include raw and normalized text hashes",
                findings,
            )
        ordered_times = [
            value
            for value in [document.published_at, document.available_at, document.fetched_at, document.processed_at]
            if value is not None
        ]
        if any(later < earlier for earlier, later in zip(ordered_times, ordered_times[1:])):
            _add_integrity_finding(
                "source_document_timestamp_order_invalid",
                source_path,
                document.document_id,
                "source document timestamps must be ordered published_at <= available_at <= fetched_at <= processed_at",
                findings,
            )

    for event in canonical_events:
        if event.published_at is None or event.available_at is None:
            _add_integrity_finding(
                "canonical_event_missing_required_timestamp",
                event_path,
                event.event_id,
                "canonical event must include published_at and available_at before it can become decision-time evidence",
                findings,
            )

    for snapshot in feature_snapshots:
        if snapshot.feature_timestamp > snapshot.decision_timestamp:
            _add_integrity_finding(
                "feature_snapshot_feature_after_decision",
                feature_path,
                snapshot.feature_snapshot_id,
                "feature_timestamp must be <= decision_timestamp",
                findings,
            )
        if snapshot.training_cutoff > snapshot.decision_timestamp:
            _add_integrity_finding(
                "feature_snapshot_training_cutoff_after_decision",
                feature_path,
                snapshot.feature_snapshot_id,
                "training_cutoff must be <= decision_timestamp",
                findings,
            )
        if not snapshot.leakage_safe:
            _add_integrity_finding(
                "feature_snapshot_leakage_not_safe",
                feature_path,
                snapshot.feature_snapshot_id,
                "feature snapshot is marked leakage_safe=false",
                findings,
            )
        late_documents = [
            document_id
            for document_id in snapshot.source_document_ids
            if (document := documents_by_id.get(document_id)) is not None
            and document.fetched_at > snapshot.decision_timestamp
        ]
        if late_documents:
            _add_integrity_finding(
                "feature_snapshot_source_fetched_after_decision",
                feature_path,
                snapshot.feature_snapshot_id,
                f"source documents were fetched after decision timestamp: {', '.join(late_documents)}",
                findings,
            )


def _add_integrity_finding(
    code: str,
    path: Path,
    artifact_id: str,
    message: str,
    findings: list[HealthFinding],
) -> None:
    findings.append(
        HealthFinding(
            code=code,
            severity="blocking",
            message=f"{artifact_id}: {message}.",
            artifact_path=str(path),
            repair_required=True,
        )
    )


def _check_research_dataset_leakage(
    storage_path: Path,
    research_datasets: list[ResearchDataset],
    findings: list[HealthFinding],
) -> None:
    for dataset in research_datasets:
        leakage_findings = list(dataset.leakage_findings)
        for row in dataset.rows:
            if row.feature_timestamp > row.decision_timestamp:
                leakage_findings.append(
                    f"{row.forecast_id}: feature_timestamp {row.feature_timestamp.isoformat()} "
                    f"> decision_timestamp {row.decision_timestamp.isoformat()}"
                )
            if row.label_timestamp <= row.decision_timestamp:
                leakage_findings.append(
                    f"{row.forecast_id}: label_timestamp {row.label_timestamp.isoformat()} "
                    f"<= decision_timestamp {row.decision_timestamp.isoformat()}"
                )
        if dataset.leakage_status != "passed" or leakage_findings:
            findings.append(
                HealthFinding(
                    code="research_dataset_leakage",
                    severity="blocking",
                    message=(
                        f"Research dataset {dataset.dataset_id} failed no-lookahead checks: "
                        + "; ".join(leakage_findings or [dataset.leakage_status])
                    ),
                    artifact_path=str(storage_path / "research_datasets.jsonl"),
                    repair_required=True,
                )
            )


def _check_dashboard(storage_path: Path, findings: list[HealthFinding]) -> None:
    dashboard_path = storage_path / "dashboard.html"
    if not dashboard_path.exists():
        findings.append(
            HealthFinding(
                code="dashboard_missing",
                severity="warning",
                message="dashboard.html is missing; render-dashboard should be run after artifacts change.",
                artifact_path=str(dashboard_path),
                repair_required=False,
            )
        )
        return
    html = dashboard_path.read_text(encoding="utf-8")
    if "Dashboard 產生時間" not in html:
        findings.append(
            HealthFinding(
                code="dashboard_freshness_missing",
                severity="warning",
                message="dashboard.html does not expose generated-at freshness text.",
                artifact_path=str(dashboard_path),
                repair_required=False,
            )
        )


def _finalize_health_result(
    *,
    storage_path: Path,
    symbol: str,
    now: datetime,
    findings: list[HealthFinding],
    create_repair_request: bool,
) -> HealthCheckResult:
    repair_findings = [finding for finding in findings if finding.repair_required]
    if repair_findings:
        status = "unhealthy"
        severity = "blocking"
    elif findings:
        status = "degraded"
        severity = "warning"
    else:
        status = "healthy"
        severity = "none"

    repair_request = (
        _create_repair_request(
            storage_path=storage_path,
            symbol=symbol,
            now=now,
            findings=repair_findings,
        )
        if repair_findings and create_repair_request
        else None
    )
    result = HealthCheckResult(
        check_id=HealthCheckResult.build_id(created_at=now, findings=findings),
        created_at=now,
        status=status,
        severity=severity,
        repair_required=bool(repair_findings),
        repair_request_id=repair_request.repair_request_id if repair_request else None,
        findings=findings,
    )
    return result


def _create_repair_request(
    *,
    storage_path: Path,
    symbol: str,
    now: datetime,
    findings: list[HealthFinding],
) -> RepairRequest:
    finding_codes = [finding.code for finding in findings]
    observed_failure = "; ".join(finding.message for finding in findings)
    repair_request_id = RepairRequest.build_id(
        created_at=now,
        finding_codes=finding_codes,
        observed_failure=observed_failure,
    )
    affected_artifacts = sorted({finding.artifact_path for finding in findings if finding.artifact_path})
    repair_request = RepairRequest(
        repair_request_id=repair_request_id,
        created_at=now,
        status="pending",
        severity="blocking",
        observed_failure=observed_failure,
        reproduction_command=(
            f"python .\\run_forecast_loop.py health-check --storage-dir {storage_path} --symbol {symbol}"
        ),
        expected_behavior="Health check should return healthy or degraded without blocking repair-required findings.",
        affected_artifacts=affected_artifacts,
        recommended_tests=[
            "python -m pytest -q",
            "python -m compileall -q src tests run_forecast_loop.py sitecustomize.py",
        ],
        safety_boundary="paper-only; no live trading; do not add real broker/exchange execution",
        acceptance_criteria=[
            "The reported health finding is fixed or explicitly quarantined.",
            "health-check returns repair_required=false for the active storage directory.",
            "dashboard can be regenerated and still exposes decision and health status.",
            "All tests pass.",
        ],
        finding_codes=finding_codes,
    )
    prompt_path = _write_repair_prompt(repair_request)
    repair_request.prompt_path = str(prompt_path)
    if storage_path.is_dir():
        JsonFileRepository(storage_path).save_repair_request(repair_request)
    else:
        _append_global_repair_request(repair_request)
    return repair_request


def _write_repair_prompt(repair_request: RepairRequest) -> Path:
    pending_dir = Path.cwd() / ".codex" / "repair_requests" / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)
    safe_name = repair_request.repair_request_id.replace(":", "_")
    prompt_path = pending_dir / f"{safe_name}.md"
    prompt_path.write_text(
        "\n".join(
            [
                f"# Codex Repair Request: {repair_request.repair_request_id}",
                "",
                "## Observed Failure",
                repair_request.observed_failure,
                "",
                "## Reproduction Command",
                f"`{repair_request.reproduction_command}`",
                "",
                "## Expected Behavior",
                repair_request.expected_behavior,
                "",
                "## Affected Artifacts",
                *[f"- `{artifact}`" for artifact in repair_request.affected_artifacts],
                "",
                "## Recommended First Tests",
                *[f"- `{command}`" for command in repair_request.recommended_tests],
                "",
                "## Safety Boundary",
                repair_request.safety_boundary,
                "",
                "## Acceptance Criteria",
                *[f"- {item}" for item in repair_request.acceptance_criteria],
                "",
            ]
        ),
        encoding="utf-8",
    )
    return prompt_path


def _append_global_repair_request(repair_request: RepairRequest) -> None:
    root = Path.cwd() / ".codex" / "repair_requests"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "repair_requests.jsonl"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                existing = json.loads(line)
            except json.JSONDecodeError:
                continue
            if existing.get("repair_request_id") == repair_request.repair_request_id:
                return
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(repair_request.to_dict(), ensure_ascii=False) + "\n")
