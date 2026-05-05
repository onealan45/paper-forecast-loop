from __future__ import annotations

from dataclasses import dataclass

from forecast_loop.models import (
    BacktestResult,
    BacktestRun,
    EventEdgeEvaluation,
    StrategyResearchDigest,
    WalkForwardValidation,
)
from forecast_loop.research_artifact_selection import latest_backtest_for_research


@dataclass(slots=True)
class StrategyDigestEvidence:
    event_edge: EventEdgeEvaluation | None
    backtest: BacktestResult | None
    walk_forward: WalkForwardValidation | None


def resolve_strategy_digest_evidence(
    *,
    digest: StrategyResearchDigest | None,
    event_edges: list[EventEdgeEvaluation],
    backtests: list[BacktestResult],
    walk_forwards: list[WalkForwardValidation],
    backtest_runs: list[BacktestRun] | None = None,
) -> StrategyDigestEvidence:
    if digest is None:
        return StrategyDigestEvidence(None, None, None)

    return StrategyDigestEvidence(
        event_edge=_evidence_by_id_or_fallback(
            digest=digest,
            items=event_edges,
            id_field="evaluation_id",
            prefix="event-edge:",
            fallback=lambda: _latest_same_symbol_as_of(event_edges, digest),
        ),
        backtest=_evidence_by_id_or_fallback(
            digest=digest,
            items=backtests,
            id_field="result_id",
            prefix="backtest-result:",
            fallback=lambda: latest_backtest_for_research(
                backtests=backtests,
                backtest_runs=backtest_runs or [],
                symbol=digest.symbol,
                as_of=digest.created_at,
            ),
        ),
        walk_forward=_evidence_by_id_or_fallback(
            digest=digest,
            items=walk_forwards,
            id_field="validation_id",
            prefix="walk-forward:",
            fallback=lambda: _latest_same_symbol_as_of(walk_forwards, digest),
        ),
    )


def _evidence_by_id_or_fallback(
    *,
    digest: StrategyResearchDigest,
    items: list,
    id_field: str,
    prefix: str,
    fallback,
):
    evidence_ids = [item for item in digest.evidence_artifact_ids if item.startswith(prefix)]
    if evidence_ids:
        return _by_id(items, id_field, set(evidence_ids), digest.symbol)
    return fallback()


def _by_id(items: list, id_field: str, evidence_ids: set[str], symbol: str):
    for item in items:
        if getattr(item, id_field, None) in evidence_ids and getattr(item, "symbol", None) == symbol:
            return item
    return None


def _latest_same_symbol_as_of(items: list, digest: StrategyResearchDigest):
    matches = [
        item
        for item in items
        if getattr(item, "symbol", None) == digest.symbol
        and getattr(item, "created_at", digest.created_at) <= digest.created_at
    ]
    return max(matches, key=lambda item: item.created_at) if matches else None
