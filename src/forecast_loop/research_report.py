from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha1
from pathlib import Path

from forecast_loop.models import (
    BaselineEvaluation,
    BacktestResult,
    Forecast,
    ForecastScore,
    MarketCandleRecord,
    StrategyDecision,
    WalkForwardValidation,
)
from forecast_loop.research_artifact_selection import latest_backtest_for_research
from forecast_loop.storage import JsonFileRepository


@dataclass(frozen=True, slots=True)
class ResearchReportResult:
    report_id: str
    report_path: Path
    storage_dir: Path
    symbol: str
    created_at: datetime

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "report_path": str(self.report_path.resolve()),
            "storage_dir": str(self.storage_dir.resolve()),
            "symbol": self.symbol,
            "created_at": self.created_at.isoformat(),
        }


def generate_research_report(
    *,
    storage_dir: Path | str,
    symbol: str,
    created_at: datetime,
    output_dir: Path | str = Path("reports") / "research",
) -> ResearchReportResult:
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("created_at must be timezone-aware")
    storage_path = Path(storage_dir)
    if not storage_path.exists() or not storage_path.is_dir():
        raise ValueError(f"storage directory does not exist: {storage_path}")

    repository = JsonFileRepository(storage_path)
    candles = [candle for candle in repository.load_market_candles() if candle.symbol == symbol]
    forecasts = [forecast for forecast in repository.load_forecasts() if forecast.symbol == symbol]
    forecast_ids = {forecast.forecast_id for forecast in forecasts}
    scores = [score for score in repository.load_scores() if score.forecast_id in forecast_ids]
    baselines = [baseline for baseline in repository.load_baseline_evaluations() if baseline.symbol == symbol]
    decisions = [decision for decision in repository.load_strategy_decisions() if decision.symbol == symbol]
    backtest_runs = [run for run in repository.load_backtest_runs() if run.symbol == symbol]
    backtests = [result for result in repository.load_backtest_results() if result.symbol == symbol]
    walk_forwards = [
        validation for validation in repository.load_walk_forward_validations() if validation.symbol == symbol
    ]
    latest_baseline = _latest(baselines, "created_at")
    latest_decision = _latest(decisions, "created_at")
    latest_backtest = latest_backtest_for_research(
        backtests=backtests,
        backtest_runs=backtest_runs,
        symbol=symbol,
    )
    latest_walk_forward = _latest(walk_forwards, "created_at")
    report_id = _report_id(
        symbol=symbol,
        created_at=created_at,
        evidence_ids=[
            *(forecast.forecast_id for forecast in forecasts),
            *(score.score_id for score in scores),
            latest_baseline.baseline_id if latest_baseline else "no-baseline",
            latest_decision.decision_id if latest_decision else "no-decision",
            latest_backtest.result_id if latest_backtest else "no-backtest",
            latest_walk_forward.validation_id if latest_walk_forward else "no-walk-forward",
        ],
    )
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_path = output_path / f"{created_at.date().isoformat()}-{report_id}.md"
    report_path.write_text(
        _render_markdown(
            report_id=report_id,
            storage_dir=storage_path,
            symbol=symbol,
            created_at=created_at,
            candles=sorted(candles, key=lambda item: item.timestamp),
            forecasts=sorted(forecasts, key=lambda item: item.anchor_time),
            scores=sorted(scores, key=lambda item: item.scored_at),
            latest_baseline=latest_baseline,
            latest_decision=latest_decision,
            latest_backtest=latest_backtest,
            latest_walk_forward=latest_walk_forward,
            backtests=backtests,
        ),
        encoding="utf-8",
    )
    return ResearchReportResult(
        report_id=report_id,
        report_path=report_path,
        storage_dir=storage_path,
        symbol=symbol,
        created_at=created_at,
    )


def _render_markdown(
    *,
    report_id: str,
    storage_dir: Path,
    symbol: str,
    created_at: datetime,
    candles: list[MarketCandleRecord],
    forecasts: list[Forecast],
    scores: list[ForecastScore],
    latest_baseline: BaselineEvaluation | None,
    latest_decision: StrategyDecision | None,
    latest_backtest: BacktestResult | None,
    latest_walk_forward: WalkForwardValidation | None,
    backtests: list[BacktestResult],
) -> str:
    lines = [
        f"# Research Report: {symbol}",
        "",
        "## Metadata",
        "",
        f"- Report ID: `{report_id}`",
        f"- Created at: `{created_at.isoformat()}`",
        f"- Storage dir: `{storage_dir.resolve()}`",
        "- Safety boundary: paper-only research report; no live trading or broker execution.",
        "",
        "## Data Coverage",
        "",
        f"- Market candles: `{len(candles)}`",
        f"- Candle range: `{_range(candles)}`",
        f"- Forecasts: `{len(forecasts)}`",
        f"- Scores: `{len(scores)}`",
        f"- Scored forecast coverage: `{_coverage_ratio(len(scores), len(forecasts))}`",
        "",
        "## Model Vs Baselines",
        "",
        *_baseline_lines(latest_baseline),
        "",
        "## Backtest Metrics",
        "",
        *_backtest_lines(latest_backtest),
        "",
        "## Walk-Forward Validation",
        "",
        *_walk_forward_lines(latest_walk_forward),
        "",
        "## Drawdown",
        "",
        *_drawdown_lines(latest_backtest, latest_walk_forward, backtests),
        "",
        "## Overfit Risk",
        "",
        *_overfit_lines(latest_walk_forward),
        "",
        "## Decision Gate Result",
        "",
        *_decision_lines(latest_decision),
        "",
        "## Known Limits",
        "",
        "- Report generation summarizes existing artifacts only.",
        "- M4E does not train models, optimize parameters, or change BUY/SELL gates.",
        "- Generated reports are runtime outputs and should not be committed by default.",
        "",
    ]
    return "\n".join(lines)


def _baseline_lines(baseline: BaselineEvaluation | None) -> list[str]:
    if baseline is None:
        return ["- No baseline evaluation found."]
    lines = [
        f"- Baseline ID: `{baseline.baseline_id}`",
        f"- Evidence grade: `{baseline.evidence_grade}`",
        f"- Sample size: `{baseline.sample_size}`",
        f"- Directional accuracy: `{_fmt_optional(baseline.directional_accuracy)}`",
        f"- Naive persistence accuracy: `{_fmt_optional(baseline.baseline_accuracy)}`",
        f"- Model edge: `{_fmt_optional(baseline.model_edge)}`",
        f"- Recent score: `{_fmt_optional(baseline.recent_score)}`",
    ]
    if baseline.baseline_results:
        lines.extend(["", "| Baseline | Accuracy | Evaluated | Hits |", "| --- | ---: | ---: | ---: |"])
        for result in baseline.baseline_results:
            lines.append(
                "| {name} | `{accuracy}` | `{evaluated}` | `{hits}` |".format(
                    name=result.get("baseline_name", "unknown"),
                    accuracy=_fmt_optional(result.get("accuracy")),
                    evaluated=result.get("evaluated_count", 0),
                    hits=result.get("hit_count", 0),
                )
            )
    return lines


def _backtest_lines(backtest: BacktestResult | None) -> list[str]:
    if backtest is None:
        return ["- No backtest result found."]
    return [
        f"- Result ID: `{backtest.result_id}`",
        f"- Strategy return: `{_fmt_float(backtest.strategy_return)}`",
        f"- Benchmark return: `{_fmt_float(backtest.benchmark_return)}`",
        f"- Max drawdown: `{_fmt_float(backtest.max_drawdown)}`",
        f"- Sharpe: `{_fmt_optional(backtest.sharpe)}`",
        f"- Turnover: `{_fmt_float(backtest.turnover)}`",
        f"- Win rate: `{_fmt_optional(backtest.win_rate)}`",
        f"- Trade count: `{backtest.trade_count}`",
    ]


def _walk_forward_lines(validation: WalkForwardValidation | None) -> list[str]:
    if validation is None:
        return ["- No walk-forward validation found."]
    return [
        f"- Validation ID: `{validation.validation_id}`",
        f"- Window count: `{validation.window_count}`",
        f"- Train / validation / test size: `{validation.train_size}` / `{validation.validation_size}` / `{validation.test_size}`",
        f"- Average validation return: `{_fmt_float(validation.average_validation_return)}`",
        f"- Average test return: `{_fmt_float(validation.average_test_return)}`",
        f"- Average benchmark return: `{_fmt_float(validation.average_benchmark_return)}`",
        f"- Average excess return: `{_fmt_float(validation.average_excess_return)}`",
        f"- Test win rate: `{_fmt_float(validation.test_win_rate)}`",
        f"- Overfit window count: `{validation.overfit_window_count}`",
    ]


def _drawdown_lines(
    latest_backtest: BacktestResult | None,
    latest_walk_forward: WalkForwardValidation | None,
    backtests: list[BacktestResult],
) -> list[str]:
    lines = []
    if latest_backtest is not None:
        lines.append(f"- Latest backtest max drawdown: `{_fmt_float(latest_backtest.max_drawdown)}`")
    if latest_walk_forward is not None:
        linked = [
            result
            for result in backtests
            if result.result_id in set(latest_walk_forward.backtest_result_ids)
        ]
        if linked:
            worst_drawdown = max(result.max_drawdown for result in linked)
            lines.append(f"- Worst linked walk-forward backtest drawdown: `{_fmt_float(worst_drawdown)}`")
    return lines or ["- No drawdown evidence found."]


def _overfit_lines(validation: WalkForwardValidation | None) -> list[str]:
    if validation is None:
        return ["- No walk-forward validation exists, so overfit risk is unknown."]
    if not validation.overfit_risk_flags:
        return ["- No overfit-risk flags recorded."]
    return [f"- `{flag}`" for flag in validation.overfit_risk_flags]


def _decision_lines(decision: StrategyDecision | None) -> list[str]:
    if decision is None:
        return ["- No strategy decision found; decision gate result is unavailable."]
    return [
        f"- Decision ID: `{decision.decision_id}`",
        f"- Action: `{decision.action}`",
        f"- Tradeable: `{decision.tradeable}`",
        f"- Evidence grade: `{decision.evidence_grade}`",
        f"- Confidence: `{_fmt_optional(decision.confidence)}`",
        f"- Risk level: `{decision.risk_level}`",
        f"- Blocked reason: `{decision.blocked_reason or 'none'}`",
        f"- Recommended position pct: `{_fmt_optional(decision.recommended_position_pct)}`",
        f"- Decision basis: {decision.decision_basis}",
    ]


def _latest(items: list, attribute: str):
    if not items:
        return None
    return max(items, key=lambda item: getattr(item, attribute))


def _range(candles: list[MarketCandleRecord]) -> str:
    if not candles:
        return "none"
    return f"{candles[0].timestamp.isoformat()} to {candles[-1].timestamp.isoformat()}"


def _coverage_ratio(scored_count: int, forecast_count: int) -> str:
    if forecast_count == 0:
        return "0/0"
    return f"{scored_count}/{forecast_count} ({scored_count / forecast_count:.2%})"


def _fmt_optional(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return _fmt_float(value)
    return str(value)


def _fmt_float(value: float) -> str:
    return f"{value:.6f}"


def _report_id(*, symbol: str, created_at: datetime, evidence_ids: list[str]) -> str:
    digest = sha1(f"{symbol}:{created_at.isoformat()}:{sorted(evidence_ids)}".encode("utf-8")).hexdigest()[:12]
    return f"research-report-{digest}"
