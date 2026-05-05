from __future__ import annotations

from datetime import datetime

from forecast_loop.models import BacktestResult, BacktestRun


DECISION_BLOCKER_BACKTEST_ID_CONTEXT = "id_context=decision_blocker_research:run_backtest:backtest_result"


def latest_backtest_for_research(
    *,
    backtests: list[BacktestResult],
    backtest_runs: list[BacktestRun],
    symbol: str,
    as_of: datetime | None = None,
    created_at_min: datetime | None = None,
) -> BacktestResult | None:
    candidates = [
        result
        for result in backtests
        if result.symbol == symbol
        and (as_of is None or result.created_at <= as_of)
        and (created_at_min is None or result.created_at >= created_at_min)
    ]
    if not candidates:
        return None
    run_by_id = {run.backtest_id: run for run in backtest_runs}
    preferred = [
        result
        for result in candidates
        if DECISION_BLOCKER_BACKTEST_ID_CONTEXT
        in run_by_id.get(result.backtest_id, result).decision_basis
    ]
    selected = preferred if preferred else candidates
    return max(selected, key=lambda item: (item.created_at, item.result_id))
