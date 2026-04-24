from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from forecast_loop.models import (
    BaselineEvaluation,
    EquityCurvePoint,
    EvaluationSummary,
    Forecast,
    ForecastScore,
    PaperFill,
    PaperOrder,
    PaperPortfolioSnapshot,
    Proposal,
    RepairRequest,
    RiskSnapshot,
    Review,
    StrategyDecision,
)


class ArtifactRepository(Protocol):
    def save_forecast(self, forecast: Forecast) -> None: ...

    def load_forecasts(self) -> list[Forecast]: ...

    def replace_forecasts(self, forecasts: list[Forecast]) -> None: ...

    def has_score_for_forecast(self, forecast_id: str) -> bool: ...

    def save_score(self, score: ForecastScore) -> None: ...

    def load_scores(self) -> list[ForecastScore]: ...

    def save_review(self, review: Review) -> None: ...

    def load_reviews(self) -> list[Review]: ...

    def save_proposal(self, proposal: Proposal) -> None: ...

    def load_proposals(self) -> list[Proposal]: ...

    def save_evaluation_summary(self, summary: EvaluationSummary) -> None: ...

    def load_evaluation_summaries(self) -> list[EvaluationSummary]: ...

    def save_baseline_evaluation(self, baseline: BaselineEvaluation) -> None: ...

    def load_baseline_evaluations(self) -> list[BaselineEvaluation]: ...

    def save_strategy_decision(self, decision: StrategyDecision) -> None: ...

    def load_strategy_decisions(self) -> list[StrategyDecision]: ...

    def save_paper_order(self, order: PaperOrder) -> None: ...

    def load_paper_orders(self) -> list[PaperOrder]: ...

    def replace_paper_orders(self, orders: list[PaperOrder]) -> None: ...

    def save_paper_fill(self, fill: PaperFill) -> None: ...

    def load_paper_fills(self) -> list[PaperFill]: ...

    def save_portfolio_snapshot(self, snapshot: PaperPortfolioSnapshot) -> None: ...

    def load_portfolio_snapshots(self) -> list[PaperPortfolioSnapshot]: ...

    def save_equity_curve_point(self, point: EquityCurvePoint) -> None: ...

    def load_equity_curve_points(self) -> list[EquityCurvePoint]: ...

    def save_risk_snapshot(self, snapshot: RiskSnapshot) -> None: ...

    def load_risk_snapshots(self) -> list[RiskSnapshot]: ...

    def save_repair_request(self, repair_request: RepairRequest) -> None: ...

    def load_repair_requests(self) -> list[RepairRequest]: ...


class JsonFileRepository:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.forecasts_path = self.root / "forecasts.jsonl"
        self.scores_path = self.root / "scores.jsonl"
        self.reviews_path = self.root / "reviews.jsonl"
        self.proposals_path = self.root / "proposals.jsonl"
        self.evaluation_summaries_path = self.root / "evaluation_summaries.jsonl"
        self.baseline_evaluations_path = self.root / "baseline_evaluations.jsonl"
        self.strategy_decisions_path = self.root / "strategy_decisions.jsonl"
        self.paper_orders_path = self.root / "paper_orders.jsonl"
        self.paper_fills_path = self.root / "paper_fills.jsonl"
        self.portfolio_snapshots_path = self.root / "portfolio_snapshots.jsonl"
        self.equity_curve_path = self.root / "equity_curve.jsonl"
        self.risk_snapshots_path = self.root / "risk_snapshots.jsonl"
        self.repair_requests_path = self.root / "repair_requests.jsonl"

    def save_forecast(self, forecast: Forecast) -> None:
        forecasts = self.load_forecasts()
        if any(existing.forecast_id == forecast.forecast_id for existing in forecasts):
            return
        with self.forecasts_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(forecast.to_dict()) + "\n")

    def load_forecasts(self) -> list[Forecast]:
        return self._load_lines(self.forecasts_path, Forecast.from_dict)

    def replace_forecasts(self, forecasts: list[Forecast]) -> None:
        with self.forecasts_path.open("w", encoding="utf-8") as handle:
            for forecast in forecasts:
                handle.write(json.dumps(forecast.to_dict()) + "\n")

    def has_score_for_forecast(self, forecast_id: str) -> bool:
        return any(score.forecast_id == forecast_id for score in self.load_scores())

    def save_score(self, score: ForecastScore) -> None:
        scores = self.load_scores()
        if any(existing.score_id == score.score_id or existing.forecast_id == score.forecast_id for existing in scores):
            return
        self._append(self.scores_path, score.to_dict())

    def load_scores(self) -> list[ForecastScore]:
        return self._load_lines(self.scores_path, ForecastScore.from_dict)

    def save_review(self, review: Review) -> None:
        if any(existing.review_id == review.review_id for existing in self.load_reviews()):
            return
        self._append(self.reviews_path, review.to_dict())

    def load_reviews(self) -> list[Review]:
        return self._load_lines(self.reviews_path, Review.from_dict)

    def save_proposal(self, proposal: Proposal) -> None:
        if any(existing.proposal_id == proposal.proposal_id for existing in self.load_proposals()):
            return
        self._append(self.proposals_path, proposal.to_dict())

    def load_proposals(self) -> list[Proposal]:
        return self._load_lines(self.proposals_path, Proposal.from_dict)

    def save_evaluation_summary(self, summary: EvaluationSummary) -> None:
        normalized_summary = EvaluationSummary.from_dict(summary.to_dict())
        summaries = self.load_evaluation_summaries()
        if any(existing.summary_id == normalized_summary.summary_id for existing in summaries):
            return
        self._append(self.evaluation_summaries_path, normalized_summary.to_dict())

    def load_evaluation_summaries(self) -> list[EvaluationSummary]:
        summaries = self._load_lines(self.evaluation_summaries_path, EvaluationSummary.from_dict)
        deduped: list[EvaluationSummary] = []
        seen_summary_ids: set[str] = set()
        for summary in summaries:
            if summary.summary_id in seen_summary_ids:
                continue
            seen_summary_ids.add(summary.summary_id)
            deduped.append(summary)
        return deduped

    def save_baseline_evaluation(self, baseline: BaselineEvaluation) -> None:
        self._append_unique(
            self.baseline_evaluations_path,
            baseline.to_dict(),
            identity_key="baseline_id",
        )

    def load_baseline_evaluations(self) -> list[BaselineEvaluation]:
        return self._load_lines(self.baseline_evaluations_path, BaselineEvaluation.from_dict)

    def save_strategy_decision(self, decision: StrategyDecision) -> None:
        self._append_unique(
            self.strategy_decisions_path,
            decision.to_dict(),
            identity_key="decision_id",
        )

    def load_strategy_decisions(self) -> list[StrategyDecision]:
        return self._load_lines(self.strategy_decisions_path, StrategyDecision.from_dict)

    def save_paper_order(self, order: PaperOrder) -> None:
        self._append_unique(
            self.paper_orders_path,
            order.to_dict(),
            identity_key="order_id",
        )

    def load_paper_orders(self) -> list[PaperOrder]:
        return self._load_lines(self.paper_orders_path, PaperOrder.from_dict)

    def replace_paper_orders(self, orders: list[PaperOrder]) -> None:
        with self.paper_orders_path.open("w", encoding="utf-8") as handle:
            for order in orders:
                handle.write(json.dumps(order.to_dict()) + "\n")

    def save_paper_fill(self, fill: PaperFill) -> None:
        self._append_unique(
            self.paper_fills_path,
            fill.to_dict(),
            identity_key="fill_id",
        )

    def load_paper_fills(self) -> list[PaperFill]:
        return self._load_lines(self.paper_fills_path, PaperFill.from_dict)

    def save_portfolio_snapshot(self, snapshot: PaperPortfolioSnapshot) -> None:
        self._append_unique(
            self.portfolio_snapshots_path,
            snapshot.to_dict(),
            identity_key="snapshot_id",
        )

    def load_portfolio_snapshots(self) -> list[PaperPortfolioSnapshot]:
        return self._load_lines(self.portfolio_snapshots_path, PaperPortfolioSnapshot.from_dict)

    def save_equity_curve_point(self, point: EquityCurvePoint) -> None:
        self._append_unique(
            self.equity_curve_path,
            point.to_dict(),
            identity_key="point_id",
        )

    def load_equity_curve_points(self) -> list[EquityCurvePoint]:
        return self._load_lines(self.equity_curve_path, EquityCurvePoint.from_dict)

    def save_risk_snapshot(self, snapshot: RiskSnapshot) -> None:
        self._append_unique(
            self.risk_snapshots_path,
            snapshot.to_dict(),
            identity_key="risk_id",
        )

    def load_risk_snapshots(self) -> list[RiskSnapshot]:
        return self._load_lines(self.risk_snapshots_path, RiskSnapshot.from_dict)

    def save_repair_request(self, repair_request: RepairRequest) -> None:
        self._append_unique(
            self.repair_requests_path,
            repair_request.to_dict(),
            identity_key="repair_request_id",
        )

    def load_repair_requests(self) -> list[RepairRequest]:
        return self._load_lines(self.repair_requests_path, RepairRequest.from_dict)

    def _append(self, path: Path, payload: dict) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def _append_unique(self, path: Path, payload: dict, *, identity_key: str) -> None:
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    existing = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if existing.get(identity_key) == payload.get(identity_key):
                    return
        self._append(path, payload)

    def _load_lines(self, path: Path, factory) -> list:
        if not path.exists():
            return []

        with path.open("r", encoding="utf-8") as handle:
            return [
                factory(json.loads(line))
                for line in handle.read().splitlines()
                if line.strip()
            ]
