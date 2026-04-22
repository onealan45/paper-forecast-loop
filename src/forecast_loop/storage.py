from __future__ import annotations

import json
from pathlib import Path

from forecast_loop.models import Forecast, ForecastScore, Proposal, Review


class JsonFileRepository:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.forecasts_path = self.root / "forecasts.jsonl"
        self.scores_path = self.root / "scores.jsonl"
        self.reviews_path = self.root / "reviews.jsonl"
        self.proposals_path = self.root / "proposals.jsonl"

    def save_forecast(self, forecast: Forecast) -> None:
        with self.forecasts_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(forecast.to_dict()) + "\n")

    def load_forecasts(self) -> list[Forecast]:
        if not self.forecasts_path.exists():
            return []

        with self.forecasts_path.open("r", encoding="utf-8") as handle:
            return [
                Forecast.from_dict(json.loads(line))
                for line in handle.read().splitlines()
                if line.strip()
            ]

    def replace_forecasts(self, forecasts: list[Forecast]) -> None:
        with self.forecasts_path.open("w", encoding="utf-8") as handle:
            for forecast in forecasts:
                handle.write(json.dumps(forecast.to_dict()) + "\n")

    def save_score(self, score: ForecastScore) -> None:
        self._append(self.scores_path, score.to_dict())

    def load_scores(self) -> list[ForecastScore]:
        return self._load_lines(self.scores_path, ForecastScore.from_dict)

    def save_review(self, review: Review) -> None:
        self._append(self.reviews_path, review.to_dict())

    def load_reviews(self) -> list[Review]:
        return self._load_lines(self.reviews_path, Review.from_dict)

    def save_proposal(self, proposal: Proposal) -> None:
        self._append(self.proposals_path, proposal.to_dict())

    def load_proposals(self) -> list[Proposal]:
        return self._load_lines(self.proposals_path, Proposal.from_dict)

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
