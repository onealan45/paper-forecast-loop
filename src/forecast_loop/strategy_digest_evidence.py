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
    event_edge_source: str | None = None
    backtest_source: str | None = None
    walk_forward_source: str | None = None


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

    event_edge, event_edge_source = _evidence_by_id_or_fallback(
        digest=digest,
        items=event_edges,
        id_field="evaluation_id",
        prefix="event-edge:",
        fallback=lambda: None,
    )
    backtest, backtest_source = _evidence_by_id_or_fallback(
        digest=digest,
        items=backtests,
        id_field="result_id",
        prefix="backtest-result:",
        fallback=lambda: latest_backtest_for_research(
            backtests=[
                item
                for item in backtests
                if item.result_id not in set(digest.decision_research_artifact_ids)
            ],
            backtest_runs=backtest_runs or [],
            symbol=digest.symbol,
            as_of=digest.created_at,
        ),
    )
    walk_forward, walk_forward_source = _evidence_by_id_or_fallback(
        digest=digest,
        items=walk_forwards,
        id_field="validation_id",
        prefix="walk-forward:",
        fallback=lambda: _latest_same_symbol_as_of(
            walk_forwards,
            digest,
            id_field="validation_id",
        ),
    )
    return StrategyDigestEvidence(
        event_edge=event_edge,
        backtest=backtest,
        walk_forward=walk_forward,
        event_edge_source=event_edge_source,
        backtest_source=backtest_source,
        walk_forward_source=walk_forward_source,
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
        item = _by_id(items, id_field, set(evidence_ids), digest)
        return item, "direct" if item is not None else None
    item = fallback()
    return item, "background_fallback" if item is not None else None


def _by_id(
    items: list,
    id_field: str,
    evidence_ids: set[str],
    digest: StrategyResearchDigest,
):
    for item in items:
        if (
            getattr(item, id_field, None) in evidence_ids
            and getattr(item, "symbol", None) == digest.symbol
            and getattr(item, "created_at", digest.created_at) <= digest.created_at
        ):
            return item
    return None


def _latest_same_symbol_as_of(
    items: list,
    digest: StrategyResearchDigest,
    *,
    id_field: str | None = None,
):
    excluded = set(digest.decision_research_artifact_ids)
    matches = [
        item
        for item in items
        if getattr(item, "symbol", None) == digest.symbol
        and getattr(item, "created_at", digest.created_at) <= digest.created_at
        and (id_field is None or getattr(item, id_field, None) not in excluded)
    ]
    return max(matches, key=lambda item: item.created_at) if matches else None
