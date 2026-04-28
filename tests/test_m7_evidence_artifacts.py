from datetime import UTC, datetime, timedelta
import json

from forecast_loop.cli import main
from forecast_loop.health import run_health_check
from forecast_loop.models import (
    CanonicalEvent,
    EventEdgeEvaluation,
    EventReliabilityCheck,
    FeatureSnapshot,
    MarketReactionCheck,
    SourceDocument,
    SourceIngestionRun,
)
from forecast_loop.sqlite_repository import SQLiteRepository
from forecast_loop.storage import JsonFileRepository


def _now() -> datetime:
    return datetime(2026, 4, 28, 12, 0, tzinfo=UTC)


def _source_document(now: datetime) -> SourceDocument:
    return SourceDocument(
        document_id="source-document:official-cpi",
        source_name="BLS",
        source_type="official",
        source_url="https://www.bls.gov/news.release/cpi.htm",
        stable_source_id="bls-cpi-2026-04",
        published_at=now - timedelta(minutes=30),
        available_at=now - timedelta(minutes=29),
        fetched_at=now - timedelta(minutes=20),
        processed_at=now - timedelta(minutes=10),
        language="en",
        headline="CPI release",
        summary="Official CPI release fixture.",
        raw_text_hash="rawhash",
        normalized_text_hash="normalizedhash",
        body_excerpt="CPI details",
        entities=["BLS", "CPI"],
        symbols=["BTC-USD"],
        topics=["macro_inflation"],
        source_reliability_score=95.0,
        duplicate_group_id="duplicate-group:cpi",
        license_note="fixture",
        ingestion_run_id="source-ingestion-run:official-cpi",
    )


def _canonical_event(now: datetime) -> CanonicalEvent:
    return CanonicalEvent(
        event_id="canonical-event:official-cpi",
        event_family="macro_inflation",
        event_type="CPI",
        symbol="BTC-USD",
        title="US CPI release",
        summary="Official CPI release fixture.",
        event_time=now - timedelta(minutes=30),
        published_at=now - timedelta(minutes=30),
        available_at=now - timedelta(minutes=29),
        fetched_at=now - timedelta(minutes=20),
        source_document_ids=["source-document:official-cpi"],
        primary_document_id="source-document:official-cpi",
        credibility_score=95.0,
        cross_source_count=1,
        official_source_flag=True,
        duplicate_group_id="duplicate-group:cpi",
        status="reliable",
    )


def test_json_repository_round_trips_m7_evidence_artifacts(tmp_path):
    repository = JsonFileRepository(tmp_path)
    now = _now()
    document = _source_document(now)
    event = _canonical_event(now)
    reliability = EventReliabilityCheck(
        check_id="event-reliability:official-cpi",
        event_id=event.event_id,
        created_at=now,
        symbol="BTC-USD",
        source_type="official",
        source_reliability_score=95.0,
        official_source_flag=True,
        cross_source_count=1,
        duplicate_count=0,
        has_stable_source=True,
        has_required_timestamps=True,
        raw_hash_present=True,
        passed=True,
        blocked_reason=None,
        flags=[],
    )
    reaction = MarketReactionCheck(
        check_id="market-reaction:official-cpi",
        event_id=event.event_id,
        symbol="BTC-USD",
        created_at=now,
        decision_timestamp=now,
        event_timestamp_used=now - timedelta(minutes=30),
        pre_event_ret_1h=0.001,
        pre_event_ret_4h=0.002,
        pre_event_ret_24h=0.003,
        post_event_ret_15m=None,
        post_event_ret_1h=0.004,
        pre_event_drift_z=0.2,
        volume_shock_z=0.1,
        priced_in_ratio=0.25,
        already_priced=False,
        passed=True,
        blocked_reason=None,
        flags=["hourly_resolution_no_15m"],
    )
    edge = EventEdgeEvaluation(
        evaluation_id="event-edge:official-cpi",
        event_family="macro_inflation",
        event_type="CPI",
        symbol="BTC-USD",
        created_at=now,
        split="validation",
        horizon_hours=24,
        sample_n=30,
        average_forward_return=0.02,
        average_benchmark_return=0.01,
        average_excess_return_after_costs=0.008,
        hit_rate=0.57,
        max_adverse_excursion_p50=-0.01,
        max_adverse_excursion_p90=-0.03,
        max_drawdown_if_traded=-0.08,
        turnover=1.2,
        estimated_cost_bps=10.0,
        dsr=None,
        white_rc_p=None,
        stability_score=0.7,
        passed=True,
        blocked_reason=None,
        flags=[],
    )
    feature = FeatureSnapshot(
        feature_snapshot_id="feature-snapshot:official-cpi",
        created_at=now,
        decision_timestamp=now,
        symbol="BTC-USD",
        source_kind="event",
        feature_namespace="macro",
        feature_name="cpi_release_reliable",
        feature_value=True,
        feature_timestamp=now - timedelta(minutes=29),
        training_cutoff=now,
        source_document_ids=[document.document_id],
        event_ids=[event.event_id],
        lineage_hash="lineagehash",
        leakage_safe=True,
        flags=[],
    )
    ingestion_run = SourceIngestionRun(
        ingestion_run_id="source-ingestion-run:official-cpi",
        created_at=now,
        source_name="BLS",
        source_type="official",
        status="success",
        document_ids=[document.document_id],
        fetched_count=1,
        stored_count=1,
        error_message=None,
        decision_basis="fixture",
    )

    repository.save_source_document(document)
    repository.save_canonical_event(event)
    repository.save_event_reliability_check(reliability)
    repository.save_market_reaction_check(reaction)
    repository.save_event_edge_evaluation(edge)
    repository.save_feature_snapshot(feature)
    repository.save_source_ingestion_run(ingestion_run)

    assert repository.load_source_documents() == [document]
    assert repository.load_canonical_events() == [event]
    assert repository.load_event_reliability_checks() == [reliability]
    assert repository.load_market_reaction_checks() == [reaction]
    assert repository.load_event_edge_evaluations() == [edge]
    assert repository.load_feature_snapshots() == [feature]
    assert repository.load_source_ingestion_runs() == [ingestion_run]


def test_sqlite_migration_preserves_m7_evidence_artifacts(tmp_path, capsys):
    repository = JsonFileRepository(tmp_path)
    now = _now()
    document = _source_document(now)
    event = _canonical_event(now)
    ingestion_run = SourceIngestionRun(
        ingestion_run_id="source-ingestion-run:sqlite",
        created_at=now,
        source_name="BLS",
        source_type="official",
        status="success",
        document_ids=[document.document_id],
        fetched_count=1,
        stored_count=1,
        error_message=None,
        decision_basis="fixture",
    )
    reliability = EventReliabilityCheck(
        check_id="event-reliability:sqlite",
        event_id=event.event_id,
        created_at=now,
        symbol="BTC-USD",
        source_type="official",
        source_reliability_score=95.0,
        official_source_flag=True,
        cross_source_count=1,
        duplicate_count=0,
        has_stable_source=True,
        has_required_timestamps=True,
        raw_hash_present=True,
        passed=True,
        blocked_reason=None,
        flags=[],
    )
    reaction = MarketReactionCheck(
        check_id="market-reaction:sqlite",
        event_id=event.event_id,
        symbol="BTC-USD",
        created_at=now,
        decision_timestamp=now,
        event_timestamp_used=now - timedelta(minutes=30),
        pre_event_ret_1h=0.001,
        pre_event_ret_4h=0.002,
        pre_event_ret_24h=0.003,
        post_event_ret_15m=None,
        post_event_ret_1h=0.004,
        pre_event_drift_z=0.2,
        volume_shock_z=0.1,
        priced_in_ratio=0.25,
        already_priced=False,
        passed=True,
        blocked_reason=None,
        flags=[],
    )
    edge = EventEdgeEvaluation(
        evaluation_id="event-edge:sqlite",
        event_family="macro_inflation",
        event_type="CPI",
        symbol="BTC-USD",
        created_at=now,
        split="validation",
        horizon_hours=24,
        sample_n=30,
        average_forward_return=0.02,
        average_benchmark_return=0.01,
        average_excess_return_after_costs=0.008,
        hit_rate=0.57,
        max_adverse_excursion_p50=-0.01,
        max_adverse_excursion_p90=-0.03,
        max_drawdown_if_traded=-0.08,
        turnover=1.2,
        estimated_cost_bps=10.0,
        dsr=None,
        white_rc_p=None,
        stability_score=0.7,
        passed=True,
        blocked_reason=None,
        flags=[],
    )
    feature = FeatureSnapshot(
        feature_snapshot_id="feature-snapshot:sqlite",
        created_at=now,
        decision_timestamp=now,
        symbol="BTC-USD",
        source_kind="event",
        feature_namespace="macro",
        feature_name="cpi_release_reliable",
        feature_value=1.0,
        feature_timestamp=now - timedelta(minutes=29),
        training_cutoff=now,
        source_document_ids=[document.document_id],
        event_ids=[event.event_id],
        lineage_hash="lineagehash",
        leakage_safe=True,
        flags=[],
    )
    repository.save_source_document(document)
    repository.save_source_ingestion_run(ingestion_run)
    repository.save_canonical_event(event)
    repository.save_event_reliability_check(reliability)
    repository.save_market_reaction_check(reaction)
    repository.save_event_edge_evaluation(edge)
    repository.save_feature_snapshot(feature)

    export_dir = tmp_path / "exported"

    assert main(["migrate-jsonl-to-sqlite", "--storage-dir", str(tmp_path)]) == 0
    assert main(["db-health", "--storage-dir", str(tmp_path)]) == 0
    health_payload = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert health_payload["artifact_counts"]["source_documents"] == 1
    assert health_payload["artifact_counts"]["source_ingestion_runs"] == 1
    assert health_payload["artifact_counts"]["canonical_events"] == 1
    assert health_payload["artifact_counts"]["event_reliability_checks"] == 1
    assert health_payload["artifact_counts"]["market_reaction_checks"] == 1
    assert health_payload["artifact_counts"]["event_edge_evaluations"] == 1
    assert health_payload["artifact_counts"]["feature_snapshots"] == 1
    assert main(["export-jsonl", "--storage-dir", str(tmp_path), "--output-dir", str(export_dir)]) == 0

    sqlite_repository = SQLiteRepository(tmp_path, initialize=False)
    assert sqlite_repository.load_source_documents() == [document]
    assert sqlite_repository.load_source_ingestion_runs() == [ingestion_run]
    assert sqlite_repository.load_canonical_events() == [event]
    assert sqlite_repository.load_event_reliability_checks() == [reliability]
    assert sqlite_repository.load_market_reaction_checks() == [reaction]
    assert sqlite_repository.load_event_edge_evaluations() == [edge]
    assert sqlite_repository.load_feature_snapshots() == [feature]
    exported_repository = JsonFileRepository(export_dir)
    assert exported_repository.load_source_documents() == [document]
    assert exported_repository.load_source_ingestion_runs() == [ingestion_run]
    assert exported_repository.load_canonical_events() == [event]
    assert exported_repository.load_event_reliability_checks() == [reliability]
    assert exported_repository.load_market_reaction_checks() == [reaction]
    assert exported_repository.load_event_edge_evaluations() == [edge]
    assert exported_repository.load_feature_snapshots() == [feature]


def test_health_check_audits_m7_evidence_artifact_integrity(tmp_path):
    now = _now()
    repository = JsonFileRepository(tmp_path)
    source_document = _source_document(now)
    source_document.published_at = None
    repository.save_source_document(source_document)
    repository.save_canonical_event(
        CanonicalEvent(
            event_id="canonical-event:missing-source",
            event_family="macro_inflation",
            event_type="CPI",
            symbol="BTC-USD",
            title="Missing source",
            summary="Event references a missing source document.",
            event_time=now - timedelta(hours=1),
            published_at=now - timedelta(hours=1),
            available_at=now - timedelta(minutes=50),
            fetched_at=now - timedelta(minutes=40),
            source_document_ids=["source-document:missing"],
            primary_document_id="source-document:missing",
            credibility_score=70.0,
            cross_source_count=1,
            official_source_flag=True,
            duplicate_group_id=None,
            status="candidate",
        )
    )
    repository.save_feature_snapshot(
        FeatureSnapshot(
            feature_snapshot_id="feature-snapshot:lookahead",
            created_at=now,
            decision_timestamp=now,
            symbol="BTC-USD",
            source_kind="event",
            feature_namespace="macro",
            feature_name="lookahead_feature",
            feature_value=True,
            feature_timestamp=now + timedelta(minutes=1),
            training_cutoff=now + timedelta(minutes=1),
            source_document_ids=["source-document:missing"],
            event_ids=["canonical-event:missing"],
            lineage_hash="lineagehash",
            leakage_safe=True,
            flags=[],
        )
    )

    health = run_health_check(storage_dir=tmp_path, symbol="BTC-USD", now=now, create_repair_request=False)

    codes = {finding.code for finding in health.findings}
    assert "source_document_missing_required_timestamp" in codes
    assert "canonical_event_missing_source_document" in codes
    assert "canonical_event_missing_primary_document" in codes
    assert "feature_snapshot_missing_source_document" in codes
    assert "feature_snapshot_missing_event" in codes
    assert "feature_snapshot_feature_after_decision" in codes
    assert "feature_snapshot_training_cutoff_after_decision" in codes
    assert health.repair_required is True


def test_health_check_reports_naive_source_timestamp_instead_of_crashing(tmp_path):
    now = _now()
    source_path = tmp_path / "source_documents.jsonl"
    payload = _source_document(now).to_dict()
    payload["published_at"] = "2026-04-28T11:00:00"
    source_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    health = run_health_check(storage_dir=tmp_path, symbol="BTC-USD", now=now, create_repair_request=False)

    assert health.repair_required is True
    assert "bad_json_row" in {finding.code for finding in health.findings}
