from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from pathlib import Path
from statistics import mean, pstdev

from forecast_loop.models import BacktestResult, BacktestRun, MarketCandleRecord
from forecast_loop.storage import JsonFileRepository


@dataclass(frozen=True, slots=True)
class BacktestEngineResult:
    run: BacktestRun
    result: BacktestResult
    storage_dir: Path

    def to_dict(self) -> dict:
        return {
            "storage_dir": str(self.storage_dir.resolve()),
            "run": self.run.to_dict(),
            "result": self.result.to_dict(),
        }


def run_backtest(
    *,
    storage_dir: Path | str,
    symbol: str,
    start: datetime,
    end: datetime,
    created_at: datetime,
    initial_cash: float = 10_000.0,
    fee_bps: float = 5.0,
    slippage_bps: float = 10.0,
    moving_average_window: int = 3,
    id_context: str | None = None,
) -> BacktestEngineResult:
    _validate_inputs(
        storage_dir=storage_dir,
        start=start,
        end=end,
        created_at=created_at,
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
    if len(candles) < 2:
        raise ValueError(f"backtest requires at least 2 candles for {symbol}")
    _validate_strictly_increasing_timestamps(candles)

    run = BacktestRun(
        backtest_id=BacktestRun.build_id(
            symbol=symbol,
            start=start,
            end=end,
            strategy_name="moving_average_trend",
            initial_cash=initial_cash,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            moving_average_window=moving_average_window,
            candle_ids=[candle.candle_id for candle in candles],
            id_context=id_context,
        ),
        created_at=created_at,
        symbol=symbol,
        start=start,
        end=end,
        strategy_name="moving_average_trend",
        initial_cash=initial_cash,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        moving_average_window=moving_average_window,
        candle_ids=[candle.candle_id for candle in candles],
        decision_basis=(
            "paper-only moving-average trend backtest using stored candles; "
            "target is 100% long when the prior candle close is above its prior moving average, otherwise cash"
            + (f"; id_context={id_context}" if id_context else "")
        ),
    )
    result = _simulate(
        run=run,
        created_at=created_at,
        candles=candles,
        moving_average_window=moving_average_window,
    )
    repository.save_backtest_run(run)
    repository.save_backtest_result(result)
    return BacktestEngineResult(run=run, result=result, storage_dir=storage_path)


def _simulate(
    *,
    run: BacktestRun,
    created_at: datetime,
    candles: list[MarketCandleRecord],
    moving_average_window: int,
) -> BacktestResult:
    fee_rate = run.fee_bps / 10_000
    slippage_rate = run.slippage_bps / 10_000
    cash = run.initial_cash
    quantity = 0.0
    entry_cost = 0.0
    trade_count = 0
    total_turnover = 0.0
    closed_trade_pnls: list[float] = []
    equity_curve: list[dict[str, object]] = []
    returns: list[float] = []
    previous_equity = run.initial_cash

    for index, candle in enumerate(candles):
        price = candle.adjusted_close if candle.adjusted_close is not None else candle.close
        if price <= 0:
            raise ValueError("backtest candle price must be positive")
        target_long = None
        if index > 0:
            signal_index = index - 1
            history = [
                item.adjusted_close if item.adjusted_close is not None else item.close
                for item in candles[max(0, signal_index - moving_average_window) : signal_index]
            ]
            if history:
                signal_candle = candles[signal_index]
                signal_price = signal_candle.adjusted_close if signal_candle.adjusted_close is not None else signal_candle.close
                moving_average = mean(history)
                target_long = signal_price >= moving_average
            if target_long is True and quantity == 0:
                buy_price = price * (1 + slippage_rate)
                gross_value = cash / (1 + fee_rate)
                fee = gross_value * fee_rate
                quantity = gross_value / buy_price
                cash -= gross_value + fee
                if abs(cash) < 1e-9:
                    cash = 0.0
                entry_cost = gross_value + fee
                total_turnover += gross_value
                trade_count += 1
            elif target_long is False and quantity > 0:
                sell_price = price * (1 - slippage_rate)
                gross_value = quantity * sell_price
                fee = gross_value * fee_rate
                cash += gross_value - fee
                closed_trade_pnls.append(gross_value - fee - entry_cost)
                total_turnover += gross_value
                quantity = 0.0
                entry_cost = 0.0
                trade_count += 1

        equity = cash + quantity * price
        period_return = (equity / previous_equity) - 1 if previous_equity else 0.0
        if index > 0:
            returns.append(period_return)
        previous_equity = equity
        equity_curve.append(
            {
                "timestamp": candle.timestamp.isoformat(),
                "price": price,
                "cash": cash,
                "quantity": quantity,
                "equity": equity,
                "position_value": quantity * price,
            }
        )

    final_equity = equity_curve[-1]["equity"]
    strategy_return = (final_equity / run.initial_cash) - 1
    first_price = candles[0].adjusted_close if candles[0].adjusted_close is not None else candles[0].close
    last_price = candles[-1].adjusted_close if candles[-1].adjusted_close is not None else candles[-1].close
    benchmark_return = (last_price / first_price) - 1
    max_drawdown = _max_drawdown([point["equity"] for point in equity_curve])
    sharpe = _sharpe(returns)
    win_rate = _win_rate(closed_trade_pnls)
    turnover = total_turnover / run.initial_cash if run.initial_cash else 0.0
    result_id = BacktestResult.build_id(
        backtest_id=run.backtest_id,
        final_equity=final_equity,
        trade_count=trade_count,
        strategy_return=strategy_return,
    )
    return BacktestResult(
        result_id=result_id,
        backtest_id=run.backtest_id,
        created_at=created_at,
        symbol=run.symbol,
        start=run.start,
        end=run.end,
        initial_cash=run.initial_cash,
        final_equity=final_equity,
        strategy_return=strategy_return,
        benchmark_return=benchmark_return,
        max_drawdown=max_drawdown,
        sharpe=sharpe,
        turnover=turnover,
        win_rate=win_rate,
        trade_count=trade_count,
        equity_curve=equity_curve,
        decision_basis="metrics include fee/slippage, buy-and-hold benchmark return, max drawdown, Sharpe, turnover, and win rate",
    )


def _validate_inputs(
    *,
    storage_dir: Path | str,
    start: datetime,
    end: datetime,
    created_at: datetime,
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
        raise ValueError("backtest start must be <= end")
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
                "backtest candles must have unique, strictly increasing timestamps "
                f"for the selected symbol; duplicate or non-increasing timestamp: {candle.timestamp.isoformat()}"
            )
        previous_timestamp = candle.timestamp


def _max_drawdown(equity_values: list[float]) -> float:
    peak = equity_values[0]
    max_drawdown = 0.0
    for equity in equity_values:
        peak = max(peak, equity)
        if peak:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
    return max_drawdown


def _sharpe(returns: list[float]) -> float | None:
    if len(returns) < 2:
        return None
    stddev = pstdev(returns)
    if stddev == 0:
        return None
    return (mean(returns) / stddev) * math.sqrt(len(returns))


def _win_rate(closed_trade_pnls: list[float]) -> float | None:
    if not closed_trade_pnls:
        return None
    return sum(1 for pnl in closed_trade_pnls if pnl > 0) / len(closed_trade_pnls)
