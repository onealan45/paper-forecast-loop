from __future__ import annotations

import json
from pathlib import Path

from forecast_loop.models import EvaluationSummary, Forecast, ForecastScore, Proposal, Review


class JsonFileRepository:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.forecasts_path = self.root / "forecasts.jsonl"
        self.scores_path = self.root / "scores.jsonl"
        self.reviews_path = self.root / "reviews.jsonl"
        self.proposals_path = self.root / "proposals.jsonl"
        self.evaluation_summaries_path = self.root / "evaluation_summaries.jsonl"

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

    def _append(self, path: Path, payload: dict) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def _load_lines(self, path: Path, factory) -> list:
        if not path.exists():
            return []

        with path.open("r", encoding="utf-8") as handle:
            return [
                factory(json.loads(line))
                for line in handle.read().splitlines()
                if line.strip()
            ]
