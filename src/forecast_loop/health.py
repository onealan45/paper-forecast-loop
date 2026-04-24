from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

from forecast_loop.models import (
    BaselineEvaluation,
    BacktestResult,
    BacktestRun,
    EquityCurvePoint,
    EvaluationSummary,
    Forecast,
    ForecastScore,
    HealthCheckResult,
    HealthFinding,
    MarketCandleRecord,
    PaperFill,
    PaperOrder,
    PaperPortfolioSnapshot,
    Proposal,
    ProviderRun,
    RepairRequest,
    ResearchDataset,
    RiskSnapshot,
    Review,
    StrategyDecision,
)
from forecast_loop.storage import JsonFileRepository


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
        "scores": _load_jsonl(storage_path / "scores.jsonl", ForecastScore.from_dict, findings),
        "reviews": _load_jsonl(storage_path / "reviews.jsonl", Review.from_dict, findings),
        "proposals": _load_jsonl(storage_path / "proposals.jsonl", Proposal.from_dict, findings),
        "decisions": _load_jsonl(storage_path / "strategy_decisions.jsonl", StrategyDecision.from_dict, findings),
        "paper_orders": _load_jsonl(storage_path / "paper_orders.jsonl", PaperOrder.from_dict, findings),
        "paper_fills": _load_jsonl(storage_path / "paper_fills.jsonl", PaperFill.from_dict, findings),
        "baselines": _load_jsonl(storage_path / "baseline_evaluations.jsonl", BaselineEvaluation.from_dict, findings),
        "portfolios": _load_jsonl(storage_path / "portfolio_snapshots.jsonl", PaperPortfolioSnapshot.from_dict, findings),
        "equity_curve": _load_jsonl(storage_path / "equity_curve.jsonl", EquityCurvePoint.from_dict, findings),
        "risk_snapshots": _load_jsonl(storage_path / "risk_snapshots.jsonl", RiskSnapshot.from_dict, findings),
        "provider_runs": _load_jsonl(storage_path / "provider_runs.jsonl", ProviderRun.from_dict, findings),
        "evaluation_summaries": _load_jsonl(storage_path / "evaluation_summaries.jsonl", EvaluationSummary.from_dict, findings),
        "repair_requests": _load_jsonl(storage_path / "repair_requests.jsonl", RepairRequest.from_dict, findings),
        "research_datasets": _load_jsonl(storage_path / "research_datasets.jsonl", ResearchDataset.from_dict, findings),
        "market_candles": _load_jsonl(storage_path / "market_candles.jsonl", MarketCandleRecord.from_dict, findings),
        "backtest_runs": _load_jsonl(storage_path / "backtest_runs.jsonl", BacktestRun.from_dict, findings),
        "backtest_results": _load_jsonl(storage_path / "backtest_results.jsonl", BacktestResult.from_dict, findings),
    }
    forecasts: list[Forecast] = artifact_rows["forecasts"]
    scores: list[ForecastScore] = artifact_rows["scores"]
    reviews: list[Review] = artifact_rows["reviews"]
    proposals: list[Proposal] = artifact_rows["proposals"]
    decisions: list[StrategyDecision] = artifact_rows["decisions"]
    paper_orders: list[PaperOrder] = artifact_rows["paper_orders"]
    paper_fills: list[PaperFill] = artifact_rows["paper_fills"]
    baselines: list[BaselineEvaluation] = artifact_rows["baselines"]
    portfolios: list[PaperPortfolioSnapshot] = artifact_rows["portfolios"]
    equity_curve: list[EquityCurvePoint] = artifact_rows["equity_curve"]
    risk_snapshots: list[RiskSnapshot] = artifact_rows["risk_snapshots"]
    provider_runs: list[ProviderRun] = artifact_rows["provider_runs"]
    evaluation_summaries: list[EvaluationSummary] = artifact_rows["evaluation_summaries"]
    repair_requests: list[RepairRequest] = artifact_rows["repair_requests"]
    research_datasets: list[ResearchDataset] = artifact_rows["research_datasets"]
    market_candles: list[MarketCandleRecord] = artifact_rows["market_candles"]
    backtest_runs: list[BacktestRun] = artifact_rows["backtest_runs"]
    backtest_results: list[BacktestResult] = artifact_rows["backtest_results"]

    _check_duplicate_ids(forecasts, "forecast_id", storage_path / "forecasts.jsonl", findings)
    _check_duplicate_ids(scores, "score_id", storage_path / "scores.jsonl", findings)
    _check_duplicate_ids(reviews, "review_id", storage_path / "reviews.jsonl", findings)
    _check_duplicate_ids(proposals, "proposal_id", storage_path / "proposals.jsonl", findings)
    _check_duplicate_ids(decisions, "decision_id", storage_path / "strategy_decisions.jsonl", findings)
    _check_duplicate_ids(paper_orders, "order_id", storage_path / "paper_orders.jsonl", findings)
    _check_duplicate_ids(paper_fills, "fill_id", storage_path / "paper_fills.jsonl", findings)
    _check_duplicate_ids(baselines, "baseline_id", storage_path / "baseline_evaluations.jsonl", findings)
    _check_duplicate_ids(portfolios, "snapshot_id", storage_path / "portfolio_snapshots.jsonl", findings)
    _check_duplicate_ids(equity_curve, "point_id", storage_path / "equity_curve.jsonl", findings)
    _check_duplicate_ids(risk_snapshots, "risk_id", storage_path / "risk_snapshots.jsonl", findings)
    _check_duplicate_ids(provider_runs, "provider_run_id", storage_path / "provider_runs.jsonl", findings)
    _check_duplicate_ids(evaluation_summaries, "summary_id", storage_path / "evaluation_summaries.jsonl", findings)
    _check_duplicate_ids(repair_requests, "repair_request_id", storage_path / "repair_requests.jsonl", findings)
    _check_duplicate_ids(research_datasets, "dataset_id", storage_path / "research_datasets.jsonl", findings)
    _check_duplicate_ids(market_candles, "candle_id", storage_path / "market_candles.jsonl", findings)
    _check_duplicate_ids(backtest_runs, "backtest_id", storage_path / "backtest_runs.jsonl", findings)
    _check_duplicate_ids(backtest_results, "result_id", storage_path / "backtest_results.jsonl", findings)

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
        market_candles,
        backtest_runs,
        backtest_results,
        findings,
    )
    _check_research_dataset_leakage(storage_path, research_datasets, findings)
    _check_dashboard(storage_path, findings)

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
    market_candles: list[MarketCandleRecord],
    backtest_runs: list[BacktestRun],
    backtest_results: list[BacktestResult],
    findings: list[HealthFinding],
) -> None:
    forecast_ids = {forecast.forecast_id for forecast in forecasts}
    score_ids = {score.score_id for score in scores}
    review_ids = {review.review_id for review in reviews}
    proposal_ids = {proposal.proposal_id for proposal in proposals}
    baseline_ids = {baseline.baseline_id for baseline in baselines}
    candle_ids = {candle.candle_id for candle in market_candles}
    backtest_run_ids = {run.backtest_id for run in backtest_runs}

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
