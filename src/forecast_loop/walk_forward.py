from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean

from forecast_loop.backtest import run_backtest
from forecast_loop.models import MarketCandleRecord, WalkForwardValidation, WalkForwardWindow
from forecast_loop.storage import JsonFileRepository


@dataclass(frozen=True, slots=True)
class WalkForwardEngineResult:
    validation: WalkForwardValidation
    storage_dir: Path

    def to_dict(self) -> dict:
        return {
            "storage_dir": str(self.storage_dir.resolve()),
            "validation": self.validation.to_dict(),
        }


def run_walk_forward_validation(
    *,
    storage_dir: Path | str,
    symbol: str,
    start: datetime,
    end: datetime,
    created_at: datetime,
    train_size: int = 4,
    validation_size: int = 3,
    test_size: int = 3,
    step_size: int = 1,
    initial_cash: float = 10_000.0,
    fee_bps: float = 5.0,
    slippage_bps: float = 10.0,
    moving_average_window: int = 3,
    id_context: str | None = None,
) -> WalkForwardEngineResult:
    _validate_inputs(
        storage_dir=storage_dir,
        start=start,
        end=end,
        created_at=created_at,
        train_size=train_size,
        validation_size=validation_size,
        test_size=test_size,
        step_size=step_size,
        initial_cash=initial_cash,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        moving_average_window=moving_average_window,
    )
    storage_path = Path(storage_dir)
    repository = JsonFileRepository(storage_path)
    candles = [
        record
        for record in repository.load_market_candles()
        if record.symbol == symbol and start <= record.timestamp <= end
    ]
    candles.sort(key=lambda item: item.timestamp)
    required_candles = train_size + validation_size + test_size
    if len(candles) < required_candles:
        raise ValueError(
            f"walk-forward requires at least {required_candles} candles for {symbol}; found {len(candles)}"
        )
    _validate_strictly_increasing_timestamps(candles)

    windows: list[WalkForwardWindow] = []
    backtest_result_ids: list[str] = []
    offset = 0
    while offset + required_candles <= len(candles):
        train = candles[offset : offset + train_size]
        validation = candles[offset + train_size : offset + train_size + validation_size]
        test = candles[offset + train_size + validation_size : offset + required_candles]

        validation_result = run_backtest(
            storage_dir=storage_path,
            symbol=symbol,
            start=validation[0].timestamp,
            end=validation[-1].timestamp,
            created_at=created_at,
            initial_cash=initial_cash,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            moving_average_window=moving_average_window,
            id_context=id_context,
        ).result
        test_result = run_backtest(
            storage_dir=storage_path,
            symbol=symbol,
            start=test[0].timestamp,
            end=test[-1].timestamp,
            created_at=created_at,
            initial_cash=initial_cash,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            moving_average_window=moving_average_window,
            id_context=id_context,
        ).result
        flags = _window_overfit_flags(
            validation_return=validation_result.strategy_return,
            test_return=test_result.strategy_return,
            benchmark_return=test_result.benchmark_return,
        )
        window = WalkForwardWindow(
            window_id=WalkForwardWindow.build_id(
                train_start=train[0].timestamp,
                validation_start=validation[0].timestamp,
                test_start=test[0].timestamp,
                validation_backtest_result_id=validation_result.result_id,
                test_backtest_result_id=test_result.result_id,
            ),
            train_start=train[0].timestamp,
            train_end=train[-1].timestamp,
            validation_start=validation[0].timestamp,
            validation_end=validation[-1].timestamp,
            test_start=test[0].timestamp,
            test_end=test[-1].timestamp,
            train_candle_count=len(train),
            validation_candle_count=len(validation),
            test_candle_count=len(test),
            validation_backtest_result_id=validation_result.result_id,
            test_backtest_result_id=test_result.result_id,
            validation_return=validation_result.strategy_return,
            test_return=test_result.strategy_return,
            benchmark_return=test_result.benchmark_return,
            excess_return=test_result.strategy_return - test_result.benchmark_return,
            overfit_flags=flags,
            decision_basis="non-overlapping train/validation/test rolling window with paper-only backtest metrics",
        )
        windows.append(window)
        backtest_result_ids.extend([validation_result.result_id, test_result.result_id])
        offset += step_size

    validation_returns = [window.validation_return for window in windows]
    test_returns = [window.test_return for window in windows]
    benchmark_returns = [window.benchmark_return for window in windows]
    excess_returns = [window.excess_return for window in windows]
    overfit_window_count = sum(1 for window in windows if window.overfit_flags)
    aggregate_flags = _aggregate_overfit_flags(
        windows=windows,
        average_validation_return=mean(validation_returns),
        average_test_return=mean(test_returns),
        average_benchmark_return=mean(benchmark_returns),
    )
    validation_artifact = WalkForwardValidation(
        validation_id=WalkForwardValidation.build_id(
            symbol=symbol,
            start=start,
            end=end,
            train_size=train_size,
            validation_size=validation_size,
            test_size=test_size,
            step_size=step_size,
            moving_average_window=moving_average_window,
            backtest_result_ids=backtest_result_ids,
        ),
        created_at=created_at,
        symbol=symbol,
        start=start,
        end=end,
        strategy_name="moving_average_trend",
        train_size=train_size,
        validation_size=validation_size,
        test_size=test_size,
        step_size=step_size,
        initial_cash=initial_cash,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        moving_average_window=moving_average_window,
        window_count=len(windows),
        average_validation_return=mean(validation_returns),
        average_test_return=mean(test_returns),
        average_benchmark_return=mean(benchmark_returns),
        average_excess_return=mean(excess_returns),
        test_win_rate=sum(1 for value in test_returns if value > 0) / len(test_returns),
        overfit_window_count=overfit_window_count,
        overfit_risk_flags=aggregate_flags,
        backtest_result_ids=backtest_result_ids,
        windows=windows,
        decision_basis=(
            "rolling walk-forward validation; train window is recorded as boundary context, "
            "validation and test windows are evaluated with paper-only backtests"
            + (f"; id_context={id_context}" if id_context else "")
        ),
    )
    repository.save_walk_forward_validation(validation_artifact)
    return WalkForwardEngineResult(validation=validation_artifact, storage_dir=storage_path)


def _validate_inputs(
    *,
    storage_dir: Path | str,
    start: datetime,
    end: datetime,
    created_at: datetime,
    train_size: int,
    validation_size: int,
    test_size: int,
    step_size: int,
    initial_cash: float,
    fee_bps: float,
    slippage_bps: float,
    moving_average_window: int,
) -> None:
    storage_path = Path(storage_dir)
    if not storage_path.exists() or not storage_path.is_dir():
        raise ValueError(f"storage directory does not exist: {storage_path}")
    for label, value in (("start", start), ("end", end), ("created_at", created_at)):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{label} must be timezone-aware")
    if start > end:
        raise ValueError("walk-forward start must be <= end")
    if train_size <= 0:
        raise ValueError("train_size must be positive")
    if validation_size < 2:
        raise ValueError("validation_size must be at least 2")
    if test_size < 2:
        raise ValueError("test_size must be at least 2")
    if step_size <= 0:
        raise ValueError("step_size must be positive")
    if initial_cash <= 0:
        raise ValueError("initial_cash must be positive")
    if fee_bps < 0:
        raise ValueError("fee_bps must be non-negative")
    if slippage_bps < 0:
        raise ValueError("slippage_bps must be non-negative")
    if moving_average_window <= 0:
        raise ValueError("moving_average_window must be positive")


def _validate_strictly_increasing_timestamps(candles: list[MarketCandleRecord]) -> None:
    previous_timestamp: datetime | None = None
    for candle in candles:
        if previous_timestamp is not None and candle.timestamp <= previous_timestamp:
            raise ValueError(
                "walk-forward candles must have unique, strictly increasing timestamps "
                f"for the selected symbol; duplicate or non-increasing timestamp: {candle.timestamp.isoformat()}"
            )
        previous_timestamp = candle.timestamp


def _window_overfit_flags(
    *,
    validation_return: float,
    test_return: float,
    benchmark_return: float,
) -> list[str]:
    flags: list[str] = []
    if validation_return > 0 and test_return <= 0:
        flags.append("validation_positive_test_nonpositive")
    if test_return < benchmark_return:
        flags.append("test_underperforms_benchmark")
    if validation_return - test_return > 0.05:
        flags.append("validation_test_gap_large")
    return flags


def _aggregate_overfit_flags(
    *,
    windows: list[WalkForwardWindow],
    average_validation_return: float,
    average_test_return: float,
    average_benchmark_return: float,
) -> list[str]:
    flags = {flag for window in windows for flag in window.overfit_flags}
    overfit_window_count = sum(1 for window in windows if window.overfit_flags)
    if overfit_window_count / len(windows) >= 0.5:
        flags.add("majority_windows_flagged")
    if average_validation_return > 0 and average_test_return <= 0:
        flags.add("aggregate_validation_positive_test_nonpositive")
    if average_test_return < average_benchmark_return:
        flags.add("aggregate_underperforms_benchmark")
    return sorted(flags)
