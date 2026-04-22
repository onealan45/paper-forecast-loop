# Forecast Replay Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic historical replay and evaluation summaries so the paper-only forecasting loop can be judged on accumulated research evidence instead of one-off runs.

**Architecture:** Keep the current JSONL-based loop intact and wrap it with a replay runner that advances time on fixed hourly steps. Persist replay-scoped evaluation summaries from already-trusted score/review/proposal artifacts, and expose the workflow through a new CLI subcommand instead of adding background services or a UI.

**Tech Stack:** Python 3.13, argparse, pathlib, json, pytest, existing `forecast_loop` modules

---

## File Structure

- Modify: `src/forecast_loop/cli.py`
  - Add a `replay-range` subcommand and write replay metadata alongside existing single-run metadata.
- Modify: `src/forecast_loop/models.py`
  - Add a compact evaluation summary model with explicit provenance fields.
- Modify: `src/forecast_loop/storage.py`
  - Add JSONL persistence helpers for replay evaluation summaries.
- Create: `src/forecast_loop/replay.py`
  - Implement the deterministic replay runner that advances the loop hour by hour.
- Create: `src/forecast_loop/evaluation.py`
  - Build evaluation summaries from forecasts, scores, reviews, and proposals without changing loop correctness rules.
- Modify: `README.md`
  - Document replay contract, new commands, evaluation artifacts, and remaining limitations.
- Create: `tests/test_replay.py`
  - Cover replay stepping, idempotent reruns, and evaluation summary generation.

### Task 1: Add Deterministic Replay Runner

**Files:**
- Create: `src/forecast_loop/replay.py`
- Modify: `src/forecast_loop/cli.py`
- Test: `tests/test_replay.py`

- [ ] **Step 1: Write the failing replay test**

```python
from datetime import UTC, datetime

from forecast_loop.config import LoopConfig
from forecast_loop.providers import InMemoryMarketDataProvider
from forecast_loop.replay import ReplayRunner
from forecast_loop.storage import JsonFileRepository


def test_replay_runner_advances_hourly_and_reuses_existing_contract(tmp_path):
    provider = InMemoryMarketDataProvider(
        {
            "BTC-USD": make_hourly_candles(
                datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
                12,
                start_price=100,
                step=2,
            )
        }
    )
    repository = JsonFileRepository(tmp_path)
    runner = ReplayRunner(
        config=LoopConfig(symbol="BTC-USD", horizon_hours=2, lookback_candles=3),
        data_provider=provider,
        repository=repository,
    )

    result = runner.run_range(
        start=datetime(2026, 4, 21, 4, 0, tzinfo=UTC),
        end=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
    )

    assert result.cycles_run == 5
    assert result.forecasts_created == 5
    assert result.scores_created == 3
    assert result.first_cycle_at == datetime(2026, 4, 21, 4, 0, tzinfo=UTC)
    assert result.last_cycle_at == datetime(2026, 4, 21, 8, 0, tzinfo=UTC)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_replay.py::test_replay_runner_advances_hourly_and_reuses_existing_contract -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'forecast_loop.replay'` or missing `ReplayRunner`

- [ ] **Step 3: Write minimal replay implementation**

```python
from dataclasses import dataclass
from datetime import datetime, timedelta

from forecast_loop.pipeline import ForecastingLoop


@dataclass(slots=True)
class ReplayResult:
    cycles_run: int
    forecasts_created: int
    scores_created: int
    first_cycle_at: datetime
    last_cycle_at: datetime


class ReplayRunner:
    def __init__(self, config, data_provider, repository) -> None:
        self.loop = ForecastingLoop(config=config, data_provider=data_provider, repository=repository)

    def run_range(self, start: datetime, end: datetime) -> ReplayResult:
        now = start
        cycles_run = 0
        forecasts_created = 0
        scores_created = 0

        while now <= end:
            result = self.loop.run_cycle(now=now)
            cycles_run += 1
            forecasts_created += 1 if result.new_forecast is not None else 0
            scores_created += len(result.scores)
            now += timedelta(hours=1)

        return ReplayResult(
            cycles_run=cycles_run,
            forecasts_created=forecasts_created,
            scores_created=scores_created,
            first_cycle_at=start,
            last_cycle_at=end,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_replay.py::test_replay_runner_advances_hourly_and_reuses_existing_contract -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/forecast_loop/replay.py src/forecast_loop/cli.py tests/test_replay.py
git commit -m "feat: add deterministic replay runner"
```

### Task 2: Persist Replay Evaluation Summaries

**Files:**
- Create: `src/forecast_loop/evaluation.py`
- Modify: `src/forecast_loop/models.py`
- Modify: `src/forecast_loop/storage.py`
- Test: `tests/test_replay.py`

- [ ] **Step 1: Write the failing evaluation summary test**

```python
from datetime import UTC, datetime

from forecast_loop.evaluation import build_evaluation_summary
from forecast_loop.models import Forecast, ForecastScore, Proposal, Review


def test_build_evaluation_summary_uses_existing_artifacts_only():
    summary = build_evaluation_summary(
        replay_id="replay:demo",
        generated_at=datetime(2026, 4, 21, 9, 0, tzinfo=UTC),
        forecasts=[
            Forecast(
                forecast_id="forecast:a",
                symbol="BTC-USD",
                created_at=datetime(2026, 4, 21, 4, 0, tzinfo=UTC),
                anchor_time=datetime(2026, 4, 21, 4, 0, tzinfo=UTC),
                target_window_start=datetime(2026, 4, 21, 4, 0, tzinfo=UTC),
                target_window_end=datetime(2026, 4, 21, 6, 0, tzinfo=UTC),
                candle_interval_minutes=60,
                expected_candle_count=3,
                status="resolved",
                status_reason="scored",
                predicted_regime="trend_up",
                confidence=0.55,
                provider_data_through=datetime(2026, 4, 21, 6, 0, tzinfo=UTC),
                observed_candle_count=3,
            )
        ],
        scores=[
            ForecastScore(
                score_id="score:a",
                forecast_id="forecast:a",
                scored_at=datetime(2026, 4, 21, 6, 0, tzinfo=UTC),
                predicted_regime="trend_up",
                actual_regime="trend_up",
                score=1.0,
                target_window_start=datetime(2026, 4, 21, 4, 0, tzinfo=UTC),
                target_window_end=datetime(2026, 4, 21, 6, 0, tzinfo=UTC),
                candle_interval_minutes=60,
                expected_candle_count=3,
                observed_candle_count=3,
                provider_data_through=datetime(2026, 4, 21, 6, 0, tzinfo=UTC),
                scoring_basis="regime_direction_over_fully_covered_hourly_window",
            )
        ],
        reviews=[],
        proposals=[],
    )

    assert summary.replay_id == "replay:demo"
    assert summary.forecast_count == 1
    assert summary.resolved_count == 1
    assert summary.average_score == 1.0
    assert summary.score_ids == ["score:a"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_replay.py::test_build_evaluation_summary_uses_existing_artifacts_only -q`
Expected: FAIL with missing `build_evaluation_summary` or missing evaluation model fields

- [ ] **Step 3: Write minimal evaluation summary implementation**

```python
from dataclasses import dataclass


@dataclass(slots=True)
class EvaluationSummary:
    replay_id: str
    generated_at: datetime
    forecast_count: int
    resolved_count: int
    waiting_for_data_count: int
    unscorable_count: int
    average_score: float | None
    score_ids: list[str]
    review_ids: list[str]
    proposal_ids: list[str]


def build_evaluation_summary(*, replay_id, generated_at, forecasts, scores, reviews, proposals):
    resolved_count = sum(1 for forecast in forecasts if forecast.status == "resolved")
    waiting_for_data_count = sum(1 for forecast in forecasts if forecast.status == "waiting_for_data")
    unscorable_count = sum(1 for forecast in forecasts if forecast.status == "unscorable")
    average_score = None if not scores else sum(score.score for score in scores) / len(scores)
    return EvaluationSummary(
        replay_id=replay_id,
        generated_at=generated_at,
        forecast_count=len(forecasts),
        resolved_count=resolved_count,
        waiting_for_data_count=waiting_for_data_count,
        unscorable_count=unscorable_count,
        average_score=average_score,
        score_ids=[score.score_id for score in scores],
        review_ids=[review.review_id for review in reviews],
        proposal_ids=[proposal.proposal_id for proposal in proposals],
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_replay.py::test_build_evaluation_summary_uses_existing_artifacts_only -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/forecast_loop/evaluation.py src/forecast_loop/models.py src/forecast_loop/storage.py tests/test_replay.py
git commit -m "feat: add replay evaluation summaries"
```

### Task 3: Expose Replay Through CLI

**Files:**
- Modify: `src/forecast_loop/cli.py`
- Modify: `src/forecast_loop/storage.py`
- Test: `tests/test_replay.py`

- [ ] **Step 1: Write the failing CLI replay test**

```python
import json

from forecast_loop.cli import main


def test_cli_replay_range_writes_evaluation_summary(tmp_path):
    exit_code = main(
        [
            "replay-range",
            "--provider",
            "sample",
            "--symbol",
            "BTC-USD",
            "--storage-dir",
            str(tmp_path),
            "--start",
            "2026-04-21T04:00:00+00:00",
            "--end",
            "2026-04-21T08:00:00+00:00",
            "--horizon-hours",
            "2",
        ]
    )

    payload = json.loads((tmp_path / "last_replay_meta.json").read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["cycles_run"] == 5
    assert payload["scores_created"] == 3
    assert payload["evaluation_summary"]["resolved_count"] == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_replay.py::test_cli_replay_range_writes_evaluation_summary -q`
Expected: FAIL with argparse error for unknown `replay-range` command

- [ ] **Step 3: Write minimal CLI replay support**

```python
replay_range = subparsers.add_parser("replay-range")
replay_range.add_argument("--provider", choices=["sample", "coingecko"], default="sample")
replay_range.add_argument("--symbol", default="BTC-USD")
replay_range.add_argument("--storage-dir", required=True)
replay_range.add_argument("--start", required=True)
replay_range.add_argument("--end", required=True)
replay_range.add_argument("--horizon-hours", type=int, default=24)
replay_range.add_argument("--lookback-candles", type=int, default=8)

if args.command == "replay-range":
    return _replay_range(args)
```

```python
def _replay_range(args) -> int:
    start = datetime.fromisoformat(args.start).astimezone(UTC)
    end = datetime.fromisoformat(args.end).astimezone(UTC)
    provider = build_sample_provider(end, args.symbol) if args.provider == "sample" else CoinGeckoMarketDataProvider()
    repository = JsonFileRepository(args.storage_dir)
    runner = ReplayRunner(
        config=LoopConfig(symbol=args.symbol, horizon_hours=args.horizon_hours, lookback_candles=args.lookback_candles),
        data_provider=provider,
        repository=repository,
    )
    replay_result = runner.run_range(start=start, end=end)
    summary = build_evaluation_summary(
        replay_id=f"replay:{start.isoformat()}:{end.isoformat()}",
        generated_at=end,
        forecasts=repository.load_forecasts(),
        scores=repository.load_scores(),
        reviews=repository.load_reviews(),
        proposals=repository.load_proposals(),
    )
    (Path(args.storage_dir) / "last_replay_meta.json").write_text(json.dumps({
        "cycles_run": replay_result.cycles_run,
        "scores_created": replay_result.scores_created,
        "evaluation_summary": summary.__dict__,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_replay.py::test_cli_replay_range_writes_evaluation_summary -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/forecast_loop/cli.py src/forecast_loop/storage.py tests/test_replay.py
git commit -m "feat: add replay CLI entrypoint"
```

### Task 4: Document Replay Contract and Final Verification

**Files:**
- Modify: `README.md`
- Test: `tests/test_replay.py`

- [ ] **Step 1: Write the failing documentation-focused replay smoke test**

```python
import json

from forecast_loop.cli import main


def test_replay_range_is_idempotent_for_existing_storage(tmp_path):
    args = [
        "replay-range",
        "--provider",
        "sample",
        "--symbol",
        "BTC-USD",
        "--storage-dir",
        str(tmp_path),
        "--start",
        "2026-04-21T04:00:00+00:00",
        "--end",
        "2026-04-21T08:00:00+00:00",
        "--horizon-hours",
        "2",
    ]

    assert main(args) == 0
    assert main(args) == 0

    forecasts = (tmp_path / "forecasts.jsonl").read_text(encoding="utf-8").splitlines()
    scores = (tmp_path / "scores.jsonl").read_text(encoding="utf-8").splitlines()

    assert len(forecasts) == 5
    assert len(scores) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_replay.py::test_replay_range_is_idempotent_for_existing_storage -q`
Expected: FAIL due to duplicate replay artifacts or missing replay command behavior

- [ ] **Step 3: Update README with replay semantics and verify idempotent behavior**

```markdown
## Replay Contract

Use `replay-range` for deterministic historical validation.

- the runner advances on hourly steps only
- replay uses the same forecast/resolve contract as `run-once`
- replay summaries are derived from persisted artifacts instead of hidden in-memory state
- rerunning the same range against the same storage directory must not duplicate forecast, score, review, or proposal semantics
```

- [ ] **Step 4: Run full verification**

Run: `pytest -q`
Expected: PASS with the existing pipeline tests plus all replay tests green

Run: `python run_forecast_loop.py replay-range --provider sample --symbol BTC-USD --storage-dir .\\paper_storage\\manual-replay --start 2026-04-21T04:00:00+00:00 --end 2026-04-21T08:00:00+00:00 --horizon-hours 2`
Expected: exit 0 and a new `last_replay_meta.json` file with replay summary counts

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_replay.py
git commit -m "docs: describe replay validation contract"
```
