from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Callable

from forecast_loop.models import (
    AutomationRun,
    BaselineEvaluation,
    BacktestResult,
    BacktestRun,
    BrokerOrder,
    BrokerReconciliation,
    CanonicalEvent,
    EventEdgeEvaluation,
    EventReliabilityCheck,
    ExecutionSafetyGate,
    EquityCurvePoint,
    EvaluationSummary,
    FeatureSnapshot,
    Forecast,
    ForecastScore,
    MacroEvent,
    MarketReactionCheck,
    MarketCandleRecord,
    NotificationArtifact,
    PaperFill,
    PaperControlEvent,
    PaperOrder,
    PaperPortfolioSnapshot,
    Proposal,
    ProviderRun,
    RepairRequest,
    ResearchDataset,
    RiskSnapshot,
    Review,
    SourceDocument,
    SourceIngestionRun,
    SourceRegistryEntry,
    StrategyDecision,
    WalkForwardValidation,
)
from forecast_loop.storage import JsonFileRepository


SCHEMA_VERSION = 1
DEFAULT_DB_FILENAME = "forecast_loop.sqlite3"


@dataclass(frozen=True, slots=True)
class ArtifactSpec:
    artifact_type: str
    filename: str
    id_key: str
    factory: Callable[[dict], object]


ARTIFACT_SPECS: tuple[ArtifactSpec, ...] = (
    ArtifactSpec("market_candles", "market_candles.jsonl", "candle_id", MarketCandleRecord.from_dict),
    ArtifactSpec("macro_events", "macro_events.jsonl", "event_id", MacroEvent.from_dict),
    ArtifactSpec("source_registry", "source_registry.jsonl", "source_id", SourceRegistryEntry.from_dict),
    ArtifactSpec("source_documents", "source_documents.jsonl", "document_id", SourceDocument.from_dict),
    ArtifactSpec(
        "source_ingestion_runs",
        "source_ingestion_runs.jsonl",
        "ingestion_run_id",
        SourceIngestionRun.from_dict,
    ),
    ArtifactSpec("canonical_events", "canonical_events.jsonl", "event_id", CanonicalEvent.from_dict),
    ArtifactSpec(
        "event_reliability_checks",
        "event_reliability_checks.jsonl",
        "check_id",
        EventReliabilityCheck.from_dict,
    ),
    ArtifactSpec(
        "market_reaction_checks",
        "market_reaction_checks.jsonl",
        "check_id",
        MarketReactionCheck.from_dict,
    ),
    ArtifactSpec(
        "event_edge_evaluations",
        "event_edge_evaluations.jsonl",
        "evaluation_id",
        EventEdgeEvaluation.from_dict,
    ),
    ArtifactSpec("feature_snapshots", "feature_snapshots.jsonl", "feature_snapshot_id", FeatureSnapshot.from_dict),
    ArtifactSpec("forecasts", "forecasts.jsonl", "forecast_id", Forecast.from_dict),
    ArtifactSpec("scores", "scores.jsonl", "score_id", ForecastScore.from_dict),
    ArtifactSpec("reviews", "reviews.jsonl", "review_id", Review.from_dict),
    ArtifactSpec("proposals", "proposals.jsonl", "proposal_id", Proposal.from_dict),
    ArtifactSpec("evaluation_summaries", "evaluation_summaries.jsonl", "summary_id", EvaluationSummary.from_dict),
    ArtifactSpec("baseline_evaluations", "baseline_evaluations.jsonl", "baseline_id", BaselineEvaluation.from_dict),
    ArtifactSpec("strategy_decisions", "strategy_decisions.jsonl", "decision_id", StrategyDecision.from_dict),
    ArtifactSpec("paper_orders", "paper_orders.jsonl", "order_id", PaperOrder.from_dict),
    ArtifactSpec("broker_orders", "broker_orders.jsonl", "broker_order_id", BrokerOrder.from_dict),
    ArtifactSpec(
        "broker_reconciliations",
        "broker_reconciliations.jsonl",
        "reconciliation_id",
        BrokerReconciliation.from_dict,
    ),
    ArtifactSpec("execution_safety_gates", "execution_safety_gates.jsonl", "gate_id", ExecutionSafetyGate.from_dict),
    ArtifactSpec("paper_fills", "paper_fills.jsonl", "fill_id", PaperFill.from_dict),
    ArtifactSpec("control_events", "control_events.jsonl", "control_id", PaperControlEvent.from_dict),
    ArtifactSpec("portfolio_snapshots", "portfolio_snapshots.jsonl", "snapshot_id", PaperPortfolioSnapshot.from_dict),
    ArtifactSpec("equity_curve", "equity_curve.jsonl", "point_id", EquityCurvePoint.from_dict),
    ArtifactSpec("risk_snapshots", "risk_snapshots.jsonl", "risk_id", RiskSnapshot.from_dict),
    ArtifactSpec("provider_runs", "provider_runs.jsonl", "provider_run_id", ProviderRun.from_dict),
    ArtifactSpec("automation_runs", "automation_runs.jsonl", "automation_run_id", AutomationRun.from_dict),
    ArtifactSpec(
        "notification_artifacts",
        "notification_artifacts.jsonl",
        "notification_id",
        NotificationArtifact.from_dict,
    ),
    ArtifactSpec("repair_requests", "repair_requests.jsonl", "repair_request_id", RepairRequest.from_dict),
    ArtifactSpec("research_datasets", "research_datasets.jsonl", "dataset_id", ResearchDataset.from_dict),
    ArtifactSpec("backtest_runs", "backtest_runs.jsonl", "backtest_id", BacktestRun.from_dict),
    ArtifactSpec("backtest_results", "backtest_results.jsonl", "result_id", BacktestResult.from_dict),
    ArtifactSpec(
        "walk_forward_validations",
        "walk_forward_validations.jsonl",
        "validation_id",
        WalkForwardValidation.from_dict,
    ),
)
_SPEC_BY_TYPE = {spec.artifact_type: spec for spec in ARTIFACT_SPECS}


def sqlite_db_path(storage_dir: Path | str, db_path: Path | str | None = None) -> Path:
    if db_path is not None:
        return Path(db_path)
    return Path(storage_dir) / DEFAULT_DB_FILENAME


class SQLiteRepository:
    def __init__(self, root: Path | str, db_path: Path | str | None = None, *, initialize: bool = True) -> None:
        self.root = Path(root)
        self.db_path = sqlite_db_path(self.root, db_path)
        if initialize:
            self.root.mkdir(parents=True, exist_ok=True)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.initialize_schema()

    def initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    artifact_type TEXT NOT NULL,
                    artifact_id TEXT NOT NULL,
                    created_at TEXT,
                    payload_json TEXT NOT NULL,
                    inserted_at TEXT NOT NULL,
                    UNIQUE (artifact_type, artifact_id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_artifacts_type_sequence
                ON artifacts (artifact_type, sequence)
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, datetime.now(tz=UTC).isoformat()),
            )

    def save_market_candle(self, candle: MarketCandleRecord) -> None:
        self._save_unique("market_candles", candle.candle_id, candle.to_dict())

    def load_market_candles(self) -> list[MarketCandleRecord]:
        return self._load("market_candles", MarketCandleRecord.from_dict)

    def save_macro_event(self, event: MacroEvent) -> None:
        self._save_unique("macro_events", event.event_id, event.to_dict())

    def load_macro_events(self) -> list[MacroEvent]:
        return self._load("macro_events", MacroEvent.from_dict)

    def save_source_registry_entry(self, entry: SourceRegistryEntry) -> None:
        self._save_unique("source_registry", entry.source_id, entry.to_dict())

    def load_source_registry_entries(self) -> list[SourceRegistryEntry]:
        return self._load("source_registry", SourceRegistryEntry.from_dict)

    def save_source_document(self, document: SourceDocument) -> None:
        self._save_unique("source_documents", document.document_id, document.to_dict())

    def load_source_documents(self) -> list[SourceDocument]:
        return self._load("source_documents", SourceDocument.from_dict)

    def save_source_ingestion_run(self, run: SourceIngestionRun) -> None:
        self._save_unique("source_ingestion_runs", run.ingestion_run_id, run.to_dict())

    def load_source_ingestion_runs(self) -> list[SourceIngestionRun]:
        return self._load("source_ingestion_runs", SourceIngestionRun.from_dict)

    def save_canonical_event(self, event: CanonicalEvent) -> None:
        self._save_unique("canonical_events", event.event_id, event.to_dict())

    def load_canonical_events(self) -> list[CanonicalEvent]:
        return self._load("canonical_events", CanonicalEvent.from_dict)

    def save_event_reliability_check(self, check: EventReliabilityCheck) -> None:
        self._save_unique("event_reliability_checks", check.check_id, check.to_dict())

    def load_event_reliability_checks(self) -> list[EventReliabilityCheck]:
        return self._load("event_reliability_checks", EventReliabilityCheck.from_dict)

    def save_market_reaction_check(self, check: MarketReactionCheck) -> None:
        self._save_unique("market_reaction_checks", check.check_id, check.to_dict())

    def load_market_reaction_checks(self) -> list[MarketReactionCheck]:
        return self._load("market_reaction_checks", MarketReactionCheck.from_dict)

    def save_event_edge_evaluation(self, evaluation: EventEdgeEvaluation) -> None:
        self._save_unique("event_edge_evaluations", evaluation.evaluation_id, evaluation.to_dict())

    def load_event_edge_evaluations(self) -> list[EventEdgeEvaluation]:
        return self._load("event_edge_evaluations", EventEdgeEvaluation.from_dict)

    def save_feature_snapshot(self, snapshot: FeatureSnapshot) -> None:
        self._save_unique("feature_snapshots", snapshot.feature_snapshot_id, snapshot.to_dict())

    def load_feature_snapshots(self) -> list[FeatureSnapshot]:
        return self._load("feature_snapshots", FeatureSnapshot.from_dict)

    def save_forecast(self, forecast: Forecast) -> None:
        self._save_unique("forecasts", forecast.forecast_id, forecast.to_dict())

    def load_forecasts(self) -> list[Forecast]:
        return self._load("forecasts", Forecast.from_dict)

    def replace_forecasts(self, forecasts: list[Forecast]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM artifacts WHERE artifact_type = ?", ("forecasts",))
            for forecast in forecasts:
                self._save_unique_with_connection(connection, "forecasts", forecast.forecast_id, forecast.to_dict())

    def has_score_for_forecast(self, forecast_id: str) -> bool:
        return any(score.forecast_id == forecast_id for score in self.load_scores())

    def save_score(self, score: ForecastScore) -> None:
        if self.has_score_for_forecast(score.forecast_id):
            return
        self._save_unique("scores", score.score_id, score.to_dict())

    def load_scores(self) -> list[ForecastScore]:
        return self._load("scores", ForecastScore.from_dict)

    def save_review(self, review: Review) -> None:
        self._save_unique("reviews", review.review_id, review.to_dict())

    def load_reviews(self) -> list[Review]:
        return self._load("reviews", Review.from_dict)

    def save_proposal(self, proposal: Proposal) -> None:
        self._save_unique("proposals", proposal.proposal_id, proposal.to_dict())

    def load_proposals(self) -> list[Proposal]:
        return self._load("proposals", Proposal.from_dict)

    def save_evaluation_summary(self, summary: EvaluationSummary) -> None:
        normalized_summary = EvaluationSummary.from_dict(summary.to_dict())
        self._save_unique("evaluation_summaries", normalized_summary.summary_id, normalized_summary.to_dict())

    def load_evaluation_summaries(self) -> list[EvaluationSummary]:
        return self._load("evaluation_summaries", EvaluationSummary.from_dict)

    def save_baseline_evaluation(self, baseline: BaselineEvaluation) -> None:
        self._save_unique("baseline_evaluations", baseline.baseline_id, baseline.to_dict())

    def load_baseline_evaluations(self) -> list[BaselineEvaluation]:
        return self._load("baseline_evaluations", BaselineEvaluation.from_dict)

    def save_strategy_decision(self, decision: StrategyDecision) -> None:
        self._save_unique("strategy_decisions", decision.decision_id, decision.to_dict())

    def load_strategy_decisions(self) -> list[StrategyDecision]:
        return self._load("strategy_decisions", StrategyDecision.from_dict)

    def save_paper_order(self, order: PaperOrder) -> None:
        self._save_unique("paper_orders", order.order_id, order.to_dict())

    def load_paper_orders(self) -> list[PaperOrder]:
        return self._load("paper_orders", PaperOrder.from_dict)

    def save_broker_order(self, order: BrokerOrder) -> None:
        self._save_unique("broker_orders", order.broker_order_id, order.to_dict())

    def load_broker_orders(self) -> list[BrokerOrder]:
        return self._load("broker_orders", BrokerOrder.from_dict)

    def save_broker_reconciliation(self, reconciliation: BrokerReconciliation) -> None:
        self._save_unique(
            "broker_reconciliations",
            reconciliation.reconciliation_id,
            reconciliation.to_dict(),
        )

    def load_broker_reconciliations(self) -> list[BrokerReconciliation]:
        return self._load("broker_reconciliations", BrokerReconciliation.from_dict)

    def save_execution_safety_gate(self, gate: ExecutionSafetyGate) -> None:
        self._save_unique("execution_safety_gates", gate.gate_id, gate.to_dict())

    def load_execution_safety_gates(self) -> list[ExecutionSafetyGate]:
        return self._load("execution_safety_gates", ExecutionSafetyGate.from_dict)

    def replace_paper_orders(self, orders: list[PaperOrder]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM artifacts WHERE artifact_type = ?", ("paper_orders",))
            for order in orders:
                self._save_unique_with_connection(connection, "paper_orders", order.order_id, order.to_dict())

    def save_paper_fill(self, fill: PaperFill) -> None:
        self._save_unique("paper_fills", fill.fill_id, fill.to_dict())

    def load_paper_fills(self) -> list[PaperFill]:
        return self._load("paper_fills", PaperFill.from_dict)

    def save_control_event(self, event: PaperControlEvent) -> None:
        self._save_unique("control_events", event.control_id, event.to_dict())

    def load_control_events(self) -> list[PaperControlEvent]:
        return self._load("control_events", PaperControlEvent.from_dict)

    def save_portfolio_snapshot(self, snapshot: PaperPortfolioSnapshot) -> None:
        self._save_unique("portfolio_snapshots", snapshot.snapshot_id, snapshot.to_dict())

    def load_portfolio_snapshots(self) -> list[PaperPortfolioSnapshot]:
        return self._load("portfolio_snapshots", PaperPortfolioSnapshot.from_dict)

    def save_equity_curve_point(self, point: EquityCurvePoint) -> None:
        self._save_unique("equity_curve", point.point_id, point.to_dict())

    def load_equity_curve_points(self) -> list[EquityCurvePoint]:
        return self._load("equity_curve", EquityCurvePoint.from_dict)

    def save_risk_snapshot(self, snapshot: RiskSnapshot) -> None:
        self._save_unique("risk_snapshots", snapshot.risk_id, snapshot.to_dict())

    def load_risk_snapshots(self) -> list[RiskSnapshot]:
        return self._load("risk_snapshots", RiskSnapshot.from_dict)

    def save_provider_run(self, provider_run: ProviderRun) -> None:
        self._save_unique("provider_runs", provider_run.provider_run_id, provider_run.to_dict())

    def load_provider_runs(self) -> list[ProviderRun]:
        return self._load("provider_runs", ProviderRun.from_dict)

    def save_automation_run(self, run: AutomationRun) -> None:
        self._save_unique("automation_runs", run.automation_run_id, run.to_dict())

    def load_automation_runs(self) -> list[AutomationRun]:
        return self._load("automation_runs", AutomationRun.from_dict)

    def save_notification_artifact(self, notification: NotificationArtifact) -> None:
        self._save_unique("notification_artifacts", notification.notification_id, notification.to_dict())

    def load_notification_artifacts(self) -> list[NotificationArtifact]:
        return self._load("notification_artifacts", NotificationArtifact.from_dict)

    def save_repair_request(self, repair_request: RepairRequest) -> None:
        self._save_unique("repair_requests", repair_request.repair_request_id, repair_request.to_dict())

    def load_repair_requests(self) -> list[RepairRequest]:
        return self._load("repair_requests", RepairRequest.from_dict)

    def save_research_dataset(self, dataset: ResearchDataset) -> None:
        self._save_unique("research_datasets", dataset.dataset_id, dataset.to_dict())

    def load_research_datasets(self) -> list[ResearchDataset]:
        return self._load("research_datasets", ResearchDataset.from_dict)

    def save_backtest_run(self, run: BacktestRun) -> None:
        self._save_unique("backtest_runs", run.backtest_id, run.to_dict())

    def load_backtest_runs(self) -> list[BacktestRun]:
        return self._load("backtest_runs", BacktestRun.from_dict)

    def save_backtest_result(self, result: BacktestResult) -> None:
        self._save_unique("backtest_results", result.result_id, result.to_dict())

    def load_backtest_results(self) -> list[BacktestResult]:
        return self._load("backtest_results", BacktestResult.from_dict)

    def save_walk_forward_validation(self, validation: WalkForwardValidation) -> None:
        self._save_unique("walk_forward_validations", validation.validation_id, validation.to_dict())

    def load_walk_forward_validations(self) -> list[WalkForwardValidation]:
        return self._load("walk_forward_validations", WalkForwardValidation.from_dict)

    def artifact_counts(self) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT artifact_type, COUNT(*) FROM artifacts GROUP BY artifact_type ORDER BY artifact_type"
            ).fetchall()
        counts = {artifact_type: 0 for artifact_type in _SPEC_BY_TYPE}
        counts.update({artifact_type: count for artifact_type, count in rows})
        return counts

    def schema_versions(self) -> list[int]:
        with self._connect() as connection:
            rows = connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
        return [row[0] for row in rows]

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _save_unique(self, artifact_type: str, artifact_id: str, payload: dict) -> None:
        with self._connect() as connection:
            self._save_unique_with_connection(connection, artifact_type, artifact_id, payload)

    def _save_unique_with_connection(
        self,
        connection: sqlite3.Connection,
        artifact_type: str,
        artifact_id: str,
        payload: dict,
    ) -> None:
        connection.execute(
            """
            INSERT OR IGNORE INTO artifacts(
                artifact_type,
                artifact_id,
                created_at,
                payload_json,
                inserted_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                artifact_type,
                artifact_id,
                _artifact_timestamp(payload),
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                datetime.now(tz=UTC).isoformat(),
            ),
        )

    def _load(self, artifact_type: str, factory: Callable[[dict], object]) -> list:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM artifacts
                WHERE artifact_type = ?
                ORDER BY sequence
                """,
                (artifact_type,),
            ).fetchall()
        return [factory(json.loads(row[0])) for row in rows]


def initialize_sqlite_database(storage_dir: Path | str, db_path: Path | str | None = None) -> dict:
    repository = SQLiteRepository(storage_dir, db_path=db_path)
    return {
        "db_path": str(repository.db_path.resolve()),
        "schema_version": SCHEMA_VERSION,
        "schema_versions": repository.schema_versions(),
        "artifact_counts": repository.artifact_counts(),
    }


def migrate_jsonl_to_sqlite(storage_dir: Path | str, db_path: Path | str | None = None) -> dict:
    json_repository = JsonFileRepository(storage_dir)
    sqlite_repository = SQLiteRepository(storage_dir, db_path=db_path)
    before_counts = sqlite_repository.artifact_counts()

    for candle in json_repository.load_market_candles():
        sqlite_repository.save_market_candle(candle)
    for event in json_repository.load_macro_events():
        sqlite_repository.save_macro_event(event)
    for entry in json_repository.load_source_registry_entries():
        sqlite_repository.save_source_registry_entry(entry)
    for document in json_repository.load_source_documents():
        sqlite_repository.save_source_document(document)
    for run in json_repository.load_source_ingestion_runs():
        sqlite_repository.save_source_ingestion_run(run)
    for event in json_repository.load_canonical_events():
        sqlite_repository.save_canonical_event(event)
    for check in json_repository.load_event_reliability_checks():
        sqlite_repository.save_event_reliability_check(check)
    for check in json_repository.load_market_reaction_checks():
        sqlite_repository.save_market_reaction_check(check)
    for evaluation in json_repository.load_event_edge_evaluations():
        sqlite_repository.save_event_edge_evaluation(evaluation)
    for snapshot in json_repository.load_feature_snapshots():
        sqlite_repository.save_feature_snapshot(snapshot)
    for forecast in json_repository.load_forecasts():
        sqlite_repository.save_forecast(forecast)
    for score in json_repository.load_scores():
        sqlite_repository.save_score(score)
    for review in json_repository.load_reviews():
        sqlite_repository.save_review(review)
    for proposal in json_repository.load_proposals():
        sqlite_repository.save_proposal(proposal)
    for summary in json_repository.load_evaluation_summaries():
        sqlite_repository.save_evaluation_summary(summary)
    for baseline in json_repository.load_baseline_evaluations():
        sqlite_repository.save_baseline_evaluation(baseline)
    for decision in json_repository.load_strategy_decisions():
        sqlite_repository.save_strategy_decision(decision)
    for order in json_repository.load_paper_orders():
        sqlite_repository.save_paper_order(order)
    for order in json_repository.load_broker_orders():
        sqlite_repository.save_broker_order(order)
    for reconciliation in json_repository.load_broker_reconciliations():
        sqlite_repository.save_broker_reconciliation(reconciliation)
    for gate in json_repository.load_execution_safety_gates():
        sqlite_repository.save_execution_safety_gate(gate)
    for fill in json_repository.load_paper_fills():
        sqlite_repository.save_paper_fill(fill)
    for event in json_repository.load_control_events():
        sqlite_repository.save_control_event(event)
    for snapshot in json_repository.load_portfolio_snapshots():
        sqlite_repository.save_portfolio_snapshot(snapshot)
    for point in json_repository.load_equity_curve_points():
        sqlite_repository.save_equity_curve_point(point)
    for snapshot in json_repository.load_risk_snapshots():
        sqlite_repository.save_risk_snapshot(snapshot)
    for provider_run in json_repository.load_provider_runs():
        sqlite_repository.save_provider_run(provider_run)
    for run in json_repository.load_automation_runs():
        sqlite_repository.save_automation_run(run)
    for notification in json_repository.load_notification_artifacts():
        sqlite_repository.save_notification_artifact(notification)
    for repair_request in json_repository.load_repair_requests():
        sqlite_repository.save_repair_request(repair_request)
    for dataset in json_repository.load_research_datasets():
        sqlite_repository.save_research_dataset(dataset)
    for run in json_repository.load_backtest_runs():
        sqlite_repository.save_backtest_run(run)
    for result in json_repository.load_backtest_results():
        sqlite_repository.save_backtest_result(result)
    for validation in json_repository.load_walk_forward_validations():
        sqlite_repository.save_walk_forward_validation(validation)

    after_counts = sqlite_repository.artifact_counts()
    return {
        "db_path": str(sqlite_repository.db_path.resolve()),
        "schema_version": SCHEMA_VERSION,
        "artifact_counts": after_counts,
        "inserted_counts": {
            artifact_type: after_counts[artifact_type] - before_counts.get(artifact_type, 0)
            for artifact_type in after_counts
        },
    }


def export_sqlite_to_jsonl(
    storage_dir: Path | str,
    output_dir: Path | str,
    db_path: Path | str | None = None,
) -> dict:
    repository = _open_existing_repository(storage_dir, db_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}

    for spec in ARTIFACT_SPECS:
        rows = _raw_payloads(repository.db_path, spec.artifact_type)
        counts[spec.artifact_type] = len(rows)
        artifact_path = output_path / spec.filename
        if rows:
            artifact_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        elif artifact_path.exists():
            artifact_path.write_text("", encoding="utf-8")

    return {
        "db_path": str(repository.db_path.resolve()),
        "output_dir": str(output_path.resolve()),
        "artifact_counts": counts,
    }


def sqlite_db_health(storage_dir: Path | str, db_path: Path | str | None = None) -> dict:
    path = sqlite_db_path(storage_dir, db_path)
    if not path.exists():
        return {
            "status": "unhealthy",
            "severity": "blocking",
            "repair_required": True,
            "db_path": str(path.resolve()),
            "schema_version": None,
            "artifact_counts": {},
            "findings": [
                {
                    "code": "sqlite_db_missing",
                    "severity": "blocking",
                    "message": f"SQLite database does not exist: {path}",
                }
            ],
        }

    findings: list[dict] = []
    counts = {artifact_type: 0 for artifact_type in _SPEC_BY_TYPE}
    schema_versions: list[int] = []
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
            schema_versions = [
                row[0]
                for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
            ]
            if SCHEMA_VERSION not in schema_versions:
                findings.append(
                    {
                        "code": "sqlite_schema_version_missing",
                        "severity": "blocking",
                        "message": f"Expected schema version {SCHEMA_VERSION} is not applied.",
                    }
                )
            rows = connection.execute(
                "SELECT artifact_type, COUNT(*) FROM artifacts GROUP BY artifact_type ORDER BY artifact_type"
            ).fetchall()
            counts.update({artifact_type: count for artifact_type, count in rows})
            duplicates = connection.execute(
                """
                SELECT artifact_type, artifact_id, COUNT(*)
                FROM artifacts
                GROUP BY artifact_type, artifact_id
                HAVING COUNT(*) > 1
                """
            ).fetchall()
            for artifact_type, artifact_id, count in duplicates:
                findings.append(
                    {
                        "code": "sqlite_duplicate_artifact_id",
                        "severity": "blocking",
                        "message": f"{artifact_type}:{artifact_id} appears {count} times.",
                    }
                )
            for spec in ARTIFACT_SPECS:
                _check_sqlite_payloads(connection, spec, findings)
    except Exception as exc:
        findings.append(
            {
                "code": "sqlite_health_error",
                "severity": "blocking",
                "message": str(exc),
            }
        )

    status = "healthy" if not findings else "unhealthy"
    return {
        "status": status,
        "severity": "none" if status == "healthy" else "blocking",
        "repair_required": status != "healthy",
        "db_path": str(path.resolve()),
        "schema_version": max(schema_versions) if schema_versions else None,
        "schema_versions": schema_versions,
        "artifact_counts": counts,
        "findings": findings,
    }


def _open_existing_repository(storage_dir: Path | str, db_path: Path | str | None) -> SQLiteRepository:
    path = sqlite_db_path(storage_dir, db_path)
    if not path.exists():
        raise ValueError(f"SQLite database does not exist: {path}. Run init-db or migrate-jsonl-to-sqlite first.")
    return SQLiteRepository(storage_dir, db_path=db_path, initialize=False)


def _raw_payloads(db_path: Path, artifact_type: str) -> list[str]:
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as connection:
        rows = connection.execute(
            """
            SELECT payload_json
            FROM artifacts
            WHERE artifact_type = ?
            ORDER BY sequence
            """,
            (artifact_type,),
        ).fetchall()
    return [row[0] for row in rows]


def _check_sqlite_payloads(connection: sqlite3.Connection, spec: ArtifactSpec, findings: list[dict]) -> None:
    rows = connection.execute(
        """
        SELECT sequence, artifact_id, payload_json
        FROM artifacts
        WHERE artifact_type = ?
        ORDER BY sequence
        """,
        (spec.artifact_type,),
    ).fetchall()
    for sequence, artifact_id, payload_json in rows:
        try:
            payload = json.loads(payload_json)
            spec.factory(payload)
        except Exception as exc:
            findings.append(
                {
                    "code": "sqlite_bad_payload",
                    "severity": "blocking",
                    "message": f"{spec.artifact_type}:{artifact_id} at sequence {sequence} cannot be parsed: {exc}",
                }
            )


def _artifact_timestamp(payload: dict) -> str | None:
    for key in ("created_at", "scored_at", "generated_at"):
        value = payload.get(key)
        if value:
            return value
    return None
