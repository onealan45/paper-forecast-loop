from __future__ import annotations

from dataclasses import dataclass

from forecast_loop.models import (
    BacktestResult,
    EventEdgeEvaluation,
    StrategyResearchDigest,
    WalkForwardValidation,
)


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
) -> StrategyDigestEvidence:
    if digest is None:
        return StrategyDigestEvidence(None, None, None)

    evidence_ids = set(digest.evidence_artifact_ids)
    event_edge = _by_id(event_edges, "evaluation_id", evidence_ids)
    backtest = _by_id(backtests, "result_id", evidence_ids)
    walk_forward = _by_id(walk_forwards, "validation_id", evidence_ids)

    return StrategyDigestEvidence(
        event_edge=event_edge or _latest_same_symbol_as_of(event_edges, digest),
        backtest=backtest or _latest_same_symbol_as_of(backtests, digest),
        walk_forward=walk_forward or _latest_same_symbol_as_of(walk_forwards, digest),
    )


def _by_id(items: list, id_field: str, evidence_ids: set[str]):
    for item in items:
        if getattr(item, id_field, None) in evidence_ids:
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
